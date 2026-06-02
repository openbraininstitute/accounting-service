"""Job api."""

from typing import Annotated

from fastapi import APIRouter, Query
from starlette.requests import Request

from app.constants import ServiceSubtype
from app.dependencies import RepoGroupDep
from app.schema.api import ApiResponse, LongrunOpenJobOut, PaginatedOut, PaginatedParams
from app.service import job as job_service

router = APIRouter()


@router.get("/longrun/open")
async def get_open_longrun_jobs(
    request: Request,
    repos: RepoGroupDep,
    subtype: Annotated[ServiceSubtype | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[LongrunOpenJobOut]]:
    """Return open longrun jobs (not finished, not cancelled), optionally filtered by subtype."""
    pagination = PaginatedParams(page=page, page_size=page_size)
    jobs, total_items = await job_service.get_open_longrun_jobs(
        repos, subtype=subtype, pagination=pagination
    )
    result = PaginatedOut[LongrunOpenJobOut].new(
        items=jobs, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[LongrunOpenJobOut]](
        message="Open longrun jobs",
        data=result,
    )
