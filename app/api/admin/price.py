"""Admin price api."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from starlette.requests import Request

from app.constants import ServiceSubtype, ServiceType
from app.dependencies import RepoGroupDep
from app.schema.admin import AdminPriceExpireIn, AdminPriceOut
from app.schema.api import AddPriceIn, ApiResponse, PaginatedOut, PaginatedParams
from app.service.admin import price as admin_price

router = APIRouter()


@router.get("")
async def get_prices(
    request: Request,
    repos: RepoGroupDep,
    *,
    service_type: ServiceType | None = None,
    service_subtype: ServiceSubtype | None = None,
    vlab_id: UUID | None = None,
    only_default: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 1000,
) -> ApiResponse[PaginatedOut[AdminPriceOut]]:
    """Return the prices, including the expired and future ones, newest first.

    Args:
        request: the incoming request.
        repos: the repository group.
        service_type: optionally filter by service type.
        service_subtype: optionally filter by service subtype.
        vlab_id: optionally return only the overrides for the given virtual-lab.
        only_default: if True, return only the default prices (not bound to any virtual-lab).
        page: page number.
        page_size: page size.
    """
    pagination = PaginatedParams(page=page, page_size=page_size)
    prices, total_items = await admin_price.list_prices(
        repos,
        pagination,
        service_type=service_type,
        service_subtype=service_subtype,
        vlab_id=vlab_id,
        only_default=only_default,
    )
    items = [AdminPriceOut.model_validate(price, from_attributes=True) for price in prices]
    result = PaginatedOut[AdminPriceOut].new(
        items=items, total_items=total_items, pagination=pagination, url=request.url
    )
    return ApiResponse[PaginatedOut[AdminPriceOut]](
        message="Prices",
        data=result,
    )


@router.get("/{price_id}")
async def get_price(
    repos: RepoGroupDep,
    price_id: int,
) -> ApiResponse[AdminPriceOut]:
    """Return the price with the given id, with its tiers."""
    result = await admin_price.get_price(repos, price_id)
    return ApiResponse[AdminPriceOut](
        message="Price",
        data=AdminPriceOut.model_validate(result, from_attributes=True),
    )


@router.put("/{price_id}")
async def update_price(
    repos: RepoGroupDep,
    price_id: int,
    price_request: AddPriceIn,
) -> ApiResponse[AdminPriceOut]:
    """Replace a price and its tiers.

    Only prices valid in the future and not referenced by any journal entry can
    be updated. To change an active price, add a new price with `POST /price`
    and a future `valid_from`, then expire the old price at that same instant.
    """
    result = await admin_price.update_price(repos, price_id, price_request)
    return ApiResponse[AdminPriceOut](
        message="Price updated",
        data=AdminPriceOut.model_validate(result, from_attributes=True),
    )


@router.post("/{price_id}/expire")
async def expire_price(
    repos: RepoGroupDep,
    price_id: int,
    expire_request: AdminPriceExpireIn,
) -> ApiResponse[AdminPriceOut]:
    """Expire a price by setting its valid_to, defaulting to now.

    Retroactive expiry is forbidden, so the ongoing jobs already priced within
    the validity window are not affected.
    """
    result = await admin_price.expire_price(repos, price_id, valid_to=expire_request.valid_to)
    return ApiResponse[AdminPriceOut](
        message="Price expired",
        data=AdminPriceOut.model_validate(result, from_attributes=True),
    )
