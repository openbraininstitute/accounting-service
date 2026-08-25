"""Report api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from starlette.requests import Request

from app.dependencies import RepoGroupDep
from app.schema.api import (
    ApiResponse,
    JobReportUnionOut,
    PaginatedOut,
    ReportQueryParams,
)
from app.service import report as report_service

router = APIRouter()


@router.get("/system", response_model_exclude_defaults=True)
async def get_jobs_for_system(
    request: Request,
    repos: RepoGroupDep,
    query: Annotated[ReportQueryParams, Query()],
) -> ApiResponse[PaginatedOut[JobReportUnionOut]]:
    """Return the job report for a given virtual-lab."""
    pagination = query.pagination
    jobs, total_items = await report_service.get_report_for_system(
        repos,
        pagination=pagination,
        started_after=query.started_after,
        started_before=query.started_before,
    )
    result = PaginatedOut[JobReportUnionOut].new(
        items=jobs, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[JobReportUnionOut]](
        message="Job report for system",
        data=result,
    )


@router.get("/virtual-lab/{vlab_id}", response_model_exclude_defaults=True)
async def get_jobs_for_vlab(
    request: Request,
    repos: RepoGroupDep,
    vlab_id: UUID,
    query: Annotated[ReportQueryParams, Query()],
) -> ApiResponse[PaginatedOut[JobReportUnionOut]]:
    """Return the job report for a given virtual-lab."""
    pagination = query.pagination
    jobs, total_items = await report_service.get_report_for_vlab(
        repos,
        vlab_id=vlab_id,
        pagination=pagination,
        started_after=query.started_after,
        started_before=query.started_before,
    )
    result = PaginatedOut[JobReportUnionOut].new(
        items=jobs, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[JobReportUnionOut]](
        message=f"Job report for virtual-lab {vlab_id}",
        data=result,
    )


@router.get("/project/{proj_id}", response_model_exclude_defaults=True)
async def get_jobs_for_proj(
    request: Request,
    repos: RepoGroupDep,
    proj_id: UUID,
    query: Annotated[ReportQueryParams, Query()],
) -> ApiResponse[PaginatedOut[JobReportUnionOut]]:
    """Return the job report for a given project."""
    pagination = query.pagination
    jobs, total_items = await report_service.get_report_for_project(
        repos,
        proj_id=proj_id,
        pagination=pagination,
        started_after=query.started_after,
        started_before=query.started_before,
    )
    result = PaginatedOut[JobReportUnionOut].new(
        items=jobs, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[JobReportUnionOut]](
        message=f"Job report for project {proj_id}",
        data=result,
    )
