"""Admin refund service."""

from http import HTTPStatus

from app.constants import ServiceType, TransactionType
from app.db.model import Job
from app.errors import ApiError, ApiErrorCode, ensure_result
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminRefundIn, AdminRefundOut
from app.utils import utcnow


def _is_charge_pending(job: Job) -> bool:
    """Return True if a periodic charger can still charge the job.

    It mirrors the queries selecting the jobs to be charged in `JobRepository`:
    `get_oneshot_to_be_charged`, `get_longrun_to_be_charged`, and
    `get_storage_finished_to_be_charged`.
    """
    match job.service_type:
        case ServiceType.ONESHOT:
            return job.started_at is not None and job.last_charged_at is None
        case ServiceType.LONGRUN:
            return job.started_at is not None and job.last_charged_at != job.finished_at
        case ServiceType.STORAGE:
            return job.finished_at is not None and job.last_charged_at != job.finished_at


async def refund_job(repos: RepositoryGroup, refund_request: AdminRefundIn) -> AdminRefundOut:
    """Refund a job by moving credits from the system account back to the project.

    The refunded amount defaults to the net amount charged for the job: the total
    credited to the system account minus the refunds already issued. A smaller
    amount can be passed explicitly to refund only a part of it.

    Only jobs that are closed and fully charged can be refunded, so that a later
    charge cannot silently turn a full refund into a net charge.
    """
    now = utcnow()
    job = await repos.job.get_job(refund_request.job_id)
    if job is None:
        raise ApiError(
            message="Job not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    if job.finished_at is None and job.cancelled_at is None:
        raise ApiError(
            message="The job is still running",
            error_code=ApiErrorCode.JOB_NOT_FINISHED,
        )
    if _is_charge_pending(job):
        raise ApiError(
            message="The job has a pending charge",
            error_code=ApiErrorCode.JOB_NOT_FINISHED,
        )
    with ensure_result(error_message="Account not found"):
        accounts = await repos.account.get_accounts_by_proj_id(proj_id=job.proj_id)
    # Lock the accounts before checking the cap to serialize concurrent refunds
    await repos.account.lock_accounts(sorted([accounts.sys.id, accounts.proj.id]))
    charged, refunded = await repos.ledger.get_sys_amounts_for_job(job.id)
    refundable = charged - refunded
    amount = refund_request.amount if refund_request.amount is not None else refundable
    if amount <= 0:
        raise ApiError(
            message="There is nothing to refund for the job",
            error_code=ApiErrorCode.INVALID_REQUEST,
            details={"refundable": f"{refundable.normalize():f}"},
        )
    if amount > refundable:
        raise ApiError(
            message="Refund amount exceeds the net charged amount for the job",
            error_code=ApiErrorCode.INVALID_REQUEST,
            details={"refundable": f"{refundable.normalize():f}"},
        )
    properties = {"reason": "admin_refund"}
    if refund_request.reason:
        properties["comment"] = refund_request.reason
    journal_id = await repos.ledger.insert_transaction(
        amount=amount,
        debited_from=accounts.sys.id,
        credited_to=accounts.proj.id,
        transaction_datetime=now,
        transaction_type=TransactionType.MANUAL_REFUND,
        job_id=job.id,
        properties=properties,
    )
    return AdminRefundOut(
        journal_id=journal_id,
        job_id=job.id,
        vlab_id=accounts.vlab.id,
        proj_id=accounts.proj.id,
        amount=amount,
    )
