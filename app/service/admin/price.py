"""Admin price service."""

from collections.abc import Sequence
from datetime import datetime
from http import HTTPStatus
from uuid import UUID

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Price
from app.errors import ApiError, ApiErrorCode, ensure_result
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, PaginatedParams
from app.utils import utcnow


async def _get_existing_price(repos: RepositoryGroup, price_id: int) -> Price:
    """Return the price with the given id, or raise a 404 error."""
    price = await repos.price.get_price_by_id(price_id)
    if price is None:
        raise ApiError(
            message="Price not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    return price


async def list_prices(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    service_type: ServiceType | None = None,
    service_subtype: ServiceSubtype | None = None,
    vlab_id: UUID | None = None,
    only_default: bool = False,
) -> tuple[Sequence[Price], int]:
    """Return a page of prices, including expired and future prices."""
    return await repos.price.list_prices(
        pagination,
        service_type=service_type,
        service_subtype=service_subtype,
        vlab_id=vlab_id,
        only_default=only_default,
    )


async def get_price(repos: RepositoryGroup, price_id: int) -> Price:
    """Return the price with the given id, with its tiers."""
    return await _get_existing_price(repos, price_id)


async def update_price(repos: RepositoryGroup, price_id: int, price_request: AddPriceIn) -> Price:
    """Replace a price and its tiers.

    Only prices valid in the future and not referenced by any journal entry can
    be updated. To change an active price, add a new price with `POST /price`
    and a future `valid_from`, then expire the old price at that same instant.
    """
    now = utcnow()
    price = await _get_existing_price(repos, price_id)
    if price.valid_from <= now:
        raise ApiError(
            message=(
                "Only prices valid in the future can be updated. "
                "To change an active price, add a new price and expire the old one"
            ),
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if await repos.price.has_journal_references(price_id):
        raise ApiError(
            message="The price is referenced by the journal and cannot be updated",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if price_request.valid_from <= now:
        raise ApiError(
            message="valid_from must be in the future",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if price_request.vlab_id:
        with ensure_result(error_message="Virtual lab not found"):
            await repos.account.get_vlab_account(vlab_id=price_request.vlab_id)
    return await repos.price.update_price(price_id, price_request.model_dump())


async def expire_price(
    repos: RepositoryGroup, price_id: int, *, valid_to: datetime | None
) -> Price:
    """Expire a price by setting its valid_to, defaulting to now.

    Retroactive expiry is forbidden: in-flight jobs resolve their price at
    reservation or start time, which must stay within the validity window.
    """
    now = utcnow()
    price = await _get_existing_price(repos, price_id)
    valid_to = valid_to or now
    if valid_to < now:
        raise ApiError(
            message="valid_to cannot be in the past",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if price.valid_to is not None and price.valid_to <= now:
        raise ApiError(
            message="The price is already expired",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if valid_to <= price.valid_from:
        raise ApiError(
            message="valid_to must be greater than valid_from",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    return await repos.price.set_price_valid_to(price_id, valid_to)
