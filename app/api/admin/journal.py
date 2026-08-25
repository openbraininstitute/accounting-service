"""Admin journal api."""

from typing import Annotated

from fastapi import APIRouter, Query
from starlette.requests import Request

from app.dependencies import RepoGroupDep
from app.schema.admin import AdminJournalOut, AdminJournalQueryParams
from app.schema.api import ApiResponse, PaginatedOut
from app.service.admin import journal as admin_journal

router = APIRouter()


@router.get("")
async def get_journal(
    request: Request,
    repos: RepoGroupDep,
    query: Annotated[AdminJournalQueryParams, Query()],
) -> ApiResponse[PaginatedOut[AdminJournalOut]]:
    """Return the journal entries with their ledger sides, newest first.

    Args:
        request: the incoming request.
        repos: the repository group.
        query: the query parameters:

            - account_id: optionally filter by account appearing on either side of the transaction.
            - transaction_type: optionally filter by transaction type.
            - job_id: optionally filter by job.
            - transaction_after: optionally filter by transaction_datetime >= transaction_after.
            - transaction_before: optionally filter by transaction_datetime < transaction_before.
            - page: page number.
            - page_size: page size.
    """
    pagination = query.pagination
    items, total_items = await admin_journal.get_journal(
        repos,
        pagination,
        account_id=query.account_id,
        transaction_type=query.transaction_type,
        job_id=query.job_id,
        transaction_after=query.transaction_after,
        transaction_before=query.transaction_before,
    )
    result = PaginatedOut[AdminJournalOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminJournalOut]](
        message="Journal entries",
        data=result,
    )
