import sqlalchemy as sa
from sqlalchemy import text

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Base, Job, Journal, Ledger

from tests.constants import PROJ_ID, VLAB_ID

DEFAULT_PRICE_TIER = {
    "min_quantity": 0,
    "max_quantity": None,
    "fixed_cost": "0",
    "multiplier": "0.00001",
}


def make_price_data(**overrides):
    """Return a default valid price API payload, with optional overrides."""
    return {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "vlab_id": None,
        "tiers": [DEFAULT_PRICE_TIER],
    } | overrides


def assert_validation_error(response, *, error_type, msg=None, loc=None):
    """Assert that the response is a 422 validation error with the expected details."""
    assert response.status_code == 422
    detail = response.json()["details"][0]
    assert detail["type"] == error_type
    if msg is not None:
        assert msg in detail["msg"]
    if loc is not None:
        assert detail["loc"] == loc


async def truncate_tables(session):
    query = text(f"""TRUNCATE {",".join(Base.metadata.tables)} RESTART IDENTITY CASCADE""")
    await session.execute(query)
    await session.commit()


async def _insert_oneshot_job(db, job_id, reserved_count, reserved_at):
    await db.execute(
        sa.insert(Job),
        [
            {
                "id": job_id,
                "vlab_id": VLAB_ID,
                "proj_id": PROJ_ID,
                "service_type": ServiceType.ONESHOT,
                "service_subtype": ServiceSubtype.ML_LLM,
                "reserved_at": reserved_at,
                "started_at": None,
                "last_alive_at": None,
                "last_charged_at": None,
                "finished_at": None,
                "cancelled_at": None,
                "reservation_params": {"count": int(reserved_count)},
            }
        ],
    )


async def _insert_longrun_job(db, job_id, instances, started_at, last_charged_at=None):
    await db.execute(
        sa.insert(Job),
        [
            {
                "id": job_id,
                "vlab_id": VLAB_ID,
                "proj_id": PROJ_ID,
                "service_type": ServiceType.LONGRUN,
                "service_subtype": ServiceSubtype.SINGLE_CELL_SIM,
                "started_at": started_at,
                "last_alive_at": started_at,
                "last_charged_at": last_charged_at,
                "finished_at": None,
                "cancelled_at": None,
                "usage_params": {
                    "instances": int(instances),
                    "instance_type": None,
                },
            }
        ],
    )


async def _insert_storage_job(db, job_id, size, started_at):
    await db.execute(
        sa.insert(Job),
        [
            {
                "id": job_id,
                "vlab_id": VLAB_ID,
                "proj_id": PROJ_ID,
                "service_type": ServiceType.STORAGE,
                "service_subtype": ServiceSubtype.STORAGE,
                "started_at": started_at,
                "last_alive_at": started_at,
                "last_charged_at": None,
                "finished_at": None,
                "cancelled_at": None,
                "usage_params": {"size": int(size)},
            }
        ],
    )


async def _update_job(db, job_id, **kwargs):
    return (
        await db.execute(sa.update(Job).values(**kwargs).where(Job.id == job_id).returning(Job))
    ).scalar_one()


async def _select_job(db, job_id):
    return (await db.execute(sa.select(Job).where(Job.id == job_id))).scalar_one_or_none()


async def _select_ledger_rows(db, job_id):
    return (
        await db.execute(
            sa.select(
                Journal.transaction_datetime,
                Journal.transaction_type,
                Journal.job_id,
                Journal.price_id,
                Journal.properties,
                Ledger.account_id,
                Ledger.amount,
            )
            .join_from(Journal, Ledger)
            .where(Journal.job_id == job_id)
            .order_by(Ledger.id)
        )
    ).all()
