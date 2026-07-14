import pytest
from pydantic import ValidationError

from app import config as test_module


def test_configs():
    configs = test_module.settings

    assert configs.APP_NAME == "accounting-service"
    assert (
        "postgresql+asyncpg://accounting_service:accounting_service@"
        f"{configs.DB_HOST}:{configs.DB_PORT}/accounting_service"
    ) == configs.DB_URI


@pytest.mark.parametrize(
    "name",
    ["SENTRY_TRACES_SAMPLE_RATE", "SENTRY_PROFILE_SESSION_SAMPLE_RATE"],
)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_configs_invalid_sentry_sample_rate(name, value):
    with pytest.raises(ValidationError, match=name):
        test_module.Settings(**{name: value})
