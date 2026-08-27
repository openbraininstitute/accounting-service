"""Price repository module."""

from collections.abc import Sequence
from datetime import datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, null, or_, true

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Journal, Price, PriceTier
from app.errors import ApiError, ApiErrorCode
from app.repository.base import BaseRepository
from app.schema.api import PaginatedParams


class PriceRepository(BaseRepository):
    """PriceRepository."""

    async def _get_vlab_price(
        self,
        vlab_id: UUID | None,
        service_type: ServiceType,
        service_subtype: ServiceSubtype,
        usage_datetime: datetime,
    ) -> Price | None:
        """Return the price for the specified vlab."""
        query = (
            sa.select(Price)
            .where(
                Price.service_type == service_type,
                Price.service_subtype == service_subtype,
                Price.vlab_id == vlab_id,
                Price.valid_from <= usage_datetime,
                or_(
                    Price.valid_to == null(),
                    Price.valid_to > usage_datetime,
                ),
            )
            .order_by(Price.valid_from.desc(), Price.id.desc())
            .limit(1)
        )
        return (await self.db.execute(query)).scalar_one_or_none()

    async def get_price(
        self,
        vlab_id: UUID,
        service_type: ServiceType,
        service_subtype: ServiceSubtype,
        usage_datetime: datetime,
    ) -> Price:
        """Return the price for the specified vlab, or fallback to the default price."""
        price = await self._get_vlab_price(
            vlab_id=vlab_id,
            service_type=service_type,
            service_subtype=service_subtype,
            usage_datetime=usage_datetime,
        )
        if not price:
            price = await self._get_vlab_price(
                vlab_id=None,
                service_type=service_type,
                service_subtype=service_subtype,
                usage_datetime=usage_datetime,
            )
        if not price:
            err = f"Missing price for: {vlab_id} {service_type} {service_subtype} {usage_datetime}"
            raise ApiError(
                message=err,
                error_code=ApiErrorCode.ENTITY_NOT_FOUND,
                http_status_code=HTTPStatus.NOT_FOUND,
            )
        return price

    async def get_price_by_id(self, price_id: int) -> Price | None:
        """Return the price with the given id, or None if missing."""
        query = sa.select(Price).where(Price.id == price_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def list_prices(
        self,
        pagination: PaginatedParams,
        *,
        service_type: ServiceType | None = None,
        service_subtype: ServiceSubtype | None = None,
        vlab_id: UUID | None = None,
        only_default: bool = False,
    ) -> tuple[Sequence[Price], int]:
        """Return a page of prices and the total count, including expired and future prices.

        Args:
            pagination: pagination params.
            service_type: optionally filter by service type.
            service_subtype: optionally filter by service subtype.
            vlab_id: optionally return only the overrides for the given virtual-lab.
            only_default: if True, return only the default prices (vlab_id is null).
        """
        where_clauses = [
            (Price.service_type == service_type) if service_type is not None else true(),
            (Price.service_subtype == service_subtype) if service_subtype is not None else true(),
            (Price.vlab_id == vlab_id) if vlab_id is not None else true(),
            (Price.vlab_id == null()) if only_default else true(),
        ]
        count_query = sa.select(func.count()).select_from(Price).where(*where_clauses)
        count = (await self.db.execute(count_query)).scalar_one()
        query = (
            sa.select(Price)
            .where(*where_clauses)
            .order_by(Price.valid_from.desc(), Price.id.desc())
            .limit(pagination.page_size)
            .offset(pagination.page_size * (pagination.page - 1))
        )
        rows = (await self.db.execute(query)).scalars().all()
        return rows, count

    async def has_journal_references(self, price_id: int) -> bool:
        """Return True if any journal entry references the given price."""
        query = sa.select(sa.exists().where(Journal.price_id == price_id))
        return (await self.db.execute(query)).scalar_one()

    async def update_price(self, price_id: int, data: dict[str, Any]) -> Price:
        """Replace a price and its tiers.

        Note: data is modified in-place.
        """
        tiers_data = data.pop("tiers")
        price = (
            await self.db.execute(
                sa.update(Price).values(data).where(Price.id == price_id).returning(Price)
            )
        ).scalar_one()
        await self.db.execute(sa.delete(PriceTier).where(PriceTier.price_id == price_id))
        for tier in tiers_data:
            await self.db.execute(sa.insert(PriceTier).values(price_id=price_id, **tier))
        await self.db.flush()
        # Refresh to load the tiers relationship
        await self.db.refresh(price, attribute_names=["tiers"])
        return price

    async def set_price_valid_to(self, price_id: int, valid_to: datetime) -> Price:
        """Set the valid_to of the given price and return the updated row."""
        price = (
            await self.db.execute(
                sa.update(Price)
                .values(valid_to=valid_to)
                .where(Price.id == price_id)
                .returning(Price)
            )
        ).scalar_one()
        # Refresh to load the tiers relationship
        await self.db.refresh(price, attribute_names=["tiers"])
        return price

    async def add_price(self, data: dict[str, Any]) -> Price:
        """Add a price for the specified vlab, or as the default price if vlab is None.

        Any other pre-existing price for the same service and vlab isn't invalidated.

        Note: data is modified in-place.
        """
        tiers_data = data.pop("tiers")
        price = (await self.db.execute(sa.insert(Price).values(data).returning(Price))).scalar_one()
        for tier in tiers_data:
            await self.db.execute(sa.insert(PriceTier).values(price_id=price.id, **tier))
        await self.db.flush()
        # Refresh to load the tiers relationship
        await self.db.refresh(price, attribute_names=["tiers"])
        return price
