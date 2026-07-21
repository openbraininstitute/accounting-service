"""Admin discount service."""

from collections.abc import Sequence
from http import HTTPStatus
from uuid import UUID

from app.db.model import Discount
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.schema.admin import AdminDiscountUpdateIn
from app.schema.api import PaginatedParams
from app.utils import utcnow


async def _get_existing_discount(repos: RepositoryGroup, discount_id: int) -> Discount:
    """Return the discount with the given id, or raise a 404 error."""
    discount = await repos.discount.get_discount(discount_id)
    if discount is None:
        raise ApiError(
            message="Discount not found",
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=HTTPStatus.NOT_FOUND,
        )
    return discount


async def list_discounts(
    repos: RepositoryGroup,
    pagination: PaginatedParams,
    *,
    vlab_id: UUID | None = None,
) -> tuple[Sequence[Discount], int]:
    """Return a page of discounts, newest first."""
    return await repos.discount.list_discounts(pagination, vlab_id=vlab_id)


async def get_discount(repos: RepositoryGroup, discount_id: int) -> Discount:
    """Return the discount with the given id."""
    return await _get_existing_discount(repos, discount_id)


async def update_discount(
    repos: RepositoryGroup, discount_id: int, update_request: AdminDiscountUpdateIn
) -> Discount:
    """Update a discount.

    `valid_to` can always be moved to any value not in the past (shortening an
    active discount going forward is legitimate); `discount` and `valid_from`
    can only change while the discount hasn't started and isn't referenced by
    any journal entry.
    """
    now = utcnow()
    discount = await _get_existing_discount(repos, discount_id)
    data = update_request.model_dump(exclude_unset=True)
    if not data:
        raise ApiError(
            message="At least one field must be provided",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if {"discount", "valid_from"} & data.keys():
        if discount.valid_from <= now:
            raise ApiError(
                message="Only discount and valid_from of future discounts can be updated",
                error_code=ApiErrorCode.INVALID_REQUEST,
            )
        if await repos.discount.has_journal_references(discount_id):
            raise ApiError(
                message="The discount is referenced by the journal and cannot be updated",
                error_code=ApiErrorCode.INVALID_REQUEST,
            )
    if (valid_to := data.get("valid_to")) is not None and valid_to < now:
        raise ApiError(
            message="valid_to cannot be set in the past",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    new_valid_from = data.get("valid_from", discount.valid_from)
    new_valid_to = data.get("valid_to", discount.valid_to)
    if new_valid_to is not None and new_valid_from >= new_valid_to:
        raise ApiError(
            message="valid_to must be greater than valid_from",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    return await repos.discount.update_discount(discount_id, data)


async def delete_discount(repos: RepositoryGroup, discount_id: int) -> None:
    """Delete a discount that hasn't started and isn't referenced by any journal entry."""
    now = utcnow()
    discount = await _get_existing_discount(repos, discount_id)
    if discount.valid_from <= now:
        raise ApiError(
            message="Only future discounts can be deleted. Shorten valid_to instead",
            error_code=ApiErrorCode.INVALID_REQUEST,
        )
    if await repos.discount.has_journal_references(discount_id):
        raise ApiError(
            message="The discount is referenced by the journal and cannot be deleted",
            error_code=ApiErrorCode.INVALID_REQUEST,
            http_status_code=HTTPStatus.CONFLICT,
        )
    await repos.discount.delete_discount(discount_id)
