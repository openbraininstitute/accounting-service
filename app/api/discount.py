"""Discount api."""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import RepoGroupDep
from app.errors import ApiError, ApiErrorCode
from app.schema.api import AddDiscountIn, ApiResponse, Discount
from app.service import discount

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_discount(
    repos: RepoGroupDep,
    discount_request: AddDiscountIn,
) -> ApiResponse[Discount]:
    """Add a new price."""
    result = await discount.create_discount(repos, discount_request)
    return ApiResponse[Discount](
        message="Discount created",
        data=Discount.model_validate(result, from_attributes=True),
    )


@router.put("", status_code=status.HTTP_200_OK)
async def update_discount(
    repos: RepoGroupDep,
    discount_update_request: Discount,
) -> ApiResponse[Discount]:
    """Update a price."""
    result = await discount.update_discount(
        repos, discount_update_request.id, discount_update_request.model_dump()
    )
    return ApiResponse[Discount](
        message="Discount updated",
        data=Discount.model_validate(result, from_attributes=True),
    )


@router.get("/virtual-lab/{vlab_id}", status_code=status.HTTP_200_OK)
async def get_all_vlab_discounts(
    repos: RepoGroupDep,
    vlab_id: UUID,
) -> ApiResponse[list[Discount]]:
    """Get alll discounts for a vlab."""
    discounts = await discount.get_all_vlab_discounts(repos, vlab_id)
    validated_discounts = [
        Discount.model_validate(discount, from_attributes=True) for discount in discounts
    ]
    return ApiResponse[list[Discount]](
        message="Virtual lab discounts fetched", data=validated_discounts
    )


@router.get("/virtual-lab/{vlab_id}/current", status_code=status.HTTP_200_OK)
async def get_current_vlab_discount(
    repos: RepoGroupDep,
    vlab_id: UUID,
) -> ApiResponse[Discount]:
    """Get current discount for a vlab."""
    current_discount = await discount.get_current_vlab_discount(repos, vlab_id)

    if not current_discount:
        raise ApiError(
            message="No current discount found for the virtual lab",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )

    return ApiResponse[Discount](
        message="Current virtual lab discount fetched",
        data=Discount.model_validate(current_discount, from_attributes=True),
    )
