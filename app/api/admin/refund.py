"""Admin refund api."""

from fastapi import APIRouter

from app.dependencies import RepoGroupDep
from app.schema.admin import AdminRefundIn, AdminRefundOut
from app.schema.api import ApiResponse
from app.service.admin import refund as admin_refund

router = APIRouter()


@router.post("")
async def refund_job(
    repos: RepoGroupDep,
    refund_request: AdminRefundIn,
) -> ApiResponse[AdminRefundOut]:
    """Refund a job by moving credits from the system account back to the project.

    The refundable amount is capped at the net amount charged for the job:
    the total charged minus the refunds already issued.
    """
    result = await admin_refund.refund_job(repos, refund_request)
    return ApiResponse[AdminRefundOut](
        message="Refund issued",
        data=result,
    )
