"""Admin job service."""

from collections.abc import Sequence
from datetime import datetime
from http import HTTPStatus
from uuid import UUID

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Job
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminJobDetailOut, AdminJobOut, AdminJobStatus
from app.schema.api import PaginatedParams
from app.service.admin.journal import assemble_journal_entries


async def list_jobs(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    vlab_id: UUID | None = None,
    proj_id: UUID | None = None,
    service_type: ServiceType | None = None,
    service_subtype: ServiceSubtype | None = None,
    status: AdminJobStatus | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
) -> tuple[Sequence[Job], int]:
    """Return a page of jobs, newest first."""
    return await repos.job.list_jobs(
        pagination,
        vlab_id=vlab_id,
        proj_id=proj_id,
        service_type=service_type,
        service_subtype=service_subtype,
        status=status,
        started_after=started_after,
        started_before=started_before,
    )


async def get_job(repos: RepositoryGroup, job_id: UUID) -> AdminJobDetailOut:
    """Return a job with its full journal trail and charge totals."""
    job = await repos.job.get_job(job_id)
    if job is None:
        raise ApiError(
            message="Job not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    journals = await repos.ledger.get_journal_for_job(job_id)
    journal_out = await assemble_journal_entries(repos, journals)
    charged, refunded = await repos.ledger.get_sys_amounts_for_job(job_id)
    remaining_reservation = await repos.ledger.get_remaining_reservation_for_job(
        job_id=job_id, raise_if_negative=False
    )
    base = AdminJobOut.model_validate(job, from_attributes=True)
    return AdminJobDetailOut(
        **base.model_dump(),
        journal=journal_out,
        total_charged=charged,
        total_refunded=refunded,
        remaining_reservation=remaining_reservation,
    )
