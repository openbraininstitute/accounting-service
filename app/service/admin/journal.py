"""Admin journal service."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.constants import TransactionType
from app.db.model import Journal
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminJournalOut, AdminLedgerEntryOut
from app.schema.api import PaginatedParams


async def assemble_journal_entries(
    repos: RepositoryGroup, journals: Sequence[Journal]
) -> list[AdminJournalOut]:
    """Return the given journal entries with both ledger sides attached."""
    rows = await repos.ledger.get_ledger_entries_for_journals([j.id for j in journals])
    ledgers_by_journal: dict[int, list[AdminLedgerEntryOut]] = {}
    for row in rows:
        entry = AdminLedgerEntryOut(
            id=row.Ledger.id,
            account_id=row.Ledger.account_id,
            account_name=row.name,
            account_type=row.account_type,
            amount=row.Ledger.amount,
        )
        ledgers_by_journal.setdefault(row.Ledger.journal_id, []).append(entry)
    return [
        AdminJournalOut(
            id=journal.id,
            transaction_datetime=journal.transaction_datetime,
            transaction_type=journal.transaction_type,
            job_id=journal.job_id,
            price_id=journal.price_id,
            discount_id=journal.discount_id,
            properties=journal.properties,
            ledgers=ledgers_by_journal.get(journal.id, []),
        )
        for journal in journals
    ]


async def get_journal(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    account_id: UUID | None = None,
    transaction_type: TransactionType | None = None,
    job_id: UUID | None = None,
    transaction_after: datetime | None = None,
    transaction_before: datetime | None = None,
) -> tuple[list[AdminJournalOut], int]:
    """Return a page of journal entries with their ledger sides, newest first."""
    if transaction_after and transaction_before and transaction_after >= transaction_before:
        raise ApiError(
            message="transaction_after must be before transaction_before",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    journals, count = await repos.ledger.get_journal_page(
        pagination,
        account_id=account_id,
        transaction_type=transaction_type,
        job_id=job_id,
        transaction_after=transaction_after,
        transaction_before=transaction_before,
    )
    items = await assemble_journal_entries(repos, journals)
    return items, count
