"""Charge for longrun jobs."""

from datetime import datetime
from decimal import Decimal

from app.constants import D0, TransactionType
from app.db.utils import try_nested
from app.logger import L
from app.repository.group import RepositoryGroup
from app.schema.domain import ChargeLongrunResult, StartedJob
from app.service.price import calculate_cost
from app.service.usage import calculate_longrun_usage_value
from app.utils import utcnow


async def _charge_generic(
    repos: RepositoryGroup,
    job: StartedJob,
    *,
    charge_start: datetime,
    charge_end: datetime,
    transaction_datetime: datetime,
    include_fixed_cost: bool,
    release_reservation: bool,
    reason: str,
    min_charging_interval: float = 0.0,
    min_charging_amount: Decimal = D0,
    expired: bool = False,
) -> None:
    total_seconds = int((charge_end - charge_start).total_seconds())
    if total_seconds < min_charging_interval:
        L.debug(
            "Not charging job {}: elapsed seconds since last charge: {:.3f}",
            job.id,
            total_seconds,
        )
        return
    accounts = await repos.account.get_accounts_by_proj_id(proj_id=job.proj_id)
    price = await repos.price.get_price(
        vlab_id=accounts.vlab.id,
        service_type=job.service_type,
        service_subtype=job.service_subtype,
        usage_datetime=job.reserved_at or job.started_at,
    )
    usage_value = calculate_longrun_usage_value(
        instances=job.usage_params["instances"],
        instance_type=job.usage_params.get("instance_type"),
        duration=total_seconds,
    )
    total_amount = calculate_cost(
        price=price,
        usage_value=usage_value,
        include_fixed_cost=include_fixed_cost,
    )
    if abs(total_amount) < min_charging_amount:
        L.debug(
            "Not charging job {}: calculated amount too low: {:.6f}",
            job.id,
            total_amount,
        )
        return
    remaining_reservation = await repos.ledger.get_remaining_reservation_for_job(
        job_id=job.id, account_id=accounts.rsv.id, raise_if_negative=True
    )
    if total_amount > 0:
        reservation_amount_to_be_charged = min(total_amount, remaining_reservation)
        project_amount_to_be_charged = max(total_amount - reservation_amount_to_be_charged, D0)
        remaining_reservation -= reservation_amount_to_be_charged
    else:
        L.info("The job {} has been previously overcharged for {:.6f}", job.id, total_amount)
        reservation_amount_to_be_charged = D0
        project_amount_to_be_charged = total_amount

    if reservation_amount_to_be_charged > 0:
        await repos.ledger.insert_transaction(
            amount=reservation_amount_to_be_charged,
            debited_from=accounts.rsv.id,
            credited_to=accounts.sys.id,
            transaction_datetime=transaction_datetime,
            transaction_type=TransactionType.CHARGE_LONGRUN,
            job_id=job.id,
            price_id=price.id,
            properties={"reason": f"{reason}:charge_reservation"},
        )
    if project_amount_to_be_charged > 0:
        await repos.ledger.insert_transaction(
            amount=project_amount_to_be_charged,
            debited_from=accounts.proj.id,
            credited_to=accounts.sys.id,
            transaction_datetime=transaction_datetime,
            transaction_type=TransactionType.CHARGE_LONGRUN,
            job_id=job.id,
            price_id=price.id,
            properties={"reason": f"{reason}:charge_project"},
        )
    elif project_amount_to_be_charged < 0:
        await repos.ledger.insert_transaction(
            amount=project_amount_to_be_charged * -1,
            debited_from=accounts.sys.id,
            credited_to=accounts.proj.id,
            transaction_datetime=transaction_datetime,
            transaction_type=TransactionType.REFUND,
            job_id=job.id,
            price_id=price.id,
            properties={"reason": f"{reason}:refund_project"},
        )
    if release_reservation and remaining_reservation > 0:
        await repos.ledger.insert_transaction(
            amount=remaining_reservation,
            debited_from=accounts.rsv.id,
            credited_to=accounts.proj.id,
            transaction_datetime=transaction_datetime,
            transaction_type=TransactionType.RELEASE,
            job_id=job.id,
            price_id=price.id,
            properties={"reason": f"{reason}:release_reservation"},
        )
    await repos.job.update_job(
        job_id=job.id,
        vlab_id=accounts.vlab.id,
        proj_id=accounts.proj.id,
        last_charged_at=charge_end,
        **(
            {
                "finished_at": charge_end,
                "cancelled_at": charge_end,
            }
            if expired
            else {}
        ),
    )


async def charge_longrun(  # noqa: C901
    repos: RepositoryGroup,
    min_charging_interval: float = 0.0,
    min_charging_amount: Decimal = D0,
    expiration_interval: float = 3600,
    transaction_datetime: datetime | None = None,
) -> ChargeLongrunResult:
    """Charge for longrun jobs.

    Args:
        repos: repository group instance.
        min_charging_interval: minimum interval between charges for running jobs.
            It doesn't affect finished jobs.
        min_charging_amount: minimum amount of money to be charged for running jobs.
            It doesn't affect finished jobs.
        expiration_interval: time since last_alive_at, after which the job is considered expired.
        transaction_datetime: datetime of the transaction, or None to use the current timestamp.
            If the job is still running, it's used also to calculate the duration to be charged.
    """

    def _on_error() -> None:
        L.exception("Error processing longrun job {}", job.id)
        result.failure += 1

    def _on_success() -> None:
        result.success += 1

    now = transaction_datetime or utcnow()
    result = ChargeLongrunResult()
    jobs = await repos.job.get_longrun_to_be_charged()
    for job in jobs:
        async with try_nested(repos.db, on_error=_on_error, on_success=_on_success):
            match job:
                case StartedJob(
                    last_alive_at=datetime() as last_alive_at,
                    last_charged_at=None,
                    finished_at=None,
                ) if ((now - last_alive_at).total_seconds() > expiration_interval):
                    # Cancel the expired job and charge the user for the first and last time
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=job.started_at,
                        charge_end=now,
                        transaction_datetime=now,
                        include_fixed_cost=True,
                        release_reservation=True,
                        reason="expired_uncharged",
                        expired=True,
                    )
                    result.expired_uncharged += 1
                case StartedJob(
                    last_alive_at=datetime() as last_alive_at,
                    last_charged_at=datetime() as last_charged_at,
                    finished_at=None,
                ) if ((now - last_alive_at).total_seconds() > expiration_interval):
                    # Cancel the expired job and charge the user for the last time
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=last_charged_at,
                        charge_end=now,
                        transaction_datetime=now,
                        include_fixed_cost=False,
                        release_reservation=True,
                        reason="expired_charged",
                        expired=True,
                    )
                    result.expired_charged += 1
                case StartedJob(last_charged_at=None, finished_at=None):
                    # Charge fixed cost and first running time, set last_charged_at=now
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=job.started_at,
                        charge_end=now,
                        transaction_datetime=now,
                        include_fixed_cost=True,
                        release_reservation=False,
                        reason="unfinished_uncharged",
                        min_charging_interval=min_charging_interval,
                        min_charging_amount=min_charging_amount,
                    )
                    result.unfinished_uncharged += 1
                case StartedJob(last_charged_at=datetime() as last_charged_at, finished_at=None):
                    # Charge running time since the last charge, set last_charged_at=now
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=last_charged_at,
                        charge_end=now,
                        transaction_datetime=now,
                        include_fixed_cost=False,
                        release_reservation=False,
                        reason="unfinished_charged",
                        min_charging_interval=min_charging_interval,
                        min_charging_amount=min_charging_amount,
                    )
                    result.unfinished_charged += 1
                case StartedJob(last_charged_at=None, finished_at=datetime() as finished_at):
                    # Charge fixed costs and full running time, set last_charged_at=finished_at,
                    # release reservation
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=job.started_at,
                        charge_end=finished_at,
                        transaction_datetime=now,
                        include_fixed_cost=True,
                        release_reservation=True,
                        reason="finished_uncharged",
                    )
                    result.finished_uncharged += 1
                case StartedJob(last_charged_at=last_charged_at, finished_at=finished_at) if (
                    last_charged_at and finished_at and last_charged_at < finished_at
                ):
                    # Charge remaining running time, set last_charged_at=finished_at,
                    # release reservation
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=last_charged_at,
                        charge_end=finished_at,
                        transaction_datetime=now,
                        include_fixed_cost=False,
                        release_reservation=True,
                        reason="finished_charged",
                    )
                    result.finished_charged += 1
                case StartedJob(last_charged_at=last_charged_at, finished_at=finished_at) if (
                    last_charged_at and finished_at and last_charged_at > finished_at
                ):
                    # Refund extra time already charged, set last_charged_at=finished_at, release
                    # reservation. This can happen:
                    # - if the event notifying the completion of the job has been processed late,
                    # and some amount of money has already been charged by the periodic charger.
                    # - if the event notifying the completion of the job has been processed after
                    # the job has been marked as expired.
                    await _charge_generic(
                        repos,
                        job,
                        charge_start=last_charged_at,
                        charge_end=finished_at,
                        transaction_datetime=now,
                        include_fixed_cost=False,
                        release_reservation=True,
                        reason="finished_overcharged",
                    )
                    result.finished_overcharged += 1
                case _:
                    err = f"Pattern not matched for job {job.id}"
                    raise ValueError(err)
    return result
