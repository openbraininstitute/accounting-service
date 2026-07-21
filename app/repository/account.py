"""Account repository module."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import and_, func, true
from sqlalchemy.orm import aliased

from app.constants import AccountType
from app.db.model import Account
from app.repository.base import BaseRepository
from app.schema.api import PaginatedParams
from app.schema.domain import Accounts, ProjAccount, RsvAccount, SysAccount, VlabAccount
from app.utils import create_uuid


class AccountRepository(BaseRepository):
    """AccountRepository."""

    async def get_system_account(self) -> SysAccount:
        """Return the system account."""
        query = sa.select(Account).where(Account.account_type == AccountType.SYS)
        result = (await self.db.execute(query)).scalar_one()
        return SysAccount.model_validate(result)

    async def _get_generic_account(
        self,
        account_id: UUID,
        account_type: AccountType,
        *,
        for_update: bool = False,
    ) -> Account:
        """Return the account for the given account id and type.

        Args:
            account_id: account UUID.
            account_type: account type.
            for_update: if True, locks the selected row against concurrent updates.
        """
        query = sa.select(Account).where(
            and_(
                Account.account_type == account_type,
                Account.id == account_id,
                Account.enabled == true(),
            )
        )
        if for_update:
            query = query.with_for_update()
        return (await self.db.execute(query)).scalar_one()

    async def get_vlab_account(self, vlab_id: UUID, *, for_update: bool = False) -> VlabAccount:
        """Return the virtual lab account for the given virtual lab id.

        Args:
            vlab_id: virtual lab UUID.
            for_update: if True, locks the selected row against concurrent updates.
        """
        result = await self._get_generic_account(
            account_id=vlab_id, account_type=AccountType.VLAB, for_update=for_update
        )
        return VlabAccount.model_validate(result)

    async def get_proj_account(self, proj_id: UUID, *, for_update: bool = False) -> ProjAccount:
        """Return the project account for the given project id.

        Args:
            proj_id: project UUID.
            for_update: if True, lock the selected row against concurrent updates.
        """
        result = await self._get_generic_account(
            account_id=proj_id, account_type=AccountType.PROJ, for_update=for_update
        )
        return ProjAccount.model_validate(result)

    async def get_reservation_account(
        self, proj_id: UUID, *, for_update: bool = False
    ) -> RsvAccount:
        """Return the reservation account for the given project id.

        Args:
            proj_id: project UUID.
            for_update: if True, locks the selected row against concurrent updates.
        """
        rows = await self.get_reservation_accounts(proj_ids=[proj_id], for_update=for_update)
        return rows[0]

    async def get_accounts_by_proj_id(
        self, proj_id: UUID, *, for_update: set[AccountType] | None = None
    ) -> Accounts:
        """Return the related VLAB, PROJ, and RSV accounts for the given proj_id."""
        for_update = for_update or set()
        proj = await self.get_proj_account(
            proj_id=proj_id, for_update=AccountType.PROJ in for_update
        )
        rsv = await self.get_reservation_account(
            proj_id=proj_id, for_update=AccountType.RSV in for_update
        )
        vlab = await self.get_vlab_account(
            vlab_id=proj.vlab_id, for_update=AccountType.VLAB in for_update
        )
        sys = await self.get_system_account()
        return Accounts(sys=sys, vlab=vlab, proj=proj, rsv=rsv)

    async def get_proj_accounts_for_vlab(self, vlab_id: UUID) -> list[ProjAccount]:
        """Return all the projects for the specified virtual-lab."""
        query = sa.select(Account).where(
            and_(
                Account.account_type == AccountType.PROJ,
                Account.parent_id == vlab_id,
                Account.enabled == true(),
            )
        )
        result = (await self.db.execute(query)).scalars()
        return [ProjAccount.model_validate(row) for row in result]

    async def lock_accounts(self, account_ids: list[UUID]) -> None:
        """Lock the given accounts in deterministic order to avoid deadlocks."""
        if not account_ids:
            return
        await self.db.execute(
            sa.select(Account.id)
            .where(Account.id.in_(account_ids))
            .order_by(Account.id)
            .with_for_update()
        )

    async def get_reservation_accounts(
        self, proj_ids: list[UUID], *, for_update: bool = False
    ) -> list[RsvAccount]:
        """Return the reservation accounts for the given project ids.

        Args:
            proj_ids: list of project UUIDs.
            for_update: if True, locks the selected rows against concurrent updates.
        """
        if not proj_ids:
            return []
        query = sa.select(Account).where(
            and_(
                Account.account_type == AccountType.RSV,
                Account.parent_id.in_(proj_ids),
                Account.enabled == true(),
            )
        )
        if for_update:
            query = query.with_for_update()
        rows = (await self.db.execute(query)).scalars()
        result = [RsvAccount.model_validate(row) for row in rows]
        if len(result) < len(proj_ids):
            errmsg = "No reservation account was found for some projects"
            raise ValueError(errmsg)
        if len(result) > len(proj_ids) or len(result) > len({rec.proj_id for rec in result}):
            errmsg = "Multiple reservation accounts were found for some projects"
            raise ValueError(errmsg)
        return result

    async def get_account(self, account_id: UUID) -> Account | None:
        """Return any account by id, including disabled accounts, or None if missing."""
        query = sa.select(Account).where(Account.id == account_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def list_accounts(
        self,
        pagination: PaginatedParams,
        *,
        account_type: AccountType | None = None,
        parent_id: UUID | None = None,
        name: str | None = None,
        enabled: bool | None = None,
    ) -> tuple[Sequence[Account], int]:
        """Return a page of accounts and the total count, including disabled accounts.

        Unlike the other getters, disabled accounts are returned unless filtered
        out explicitly with `enabled`.
        """
        where_clauses = [
            (Account.account_type == account_type) if account_type is not None else true(),
            (Account.parent_id == parent_id) if parent_id is not None else true(),
            Account.name.icontains(name, autoescape=True) if name is not None else true(),
            (Account.enabled == enabled) if enabled is not None else true(),
        ]
        count_query = sa.select(func.count()).select_from(Account).where(*where_clauses)
        count = (await self.db.execute(count_query)).scalar_one()
        query = (
            sa.select(Account)
            .where(*where_clauses)
            .order_by(Account.created_at.desc(), Account.id)
            .limit(pagination.page_size)
            .offset(pagination.page_size * (pagination.page - 1))
        )
        rows = (await self.db.execute(query)).scalars().all()
        return rows, count

    async def list_projects_with_reservation(
        self,
        pagination: PaginatedParams,
        *,
        vlab_id: UUID,
        enabled: bool | None = None,
    ) -> tuple[Sequence[sa.Row], int]:
        """Return a page of (project account, reservation balance) rows for a virtual-lab.

        Disabled accounts are returned unless filtered out explicitly with `enabled`.
        """
        rsv = aliased(Account)
        where_clauses = [
            Account.account_type == AccountType.PROJ,
            Account.parent_id == vlab_id,
            (Account.enabled == enabled) if enabled is not None else true(),
        ]
        count_query = sa.select(func.count()).select_from(Account).where(*where_clauses)
        count = (await self.db.execute(count_query)).scalar_one()
        query = (
            sa.select(Account, rsv.balance.label("reservation"))
            .outerjoin(rsv, and_(rsv.parent_id == Account.id, rsv.account_type == AccountType.RSV))
            .where(*where_clauses)
            .order_by(Account.created_at.desc(), Account.id)
            .limit(pagination.page_size)
            .offset(pagination.page_size * (pagination.page - 1))
        )
        rows = (await self.db.execute(query)).all()
        return rows, count

    async def get_child_account_ids(self, parent_ids: Sequence[UUID]) -> list[UUID]:
        """Return the ids of the direct children of the given accounts, including disabled."""
        if not parent_ids:
            return []
        query = sa.select(Account.id).where(Account.parent_id.in_(parent_ids))
        return list((await self.db.execute(query)).scalars().all())

    async def set_accounts_enabled(
        self, account_ids: Sequence[UUID], *, enabled: bool
    ) -> Sequence[Account]:
        """Set the enabled flag on the given accounts and return the updated rows."""
        if not account_ids:
            return []
        query = (
            sa.update(Account)
            .values(enabled=enabled)
            .where(Account.id.in_(account_ids))
            .returning(Account)
        )
        return (await self.db.execute(query)).scalars().all()

    async def _add_generic_account(self, **kwargs) -> Account:
        return (
            await self.db.execute(sa.insert(Account).values(kwargs).returning(Account))
        ).scalar_one()

    async def add_sys_account(self, account_id: UUID, name: str) -> SysAccount:
        """Add the system account. Only one system account is allowed."""
        account = await self._add_generic_account(
            account_type=AccountType.SYS,
            id=account_id,
            name=name,
        )
        return SysAccount.model_validate(account)

    async def add_vlab_account(self, account_id: UUID, name: str) -> VlabAccount:
        """Add a new virtual lab account."""
        account = await self._add_generic_account(
            account_type=AccountType.VLAB, id=account_id, name=name
        )
        return VlabAccount.model_validate(account)

    async def add_proj_account(self, account_id: UUID, name: str, vlab_id: UUID) -> ProjAccount:
        """Add a new project account."""
        account = await self._add_generic_account(
            account_type=AccountType.PROJ,
            id=account_id,
            name=name,
            parent_id=vlab_id,
        )
        await self._add_generic_account(
            account_type=AccountType.RSV,
            id=create_uuid(),
            name=f"{name}/RESERVATION",
            parent_id=account_id,
        )
        return ProjAccount.model_validate(account)
