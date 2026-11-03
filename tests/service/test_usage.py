from decimal import Decimal

import pytest

from app.service import usage as test_module


@pytest.fixture
def _weights(monkeypatch):
    """Set a known instance_type weight map for the duration of a test."""
    monkeypatch.setattr(
        test_module.settings,
        "LONGRUN_INSTANCE_TYPE_WEIGHTS",
        {
            "small": Decimal(1),
            "medium": Decimal(2),
            "large": Decimal(3),
            "fullnode": Decimal(4),
        },
    )


@pytest.mark.usefixtures("_weights")
@pytest.mark.parametrize(
    ("instance_type", "expected"),
    [
        ("small", 3600),
        ("medium", 7200),
        ("large", 10800),
        ("fullnode", 14400),
    ],
)
def test_longrun_usage_value_applies_weight(instance_type, expected):
    # 1 instance for 1 hour, scaled by the per-instance_type weight.
    result = test_module.calculate_longrun_usage_value(
        instances=1, instance_type=instance_type, duration=3600
    )
    assert result == expected


@pytest.mark.usefixtures("_weights")
@pytest.mark.parametrize("instance_type", [None, "", "unknown"])
def test_longrun_usage_value_unweighted_defaults_to_one(instance_type):
    # None, empty, or an instance_type absent from the map uses weight 1,
    # preserving the pre-weighting behaviour.
    result = test_module.calculate_longrun_usage_value(
        instances=1, instance_type=instance_type, duration=3600
    )
    assert result == 3600


@pytest.mark.usefixtures("_weights")
def test_longrun_usage_value_scales_with_instances_and_weight():
    # instances and weight both scale the billed usage: 2 * 100 * 3 (large).
    result = test_module.calculate_longrun_usage_value(
        instances=2, instance_type="large", duration=100
    )
    assert result == 600


def test_default_instance_type_weights_match_agreed_pricing():
    """The shipped default weights encode the agreed per-size pricing
    (S x1, M x2, L x3, XL x4), used as-is unless overridden by env."""
    weights = test_module.settings.LONGRUN_INSTANCE_TYPE_WEIGHTS
    assert weights == {
        "small": Decimal(1),
        "medium": Decimal(2),
        "large": Decimal(3),
        "fullnode": Decimal(4),
    }
