"""Admin discount api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status
from starlette.requests import Request

from app.dependencies import RepoGroupDep
from app.schema.admin import AdminDiscountUpdateIn
from app.schema.api import AddDiscountIn, ApiResponse, Discount, PaginatedOut, PaginatedParams
from app.service import discount as discount_service
from app.service.admin import discount as admin_discount

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_discount(
    repos: RepoGroupDep,
    discount_request: AddDiscountIn,
) -> ApiResponse[Discount]:
    """Create a new discount.

    Discount=0 can be used to override existing discount.
    Discount=1 renders all the services free.
    """
    result = await discount_service.create_discount(repos, discount_request)
    return ApiResponse[Discount](
        message="Discount created",
        data=Discount.model_validate(result, from_attributes=True),
    )


@router.get("")
async def get_discounts(
    request: Request,
    repos: RepoGroupDep,
    *,
    vlab_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[Discount]]:
    """Return the discounts, newest first, optionally filtered by virtual-lab."""
    pagination = PaginatedParams(page=page, page_size=page_size)
    discounts, total_items = await admin_discount.list_discounts(repos, pagination, vlab_id=vlab_id)
    items = [Discount.model_validate(discount, from_attributes=True) for discount in discounts]
    result = PaginatedOut[Discount].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[Discount]](
        message="Discounts",
        data=result,
    )


@router.get("/{discount_id}")
async def get_discount(
    repos: RepoGroupDep,
    discount_id: int,
) -> ApiResponse[Discount]:
    """Return the discount with the given id."""
    result = await admin_discount.get_discount(repos, discount_id)
    return ApiResponse[Discount](
        message="Discount",
        data=Discount.model_validate(result, from_attributes=True),
    )


@router.patch("/{discount_id}")
async def update_discount(
    repos: RepoGroupDep,
    discount_id: int,
    update_request: AdminDiscountUpdateIn,
) -> ApiResponse[Discount]:
    """Update a discount.

    `valid_to` can always be moved to any value not in the past; `discount` and
    `valid_from` can only change while the discount hasn't started and isn't
    referenced by any journal entry.
    """
    result = await admin_discount.update_discount(repos, discount_id, update_request)
    return ApiResponse[Discount](
        message="Discount updated",
        data=Discount.model_validate(result, from_attributes=True),
    )


@router.delete("/{discount_id}")
async def delete_discount(
    repos: RepoGroupDep,
    discount_id: int,
) -> ApiResponse[None]:
    """Delete a discount that hasn't started and isn't referenced by any journal entry."""
    await admin_discount.delete_discount(repos, discount_id)
    return ApiResponse[None](
        message="Discount deleted",
        data=None,
    )
