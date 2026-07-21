"""Admin journal api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import AwareDatetime
from starlette.requests import Request

from app.constants import TransactionType
from app.dependencies import RepoGroupDep
from app.schema.admin import AdminJournalOut
from app.schema.api import ApiResponse, PaginatedOut, PaginatedParams
from app.service.admin import journal as admin_journal

router = APIRouter()


@router.get("")
async def get_journal(
    request: Request,
    repos: RepoGroupDep,
    *,
    account_id: UUID | None = None,
    transaction_type: TransactionType | None = None,
    job_id: UUID | None = None,
    transaction_after: AwareDatetime | None = None,
    transaction_before: AwareDatetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[AdminJournalOut]]:
    """Return the journal entries with their ledger sides, newest first.

    Args:
        request: the incoming request.
        repos: the repository group.
        account_id: optionally filter by account appearing on either side of the transaction.
        transaction_type: optionally filter by transaction type.
        job_id: optionally filter by job.
        transaction_after: optionally filter by transaction_datetime >= transaction_after.
        transaction_before: optionally filter by transaction_datetime < transaction_before.
        page: page number.
        page_size: page size.
    """
    pagination = PaginatedParams(page=page, page_size=page_size)
    items, total_items = await admin_journal.get_journal(
        repos,
        pagination,
        account_id=account_id,
        transaction_type=transaction_type,
        job_id=job_id,
        transaction_after=transaction_after,
        transaction_before=transaction_before,
    )
    result = PaginatedOut[AdminJournalOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminJournalOut]](
        message="Journal entries",
        data=result,
    )
