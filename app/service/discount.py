"""Discount service."""

from collections.abc import Sequence
from http import HTTPStatus
from typing import Any
from uuid import UUID

from app.db.model import Discount
from app.errors import ensure_result
from app.repository.group import RepositoryGroup
from app.schema.api import AddDiscountIn


async def create_discount(repos: RepositoryGroup, discount_request: AddDiscountIn) -> Discount:
    """Add a price."""
    with ensure_result(error_message="Virtual lab not found"):
        await repos.account.get_vlab_account(vlab_id=discount_request.vlab_id)
    return await repos.discount.create_discount(discount_request.model_dump())


async def update_discount(
    repos: RepositoryGroup,
    discount_id: int,
    discount_request: dict[str, Any],
) -> Discount:
    """Update a discount."""
    with ensure_result(
        error_message="Virtual lab not found", http_status_code=HTTPStatus.UNPROCESSABLE_ENTITY
    ):
        await repos.account.get_vlab_account(vlab_id=discount_request["vlab_id"])
    return await repos.discount.update_discount(discount_id, discount_request)


async def get_all_vlab_discounts(repos: RepositoryGroup, vlab_id: UUID) -> Sequence[Discount]:
    """Get the current discount for the specified vlab."""
    return await repos.discount.get_all_vlab_discounts(vlab_id)


async def get_current_vlab_discount(repos: RepositoryGroup, vlab_id: UUID) -> Discount | None:
    """Get the current discount for the specified vlab."""
    return await repos.discount.get_current_vlab_discount(vlab_id)
