from datetime import datetime
from decimal import Decimal

import pytest

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Discount, Price
from app.errors import ApiError
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, EstimateOneshotCostIn
from app.service import price as test_module

from tests.constants import UUIDS


class TestCalculateCost:
    @staticmethod
    def test_without_fixed_cost_or_discount():
        price = Price(
            id=1,
            service_type=ServiceType.ONESHOT,
            service_subtype=ServiceSubtype.ML_LLM,
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            fixed_cost=Decimal("1.5"),
            multiplier=Decimal("0.01"),
            vlab_id=None,
        )
        result = test_module.calculate_cost(
            price=price, usage_value=100, include_fixed_cost=False, discount=None
        )
        assert result == Decimal("1.0")

    @staticmethod
    def test_with_fixed_cost():
        price = Price(
            id=1,
            service_type=ServiceType.ONESHOT,
            service_subtype=ServiceSubtype.ML_LLM,
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            fixed_cost=Decimal("1.5"),
            multiplier=Decimal("0.01"),
            vlab_id=None,
        )
        result = test_module.calculate_cost(
            price=price, usage_value=100, include_fixed_cost=True, discount=None
        )
        assert result == Decimal("2.5")

    @staticmethod
    def test_with_discount():
        price = Price(
            id=1,
            service_type=ServiceType.ONESHOT,
            service_subtype=ServiceSubtype.ML_LLM,
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            fixed_cost=Decimal(0),
            multiplier=Decimal("0.01"),
            vlab_id=None,
        )
        discount = Discount(
            id=1,
            vlab_id=UUIDS.VLAB[0],
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            discount=Decimal("0.2"),
        )
        result = test_module.calculate_cost(
            price=price, usage_value=100, include_fixed_cost=False, discount=discount
        )
        assert result == Decimal("0.8")

    @staticmethod
    def test_with_fixed_cost_and_discount():
        price = Price(
            id=1,
            service_type=ServiceType.ONESHOT,
            service_subtype=ServiceSubtype.ML_LLM,
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            fixed_cost=Decimal("1.5"),
            multiplier=Decimal("0.01"),
            vlab_id=None,
        )
        discount = Discount(
            id=1,
            vlab_id=UUIDS.VLAB[0],
            valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
            valid_to=None,
            discount=Decimal("0.2"),
        )
        result = test_module.calculate_cost(
            price=price, usage_value=100, include_fixed_cost=True, discount=discount
        )
        assert result == Decimal("2.0")


@pytest.mark.usefixtures("_db_account")
async def test_add_price(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=Decimal(0),
        multiplier=Decimal("0.00001"),
        vlab_id=None,
    )
    result = await test_module.add_price(repos, price_request)
    assert result.service_type == ServiceType.ONESHOT
    assert result.multiplier == Decimal("0.00001")


@pytest.mark.usefixtures("_db_account")
async def test_add_price_with_vlab_id(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=Decimal(0),
        multiplier=Decimal("0.00001"),
        vlab_id=UUIDS.VLAB[0],
    )
    result = await test_module.add_price(repos, price_request)
    assert result.vlab_id == UUIDS.VLAB[0]


@pytest.mark.usefixtures("_db_account")
async def test_add_price_invalid_vlab(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=Decimal(0),
        multiplier=Decimal("0.00001"),
        vlab_id=UUIDS.VLAB[2],
    )
    with pytest.raises(ApiError, match="Virtual lab not found"):
        await test_module.add_price(repos, price_request)


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost(db):
    repos = RepositoryGroup(db)
    estimate_request = EstimateOneshotCostIn(
        proj_id=UUIDS.PROJ[0],
        type=ServiceType.ONESHOT,
        subtype=ServiceSubtype.ML_LLM,
        count=100,
    )
    result = await test_module.estimate_oneshot_cost(repos, estimate_request)
    assert result.cost == Decimal("0.001")


async def test_estimate_oneshot_cost_invalid_project(db):
    repos = RepositoryGroup(db)
    estimate_request = EstimateOneshotCostIn(
        proj_id=UUIDS.PROJ[0],
        type=ServiceType.ONESHOT,
        subtype=ServiceSubtype.ML_LLM,
        count=100,
    )
    with pytest.raises(ApiError, match="Project not found"):
        await test_module.estimate_oneshot_cost(repos, estimate_request)
