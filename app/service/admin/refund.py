"""Admin refund service."""

from http import HTTPStatus

from app.constants import TransactionType
from app.errors import ApiError, ApiErrorCode, ensure_result
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminRefundIn, AdminRefundOut
from app.utils import utcnow


async def refund_job(repos: RepositoryGroup, refund_request: AdminRefundIn) -> AdminRefundOut:
    """Refund a job by moving credits from the system account back to the project.

    The refundable amount is capped at the net amount charged for the job:
    the total credited to the system account minus the refunds already issued.
    """
    now = utcnow()
    job = await repos.job.get_job(refund_request.job_id)
    if job is None:
        raise ApiError(
            message="Job not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    with ensure_result(error_message="Account not found"):
        accounts = await repos.account.get_accounts_by_proj_id(proj_id=job.proj_id)
    # Lock the accounts before checking the cap to serialize concurrent refunds
    await repos.account.lock_accounts(sorted([accounts.sys.id, accounts.proj.id]))
    charged, refunded = await repos.ledger.get_sys_amounts_for_job(job.id)
    refundable = charged - refunded
    if refund_request.amount > refundable:
        raise ApiError(
            message="Refund amount exceeds the net charged amount for the job",
            error_code=ApiErrorCode.INVALID_REQUEST,
            details={"refundable": f"{refundable.normalize():f}"},
        )
    properties = {"reason": "admin_refund"}
    if refund_request.reason:
        properties["comment"] = refund_request.reason
    journal_id = await repos.ledger.insert_transaction(
        amount=refund_request.amount,
        debited_from=accounts.sys.id,
        credited_to=accounts.proj.id,
        transaction_datetime=now,
        transaction_type=TransactionType.REFUND,
        job_id=job.id,
        properties=properties,
    )
    return AdminRefundOut(
        journal_id=journal_id,
        job_id=job.id,
        vlab_id=accounts.vlab.id,
        proj_id=accounts.proj.id,
        amount=refund_request.amount,
    )
