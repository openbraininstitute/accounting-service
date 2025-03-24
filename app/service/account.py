"""Account service."""

from decimal import Decimal
from uuid import UUID

from app.constants import D0
from app.repository.group import RepositoryGroup
from app.schema.domain import ProjAccount, SysAccount, VlabAccount
from app.service.budget import top_up


async def add_system(repos: RepositoryGroup, account_id: UUID, name: str) -> SysAccount:
    """Add the system account."""
    return await repos.account.add_sys_account(account_id=account_id, name=name)


async def add_virtual_lab(
    repos: RepositoryGroup, account_id: UUID, name: str, balance: Decimal
) -> VlabAccount:
    """Add a new virtual lab account."""
    account = await repos.account.add_vlab_account(account_id=account_id, name=name)

    if balance == D0:
        return account

    await top_up(repos, vlab_id=account.id, amount=balance)
    return await repos.account.get_vlab_account(vlab_id=account.id)


async def add_project(
    repos: RepositoryGroup, account_id: UUID, name: str, vlab_id: UUID
) -> ProjAccount:
    """Add a new project account."""
    return await repos.account.add_proj_account(account_id=account_id, name=name, vlab_id=vlab_id)
