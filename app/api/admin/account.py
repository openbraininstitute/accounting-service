"""Admin account api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from starlette.requests import Request

from app.dependencies import RepoGroupDep
from app.schema.admin import (
    AdminAccountOut,
    AdminAccountStatusOut,
    AdminAccountUpdateIn,
    AdminProjOut,
    AdminVlabOut,
)
from app.schema.api import ApiResponse, PaginatedOut, PaginatedParams
from app.service.admin import account as admin_account

router = APIRouter()


@router.get("/virtual-lab")
async def get_virtual_labs(
    request: Request,
    repos: RepoGroupDep,
    *,
    name: str | None = None,
    enabled: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[AdminVlabOut]]:
    """Return the virtual-lab accounts, including the disabled ones.

    Args:
        request: the incoming request.
        repos: the repository group.
        name: optionally filter by substring of the account name, case-insensitive.
        enabled: optionally filter by enabled flag.
        page: page number.
        page_size: page size.
    """
    pagination = PaginatedParams(page=page, page_size=page_size)
    accounts, total_items = await admin_account.list_vlabs(
        repos, pagination, name=name, enabled=enabled
    )
    items = [AdminVlabOut.model_validate(account, from_attributes=True) for account in accounts]
    result = PaginatedOut[AdminVlabOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminVlabOut]](
        message="Virtual lab accounts",
        data=result,
    )


@router.get("/virtual-lab/{vlab_id}/project")
async def get_projects(
    request: Request,
    repos: RepoGroupDep,
    vlab_id: UUID,
    *,
    enabled: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[AdminProjOut]]:
    """Return the project accounts of a virtual-lab, including the disabled ones."""
    pagination = PaginatedParams(page=page, page_size=page_size)
    items, total_items = await admin_account.list_projects(
        repos, pagination, vlab_id=vlab_id, enabled=enabled
    )
    result = PaginatedOut[AdminProjOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminProjOut]](
        message=f"Project accounts for virtual-lab {vlab_id}",
        data=result,
    )


@router.get("/{account_id}")
async def get_account(
    repos: RepoGroupDep,
    account_id: UUID,
) -> ApiResponse[AdminAccountOut]:
    """Return any account by id, including disabled accounts."""
    result = await admin_account.get_account(repos, account_id)
    return ApiResponse[AdminAccountOut](
        message="Account",
        data=result,
    )


@router.patch("/{account_id}")
async def update_account(
    repos: RepoGroupDep,
    account_id: UUID,
    update_request: AdminAccountUpdateIn,
) -> ApiResponse[AdminAccountStatusOut]:
    """Enable or disable a virtual-lab or project account, cascading to its subtree.

    Disabling doesn't stop the open jobs listed in `open_job_ids`: they cannot be
    charged until the accounts are enabled again.
    """
    result = await admin_account.set_account_status(
        repos, account_id, enabled=update_request.enabled
    )
    return ApiResponse[AdminAccountStatusOut](
        message=f"Account {'enabled' if update_request.enabled else 'disabled'}",
        data=result,
    )
