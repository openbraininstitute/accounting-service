"""Admin account service."""

from collections.abc import Sequence
from http import HTTPStatus
from uuid import UUID

from app.constants import D0, AccountType
from app.db.model import Account
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminAccountOut, AdminAccountStatusOut, AdminProjOut
from app.schema.api import PaginatedParams


async def _get_existing_account(repos: RepositoryGroup, account_id: UUID) -> Account:
    """Return any account by id, including disabled accounts, or raise a 404 error."""
    account = await repos.account.get_account(account_id)
    if account is None:
        raise ApiError(
            message="Account not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    return account


async def list_vlabs(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    name: str | None = None,
    enabled: bool | None = None,
) -> tuple[Sequence[Account], int]:
    """Return a page of virtual-lab accounts, including disabled ones."""
    return await repos.account.list_accounts(
        pagination, account_type=AccountType.VLAB, name=name, enabled=enabled
    )


async def list_projects(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    vlab_id: UUID,
    enabled: bool | None = None,
) -> tuple[list[AdminProjOut], int]:
    """Return a page of project accounts for a virtual-lab, including disabled ones."""
    vlab = await repos.account.get_account(vlab_id)
    if vlab is None or vlab.account_type != AccountType.VLAB:
        raise ApiError(
            message="Virtual lab not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    rows, count = await repos.account.list_projects_with_reservation(
        pagination, vlab_id=vlab_id, enabled=enabled
    )
    items = [
        AdminProjOut(
            id=row.Account.id,
            vlab_id=vlab_id,
            name=row.Account.name,
            balance=row.Account.balance,
            reservation=row.reservation if row.reservation is not None else D0,
            enabled=row.Account.enabled,
            created_at=row.Account.created_at,
            updated_at=row.Account.updated_at,
        )
        for row in rows
    ]
    return items, count


async def get_account(repos: RepositoryGroup, account_id: UUID) -> AdminAccountOut:
    """Return any account by id, including disabled accounts."""
    account = await _get_existing_account(repos, account_id)
    return AdminAccountOut.model_validate(account, from_attributes=True)


async def set_account_status(
    repos: RepositoryGroup, account_id: UUID, *, enabled: bool
) -> AdminAccountStatusOut:
    """Enable or disable an account, cascading to its subtree.

    Disabling a virtual-lab disables its projects and their reservation accounts;
    disabling a project disables its reservation account. Enabling cascades the
    same way, so re-enabling a virtual-lab re-enables all its projects, including
    the ones that were disabled individually.
    """
    account = await _get_existing_account(repos, account_id)
    if account.account_type not in {AccountType.VLAB, AccountType.PROJ}:
        raise ApiError(
            message="Only virtual-lab and project accounts can be enabled or disabled",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if enabled and account.account_type == AccountType.PROJ and account.parent_id is not None:
        parent = await repos.account.get_account(account.parent_id)
        if parent is not None and not parent.enabled:
            raise ApiError(
                message="Cannot enable a project while its virtual-lab is disabled",
                error_code=ApiErrorCode.INVALID_REQUEST,
            )
    children = await repos.account.get_child_account_ids([account.id])
    grandchildren = await repos.account.get_child_account_ids(children)
    all_ids = [account.id, *children, *grandchildren]
    # Lock all involved accounts up front in deterministic order to avoid deadlocks
    await repos.account.lock_accounts(sorted(all_ids))
    updated = await repos.account.set_accounts_enabled(all_ids, enabled=enabled)
    # Open jobs are reported as a warning, not blocked: the periodic chargers cannot
    # charge them while the accounts are disabled
    open_job_ids = (
        [] if enabled else await repos.job.get_open_job_ids(account_ids=[account.id, *children])
    )
    accounts = sorted(
        (AdminAccountOut.model_validate(row, from_attributes=True) for row in updated),
        key=lambda account_out: str(account_out.id),
    )
    return AdminAccountStatusOut(accounts=accounts, open_job_ids=open_job_ids)
