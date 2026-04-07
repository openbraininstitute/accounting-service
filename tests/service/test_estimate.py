from decimal import Decimal

import pytest

from app.constants import ServiceSubtype, ServiceType
from app.errors import ApiError
from app.repository.group import RepositoryGroup
from app.schema.api import EstimateOneshotCostIn
from app.service import price as test_module

from tests.constants import UUIDS


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
