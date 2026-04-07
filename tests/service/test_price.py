from datetime import datetime
from decimal import Decimal

import pytest

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Discount, Price, PriceTier
from app.errors import ApiError
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn
from app.service import price as test_module

from tests.constants import UUIDS

_DISCOUNT_20 = Discount(
    id=1,
    vlab_id=UUIDS.VLAB[0],
    valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
    valid_to=None,
    discount=Decimal("0.2"),
)


def _make_price(tiers):
    """Helper to create a Price with tiers for unit tests."""
    price = Price(
        id=1,
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        vlab_id=None,
    )
    price.tiers = sorted(
        [PriceTier(price_id=1, **t) for t in tiers],
        key=lambda t: t.min_quantity,
    )
    return price


def _tier(min_q, max_q, fixed, mult):
    return {
        "min_quantity": min_q,
        "max_quantity": max_q,
        "fixed_cost": Decimal(str(fixed)),
        "multiplier": Decimal(str(mult)),
    }


@pytest.mark.parametrize(
    ("tiers", "previous_usage", "current_usage", "discount", "expected"),
    [
        pytest.param(
            [_tier(0, None, 0, "0.01")],
            0,
            100,
            None,
            "1.0",  # 0.01 * 100
            id="single_tier",
        ),
        pytest.param(
            [_tier(0, None, "1.5", "0.01")],
            0,
            100,
            None,
            "2.5",  # 1.5 + 0.01 * 100
            id="single_tier_with_fixed_cost",
        ),
        pytest.param(
            [_tier(0, None, 0, "0.01")],
            0,
            100,
            _DISCOUNT_20,
            "0.8",  # 0.01 * 100 * 0.8
            id="single_tier_with_discount",
        ),
        pytest.param(
            [_tier(0, None, "1.5", "0.01")],
            0,
            100,
            _DISCOUNT_20,
            "2.0",  # (1.5 + 0.01 * 100) * 0.8
            id="single_tier_with_fixed_cost_and_discount",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, None, 0, "0.05")],
            0,
            150,
            None,
            "12.5",  # 0.10 * 100 + 0.05 * 50
            id="two_tiers_full_range",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, None, 0, "0.05")],
            0,
            50,
            None,
            "5.0",  # 0.10 * 50
            id="two_tiers_within_first",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, None, 0, "0.05")],
            60,
            90,
            None,
            "3.0",  # 0.10 * (90 - 60)
            id="two_tiers_incremental_same_tier",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, None, 0, "0.05")],
            80,
            150,
            None,
            "4.5",  # 0.10 * (100 - 80) + 0.05 * (150 - 100)
            id="two_tiers_incremental_crossing_boundary",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, None, 0, "0.05")],
            120,
            200,
            None,
            "4.0",  # 0.05 * (200 - 120)
            id="two_tiers_incremental_both_in_second",
        ),
        pytest.param(
            [_tier(0, 100, 0, "0.10"), _tier(100, 500, 0, "0.05"), _tier(500, None, 0, "0.01")],
            80,
            600,
            None,
            "23.0",  # 0.10 * (100 - 80) + 0.05 * (500 - 100) + 0.01 * (600 - 500)
            id="three_tiers_incremental_crossing_two_boundaries",
        ),
        pytest.param(
            [_tier(0, 21, 5, 0), _tier(21, None, 45, 0)],
            0,
            10,
            None,
            "5",  # fixed 5
            id="step_function_first_tier",
        ),
        pytest.param(
            [_tier(0, 21, 5, 0), _tier(21, None, 45, 0)],
            0,
            20,
            None,
            "5",  # fixed 5
            id="step_function_first_tier_boundary",
        ),
        pytest.param(
            [_tier(0, 21, 5, 0), _tier(21, None, 45, 0)],
            0,
            100,
            None,
            "50",  # fixed 5 + fixed 45
            id="step_function_second_tier",
        ),
    ],
)
def test_calculate_cost(tiers, previous_usage, current_usage, discount, expected):
    price = _make_price(tiers)
    result = test_module.calculate_cost(
        price=price,
        previous_usage=previous_usage,
        current_usage=current_usage,
        discount=discount,
    )
    assert result == Decimal(expected)


@pytest.mark.usefixtures("_db_account")
async def test_add_price(db):
    repos = RepositoryGroup(db)
    price_request = AddPriceIn(
        service_type=ServiceType.ONESHOT,
        service_subtype=ServiceSubtype.ML_LLM,
        valid_from=datetime.fromisoformat("2024-01-01T00:00:00Z"),
        valid_to=None,
        vlab_id=None,
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "fixed_cost": 0,
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
        vlab_id=UUIDS.VLAB[0],
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "fixed_cost": 0,
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
        vlab_id=UUIDS.VLAB[2],
        tiers=[
            {
                "min_quantity": 0,
                "max_quantity": None,
                "fixed_cost": 0,
                "multiplier": "0.00001",
            }
        ],
    )
    with pytest.raises(ApiError, match="Virtual lab not found"):
        await test_module.add_price(repos, price_request)
