"""Usage api.

Messages are pushed to the queue with minimal validation for better performance.
They are fully validated and processed when retrieved from the queue.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status
from starlette.requests import Request

from app.constants import ServiceSubtype
from app.dependencies import RepoGroupDep, SQSManagerDep
from app.schema.api import ApiResponse, LongrunOpenJobOut, PaginatedOut, PaginatedParams
from app.schema.queue import LongrunEvent, OneshotEvent, StorageEvent
from app.service import usage

router = APIRouter()


@router.post("/oneshot", status_code=status.HTTP_201_CREATED)
async def add_oneshot_usage(event: OneshotEvent, sqs_manager: SQSManagerDep) -> ApiResponse:
    """Add a new usage for oneshot job."""
    await usage.add_oneshot_usage(event, sqs_manager=sqs_manager)
    return ApiResponse(message="Oneshot usage received")


@router.post("/longrun", status_code=status.HTTP_201_CREATED)
async def add_longrun_usage(event: LongrunEvent, sqs_manager: SQSManagerDep) -> ApiResponse:
    """Add a new usage for longrun job."""
    await usage.add_longrun_usage(event, sqs_manager=sqs_manager)
    return ApiResponse(message="Longrun usage received")


@router.post("/storage", status_code=status.HTTP_201_CREATED)
async def add_storage_usage(event: StorageEvent, sqs_manager: SQSManagerDep) -> ApiResponse:
    """Add a new usage for storage."""
    await usage.add_storage_usage(event, sqs_manager=sqs_manager)
    return ApiResponse(message="Storage usage received")


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
    jobs, total_items = await usage.get_open_longrun_jobs(
        repos, subtype=subtype, pagination=pagination
    )
    result = PaginatedOut[LongrunOpenJobOut].new(
        items=jobs, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[LongrunOpenJobOut]](
        message="Open longrun jobs",
        data=result,
    )
