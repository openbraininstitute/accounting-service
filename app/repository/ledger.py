"""Ledger repository module."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, true

from app.constants import D0, AccountType, TransactionType
from app.db.model import Account, Journal, Ledger
from app.logger import L
from app.repository.base import BaseRepository
from app.schema.api import PaginatedParams


class LedgerRepository(BaseRepository):
    """LedgerRepository."""

    async def insert_transaction(
        self,
        amount: Decimal,
        debited_from: UUID,
        credited_to: UUID,
        transaction_datetime: datetime,
        transaction_type: TransactionType,
        job_id: UUID | None = None,
        price_id: int | None = None,
        discount_id: int | None = None,
        properties: dict | None = None,
    ) -> int:
        """Insert a transaction into journal and ledger, and update the balance accordingly.

        Return the id of the inserted journal entry.
        """
        if amount <= 0:
            L.warning("Negative transaction amount: {}", amount)
        # Lock both accounts in deterministic order to prevent deadlocks
        # and ensure consistent insertion order in journal and ledger
        await self.db.execute(
            sa.select(Account.id)
            .where(Account.id.in_([debited_from, credited_to]))
            .order_by(Account.id)
            .with_for_update()
        )
        query = (
            sa.insert(Journal)
            .values(
                transaction_datetime=transaction_datetime,
                transaction_type=transaction_type,
                job_id=job_id,
                price_id=price_id,
                discount_id=discount_id,
                properties=properties,
            )
            .returning(Journal.id)
        )
        journal_id = (await self.db.execute(query)).scalar_one()
        await self.db.execute(
            sa.insert(Ledger),
            [
                {
                    "account_id": debited_from,
                    "journal_id": journal_id,
                    "amount": -1 * amount,
                },
                {
                    "account_id": credited_to,
                    "journal_id": journal_id,
                    "amount": amount,
                },
            ],
        )
        (
            await self.db.execute(
                sa.update(Account)
                .values(balance=Account.balance + amount)
                .where(Account.id == credited_to)
                .returning(Account.balance)
            )
        ).one()
        (
            await self.db.execute(
                sa.update(Account)
                .values(balance=Account.balance - amount)
                .where(Account.id == debited_from)
                .returning(Account.balance)
            )
        ).one()
        return journal_id

    async def get_journal_page(
        self,
        pagination: PaginatedParams,
        *,
        account_id: UUID | None = None,
        transaction_type: TransactionType | None = None,
        job_id: UUID | None = None,
        transaction_after: datetime | None = None,
        transaction_before: datetime | None = None,
    ) -> tuple[Sequence[Journal], int]:
        """Return a page of journal entries and the total count, newest first.

        The `account_id` filter matches journal entries where the account appears
        on either side of the transaction.
        """
        where_clauses = [
            sa.exists().where(Ledger.journal_id == Journal.id, Ledger.account_id == account_id)
            if account_id is not None
            else true(),
            (Journal.transaction_type == transaction_type)
            if transaction_type is not None
            else true(),
            (Journal.job_id == job_id) if job_id is not None else true(),
            (Journal.transaction_datetime >= transaction_after) if transaction_after else true(),
            (Journal.transaction_datetime < transaction_before) if transaction_before else true(),
        ]
        count_query = sa.select(func.count()).select_from(Journal).where(*where_clauses)
        count = (await self.db.execute(count_query)).scalar_one()
        query = (
            sa.select(Journal)
            .where(*where_clauses)
            .order_by(Journal.transaction_datetime.desc(), Journal.id.desc())
            .limit(pagination.page_size)
            .offset(pagination.page_size * (pagination.page - 1))
        )
        rows = (await self.db.execute(query)).scalars().all()
        return rows, count

    async def get_journal_for_job(self, job_id: UUID) -> Sequence[Journal]:
        """Return all the journal entries for a job, oldest first."""
        query = (
            sa.select(Journal)
            .where(Journal.job_id == job_id)
            .order_by(Journal.transaction_datetime, Journal.id)
        )
        return (await self.db.execute(query)).scalars().all()

    async def get_ledger_entries_for_journals(self, journal_ids: Sequence[int]) -> Sequence[sa.Row]:
        """Return (Ledger, account name, account type) rows for the given journal entries."""
        if not journal_ids:
            return []
        query = (
            sa.select(Ledger, Account.name, Account.account_type)
            .join(Account, Account.id == Ledger.account_id)
            .where(Ledger.journal_id.in_(journal_ids))
            .order_by(Ledger.journal_id, Ledger.id)
        )
        return (await self.db.execute(query)).all()

    async def get_sys_amounts_for_job(self, job_id: UUID) -> tuple[Decimal, Decimal]:
        """Return the (charged, refunded) totals on the system account for a job.

        Charges credit the system account (positive ledger amounts) and refunds
        debit it (negative ledger amounts), so `charged - refunded` is the net
        amount charged for the job and not refunded yet.
        """
        query = (
            sa.select(
                func.coalesce(func.sum(sa.case((Ledger.amount > D0, Ledger.amount), else_=D0)), D0),
                func.coalesce(
                    func.sum(sa.case((Ledger.amount < D0, -Ledger.amount), else_=D0)), D0
                ),
            )
            .select_from(Journal)
            .join(Ledger, Ledger.journal_id == Journal.id)
            .join(Account, Account.id == Ledger.account_id)
            .where(Journal.job_id == job_id, Account.account_type == AccountType.SYS)
        )
        charged, refunded = (await self.db.execute(query)).one()
        return charged, refunded

    async def get_remaining_reservation_for_job(
        self, *, job_id: UUID, account_id: UUID | None = None, raise_if_negative: bool = True
    ) -> Decimal:
        """Return the remaining reservation amount for a specific job."""
        query = (
            sa.select(
                func.sum(Ledger.amount).label("total"),
            )
            .select_from(Journal)
            .join(Ledger)
            .join(Account)
            .where(
                Journal.job_id == job_id,
                Account.account_type == AccountType.RSV,
                (Ledger.account_id == account_id) if account_id else true(),
            )
        )
        result = (await self.db.execute(query)).scalar_one() or D0
        if raise_if_negative and result < 0:
            err = f"Reservation for job {job_id} is negative: {result}"
            raise RuntimeError(err)
        return result
