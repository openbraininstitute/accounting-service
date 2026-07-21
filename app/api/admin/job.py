"""Admin job api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import AwareDatetime
from starlette.requests import Request

from app.constants import ServiceSubtype, ServiceType
from app.dependencies import RepoGroupDep
from app.schema.admin import AdminJobDetailOut, AdminJobOut, AdminJobStatus
from app.schema.api import ApiResponse, PaginatedOut, PaginatedParams
from app.service.admin import job as admin_job

router = APIRouter()


@router.get("")
async def get_jobs(
    request: Request,
    repos: RepoGroupDep,
    *,
    vlab_id: UUID | None = None,
    proj_id: UUID | None = None,
    service_type: ServiceType | None = None,
    service_subtype: ServiceSubtype | None = None,
    status: AdminJobStatus | None = None,
    started_after: AwareDatetime | None = None,
    started_before: AwareDatetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[AdminJobOut]]:
    """Return the jobs, newest first.

    Args:
        request: the incoming request.
        repos: the repository group.
        vlab_id: optionally filter by virtual-lab.
        proj_id: optionally filter by project.
        service_type: optionally filter by service type.
        service_subtype: optionally filter by service subtype.
        status: optionally filter by job status.
        started_after: optionally filter by started_at >= started_after.
        started_before: optionally filter by started_at < started_before.
        page: page number.
        page_size: page size.
    """
    pagination = PaginatedParams(page=page, page_size=page_size)
    jobs, total_items = await admin_job.list_jobs(
        repos,
        pagination,
        vlab_id=vlab_id,
        proj_id=proj_id,
        service_type=service_type,
        service_subtype=service_subtype,
        status=status,
        started_after=started_after,
        started_before=started_before,
    )
    items = [AdminJobOut.model_validate(job, from_attributes=True) for job in jobs]
    result = PaginatedOut[AdminJobOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminJobOut]](
        message="Jobs",
        data=result,
    )


@router.get("/{job_id}")
async def get_job(
    repos: RepoGroupDep,
    job_id: UUID,
) -> ApiResponse[AdminJobDetailOut]:
    """Return a job with its full journal trail and charge totals."""
    result = await admin_job.get_job(repos, job_id)
    return ApiResponse[AdminJobDetailOut](
        message="Job",
        data=result,
    )
