"""Discount repository module."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import null, or_

from app import utils
from app.db.model import Discount
from app.repository.base import BaseRepository


class DiscountRepository(BaseRepository):
    """Repository for managing discount records in the database."""

    async def get_current_vlab_discount(self, vlab_id: UUID) -> Discount | None:
        """Retrieve the currently active discount for a specific virtual lab.

        Finds the most recent discount that is currently valid (started in the past and
        either has no end date or ends in the future).

        Args:
            vlab_id: UUID of the virtual lab to query discounts for

        Returns:
            The most recent active Discount object or None if no active discount exists
        """
        now = utils.utcnow()
        query = (
            sa.select(Discount)
            .where(
                Discount.vlab_id == vlab_id,
                Discount.valid_from <= now,
                or_(
                    Discount.valid_to == null(),
                    Discount.valid_to > now,
                ),
            )
            .order_by(Discount.valid_from.desc(), Discount.id.desc())
            .limit(1)
        )
        return (await self.db.execute(query)).scalar_one_or_none()

    async def get_all_vlab_discounts(self, vlab_id: UUID) -> Sequence[Discount]:
        """Retrieve all discounts (active and inactive) for a specific virtual lab.

        Returns discounts sorted by validity date in descending order (newest first).

        Args:
            vlab_id: UUID of the virtual lab to query discounts for

        Returns:
            List of all Discount objects associated with the virtual lab
        """
        query = (
            sa.select(Discount)
            .where(Discount.vlab_id == vlab_id)
            .order_by(Discount.valid_from.desc(), Discount.id.desc())
        )
        return (await self.db.execute(query)).scalars().all()

    async def create_discount(self, data: dict[str, Any]) -> Discount:
        """Create a new discount record in the database.

        Args:
            data: Dictionary containing discount attributes (vlab_id, percentage, valid_from,
                 valid_to, etc.)

        Returns:
            The newly created Discount object
        """
        return (
            await self.db.execute(sa.insert(Discount).values(data).returning(Discount))
        ).scalar_one()

    async def update_discount(self, discount_id: int, data: dict[str, Any]) -> Discount:
        """Update an existing discount record by its ID.

        Args:
            discount_id: The UUID of the discount to update
            data: Dictionary containing the fields to update (percentage, valid_from, etc.)

        Returns:
            Updated Discount object or None if discount not found
        """
        query = (
            sa.update(Discount).where(Discount.id == discount_id).values(data).returning(Discount)
        )
        return (await self.db.execute(query)).scalar_one()
