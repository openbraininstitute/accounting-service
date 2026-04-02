"""Charge for oneshot jobs."""

from datetime import datetime

from app.constants import D0, TransactionType
from app.db.session import SessionFactory
from app.logger import L
from app.repository.group import RepositoryGroup
from app.schema.domain import ChargeOneshotResult, StartedJob
from app.service.price import calculate_cost
from app.service.usage import calculate_oneshot_usage_value


async def _charge_generic(
    repos: RepositoryGroup,
    job: StartedJob,
    *,
    charging_at: datetime,
    reason: str,
) -> None:
    accounts = await repos.account.get_accounts_by_proj_id(proj_id=job.proj_id)
    price = await repos.price.get_price(
        vlab_id=accounts.vlab.id,
        service_type=job.service_type,
        service_subtype=job.service_subtype,
        usage_datetime=job.reserved_at or job.started_at,
    )
    discount = await repos.discount.get_current_vlab_discount(accounts.vlab.id)
    discount_id = None if not discount else discount.id
    usage_value = calculate_oneshot_usage_value(
        count=job.usage_params["count"],
    )
    total_amount = calculate_cost(
        price=price,
        discount=discount,
        previous_usage=0,
        current_usage=usage_value,
        include_fixed_cost=True,
    )
    if total_amount < 0:
        err = f"Total amount for job {job.id} is negative: {total_amount}"
        raise RuntimeError(err)
    remaining_reservation = await repos.ledger.get_remaining_reservation_for_job(
        job_id=job.id, account_id=accounts.rsv.id, raise_if_negative=True
    )
    reservation_amount_to_be_charged = min(total_amount, remaining_reservation)
    project_amount_to_be_charged = max(total_amount - reservation_amount_to_be_charged, D0)
    remaining_reservation -= reservation_amount_to_be_charged
    if reservation_amount_to_be_charged > 0:
        await repos.ledger.insert_transaction(
            amount=reservation_amount_to_be_charged,
            debited_from=accounts.rsv.id,
            credited_to=accounts.sys.id,
            transaction_datetime=charging_at,
            transaction_type=TransactionType.CHARGE_ONESHOT,
            job_id=job.id,
            price_id=price.id,
            discount_id=discount_id,
            properties={"reason": f"{reason}:charge_reservation"},
        )
    if project_amount_to_be_charged > 0:
        await repos.ledger.insert_transaction(
            amount=project_amount_to_be_charged,
            debited_from=accounts.proj.id,
            credited_to=accounts.sys.id,
            transaction_datetime=charging_at,
            transaction_type=TransactionType.CHARGE_ONESHOT,
            job_id=job.id,
            price_id=price.id,
            discount_id=discount_id,
            properties={"reason": f"{reason}:charge_project"},
        )
    if remaining_reservation > 0:
        await repos.ledger.insert_transaction(
            amount=remaining_reservation,
            debited_from=accounts.rsv.id,
            credited_to=accounts.proj.id,
            transaction_datetime=charging_at,
            transaction_type=TransactionType.RELEASE,
            job_id=job.id,
            price_id=price.id,
            discount_id=discount_id,
            properties={"reason": f"{reason}:release_reservation"},
        )
    await repos.job.update_job(
        job_id=job.id,
        vlab_id=accounts.vlab.id,
        proj_id=accounts.proj.id,
        last_charged_at=charging_at,
    )


async def charge_oneshot(session_factory: SessionFactory) -> ChargeOneshotResult:
    """Charge for oneshot jobs.

    Args:
        session_factory: async context manager that yields an AsyncSession.
    """
    result = ChargeOneshotResult()
    async with session_factory() as db:
        jobs = await RepositoryGroup(db=db).job.get_oneshot_to_be_charged()
    for job in jobs:
        try:
            async with session_factory() as db:
                repos = RepositoryGroup(db=db)
                await _charge_generic(
                    repos, job, charging_at=job.started_at, reason="finished_uncharged"
                )
        except Exception:  # noqa: BLE001
            L.exception("Error processing oneshot job {}", job.id)
            result.failure += 1
        else:
            result.success += 1
    return result
