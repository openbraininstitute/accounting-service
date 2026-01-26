"""Estimate api."""

from fastapi import APIRouter

from app.dependencies import RepoGroupDep
from app.schema.api import ApiResponse, EstimateCostOut, EstimateOneshotCostIn
from app.service import price

router = APIRouter()


@router.post("/oneshot")
async def estimate_oneshot_cost(
    repos: RepoGroupDep,
    estimate_request: EstimateOneshotCostIn,
) -> ApiResponse[EstimateCostOut]:
    """Estimate the cost in credits for a oneshot job."""
    result = await price.estimate_oneshot_cost(repos, estimate_request)
    return ApiResponse[EstimateCostOut](
        message="Cost estimation for oneshot job",
        data=result,
    )
