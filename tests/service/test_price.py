from datetime import datetime
from decimal import Decimal

import pytest

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Discount, Price, PriceTier
from app.errors import ApiError
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, EstimateOneshotCostIn
from app.service import price as test_module

from tests.constants import UUIDS

_DISCOUNT = Discount(
    id=1,
    vlab_id=UUIDS.VLAB[0],
    valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
    valid_to=None,
    discount=Decimal("0.2"),
)

_SINGLE_TIER = [
    {
        "min_quantity": 0,
        "max_quantity": None,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.01"),
    },
]

_TWO_TIERS = [
    {
        "min_quantity": 0,
        "max_quantity": 100,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.10"),
    },
    {
        "min_quantity": 100,
        "max_quantity": None,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.05"),
    },
]

_THREE_TIERS = [
    {
        "min_quantity": 0,
        "max_quantity": 100,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.10"),
    },
    {
        "min_quantity": 100,
        "max_quantity": 500,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.05"),
    },
    {
        "min_quantity": 500,
        "max_quantity": None,
        "base_cost": Decimal(0),
        "multiplier": Decimal("0.01"),
    },
]


def _make_price(*, fixed_cost, tiers):
    """Helper to create a Price with tiers for unit tests."""
    price = Price(
        id=1,
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=Decimal(str(fixed_cost)),
        vlab_id=None,
    )
    price.tiers = sorted(
        [PriceTier(price_id=1, **t) for t in tiers],
        key=lambda t: t.min_quantity,
    )
    return price


def test_calculate_cost_without_fixed_cost_or_discount():
    price = _make_price(fixed_cost="1.5", tiers=_SINGLE_TIER)
    result = test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=100, include_fixed_cost=False, discount=None
    )
    assert result == Decimal("1.0")


def test_calculate_cost_with_fixed_cost():
    price = _make_price(fixed_cost="1.5", tiers=_SINGLE_TIER)
    result = test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=100, include_fixed_cost=True, discount=None
    )
    assert result == Decimal("2.5")


def test_calculate_cost_with_discount():
    price = _make_price(fixed_cost=0, tiers=_SINGLE_TIER)
    result = test_module.calculate_cost(
        price=price,
        previous_usage=0,
        current_usage=100,
        include_fixed_cost=False,
        discount=_DISCOUNT,
    )
    assert result == Decimal("0.8")


def test_calculate_cost_with_fixed_cost_and_discount():
    price = _make_price(fixed_cost="1.5", tiers=_SINGLE_TIER)
    result = test_module.calculate_cost(
        price=price,
        previous_usage=0,
        current_usage=100,
        include_fixed_cost=True,
        discount=_DISCOUNT,
    )
    assert result == Decimal("2.0")


def test_calculate_cost_multiple_tiers_full():
    price = _make_price(fixed_cost=0, tiers=_TWO_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=150, include_fixed_cost=False, discount=None
    )
    # From 0 to 150: 10 + 0.05 * 50 = 12.5
    assert result == Decimal("12.5")


def test_calculate_cost_multiple_tiers_within_first_tier():
    price = _make_price(fixed_cost=0, tiers=_TWO_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=50, include_fixed_cost=False, discount=None
    )
    # From 0 to 50: 0 + 0.10 * 50 = 5.0
    assert result == Decimal("5.0")


def test_calculate_cost_incremental_within_same_tier():
    # Previous charge covered 0-60, now charging 60-90, both in tier 1
    price = _make_price(fixed_cost=0, tiers=_TWO_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=60, current_usage=90, include_fixed_cost=False, discount=None
    )
    # tier_cost(90) - tier_cost(60) = 9.0 - 6.0 = 3.0
    assert result == Decimal("3.0")


def test_calculate_cost_incremental_crossing_tier_boundary():
    # Previous charge covered 0-80, now charging 80-150, crossing from tier 1 to tier 2
    price = _make_price(fixed_cost=0, tiers=_TWO_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=80, current_usage=150, include_fixed_cost=False, discount=None
    )
    # tier_cost(150) = 10 + 0.05*50 = 12.5
    # tier_cost(80)  = 0 + 0.10*80 = 8.0
    # incremental = 12.5 - 8.0 = 4.5
    assert result == Decimal("4.5")


def test_calculate_cost_incremental_both_in_second_tier():
    # Previous charge covered 0-120, now charging 120-200
    price = _make_price(fixed_cost=0, tiers=_TWO_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=120, current_usage=200, include_fixed_cost=False, discount=None
    )
    # tier_cost(200) = 10 + 0.05*100 = 15
    # tier_cost(120) = 10 + 0.05*20 = 11
    # incremental = 15 - 11 = 4
    assert result == Decimal("4.0")


def test_calculate_cost_three_tiers_incremental():
    # Tier 1: 0-100 at 0.10 => accumulated = 10
    # Tier 2: 100-500 at 0.05 => accumulated = 10 + 400*0.05 = 30
    # Tier 3: 500+ at 0.01
    # Charge from 80 to 600, crossing two boundaries
    price = _make_price(fixed_cost="1.0", tiers=_THREE_TIERS)
    result = test_module.calculate_cost(
        price=price, previous_usage=80, current_usage=600, include_fixed_cost=False, discount=None
    )
    # tier_cost(600) = 30 + 0.01*100 = 31
    # tier_cost(80)  = 0 + 0.10*80 = 8
    # incremental = 31 - 8 = 23
    assert result == Decimal("23.0")


def test_calculate_cost_flat_step_function():
    # Up to 20 -> 5 credits, above 20 -> 50 credits
    # base_cost is incremental: tier 2 adds 45 on top of tier 1's 5
    price = _make_price(
        fixed_cost=0,
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": 21,
                "base_cost": Decimal(5),
                "multiplier": Decimal(0),
            },
            {
                "min_quantity": 21,
                "max_quantity": None,
                "base_cost": Decimal(45),
                "multiplier": Decimal(0),
            },
        ],
    )
    assert test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=10, include_fixed_cost=False, discount=None
    ) == Decimal(5)
    assert test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=20, include_fixed_cost=False, discount=None
    ) == Decimal(5)
    assert test_module.calculate_cost(
        price=price, previous_usage=0, current_usage=100, include_fixed_cost=False, discount=None
    ) == Decimal(50)


@pytest.mark.usefixtures("_db_account")
async def test_add_price(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=0,
        vlab_id=None,
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "base_cost": 0,
                "multiplier": "0.00001",
            }
        ],
    )
    result = await test_module.add_price(repos, price_request)
    assert result.service_type == ServiceType.ONESHOT
    assert len(result.tiers) == 1
    assert result.tiers[0].multiplier == Decimal("0.00001")


@pytest.mark.usefixtures("_db_account")
async def test_add_price_with_vlab_id(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        fixed_cost=0,
        vlab_id=UUIDS.VLAB[0],
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "base_cost": 0,
                "multiplier": "0.00001",
            }
        ],
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
        fixed_cost=0,
        vlab_id=UUIDS.VLAB[2],
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "base_cost": 0,
                "multiplier": "0.00001",
            }
        ],
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
