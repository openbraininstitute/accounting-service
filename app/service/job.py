"""Job service."""

from app.constants import ServiceSubtype
from app.repository.group import RepositoryGroup
from app.schema.api import LongrunOpenJobOut, PaginatedParams


async def get_open_longrun_jobs(
    repos: RepositoryGroup,
    *,
    subtype: ServiceSubtype | None = None,
    pagination: PaginatedParams,
) -> tuple[list[LongrunOpenJobOut], int]:
    """Return a paginated list of open longrun jobs."""
    jobs, total = await repos.job.get_open_longrun_jobs(pagination, subtype=subtype)
    return [LongrunOpenJobOut.model_validate(job) for job in jobs], total
