"""Charge for storage."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.constants import D0, TransactionType
from app.db.utils import try_nested
from app.logger import L
from app.repository.group import RepositoryGroup
from app.schema.domain import ChargeStorageResult, StartedJob
from app.service.price import calculate_cost
from app.service.usage import calculate_storage_usage_value
from app.utils import utcnow


def _get_price_per_gb_per_day() -> Decimal:
    # TODO: to be retrieved from db
    return round(Decimal("0.023") / 30, ndigits=10)


def _get_amount(total_seconds: float, total_bytes: float) -> Decimal:
    return round(
        Decimal(total_seconds / 24 / 3600 * total_bytes / 1024**3) * _get_price_per_gb_per_day(),
        ndigits=10,
    )


async def _charge_one(
    repos: RepositoryGroup,
    job: StartedJob,
    transaction_datetime: datetime,
    min_charging_interval: float,
    min_charging_amount: Decimal,
    properties: dict[str, Any] | None = None,
) -> None:
    charging_at = job.finished_at or transaction_datetime
    charging_start = job.last_charged_at or job.started_at
    total_seconds = int((charging_at - charging_start).total_seconds())
    if not job.finished_at and total_seconds < min_charging_interval:
        L.debug(
            "Not charging job {}: elapsed seconds since last charge: {}",
            job.id,
            total_seconds,
        )
        return
    accounts = await repos.account.get_accounts_by_proj_id(proj_id=job.proj_id)
    price = await repos.price.get_price(
        vlab_id=accounts.vlab.id,
        service_type=job.service_type,
        service_subtype=job.service_subtype,
        usage_datetime=charging_at,
    )
    discount = await repos.discount.get_current_vlab_discount(accounts.vlab.id)
    discount_id = None if not discount else discount.id
    usage_value = calculate_storage_usage_value(
        size=job.usage_params["size"],
        duration=total_seconds,
    )
    total_amount = calculate_cost(
        price=price, discount=discount, usage_value=usage_value, include_fixed_cost=False
    )
    if not job.finished_at and abs(total_amount) < min_charging_amount:
        L.debug(
            "Not charging job {}: calculated amount too low: {:.6f}",
            job.id,
            total_amount,
        )
        return
    await repos.ledger.insert_transaction(
        amount=total_amount,
        debited_from=accounts.proj.id,
        credited_to=accounts.sys.id,
        transaction_datetime=transaction_datetime,
        transaction_type=TransactionType.CHARGE_STORAGE,
        job_id=job.id,
        price_id=price.id,
        discount_id=discount_id,
        properties=properties,
    )
    await repos.job.update_job(
        job_id=job.id,
        vlab_id=accounts.vlab.id,
        proj_id=accounts.proj.id,
        last_charged_at=charging_at,
    )


async def charge_storage(
    repos: RepositoryGroup,
    jobs: Sequence[StartedJob],
    min_charging_interval: float = 0.0,
    min_charging_amount: Decimal = D0,
    transaction_datetime: datetime | None = None,
) -> ChargeStorageResult:
    """Charge for the storage and update the corresponding job.

    Args:
        repos: repository group instance.
        jobs: sequence of jobs to be processed, or None to select all the job not finished yet.
        min_charging_interval: minimum interval between charges for running jobs.
        min_charging_amount: minimum amount of money to be charged for running jobs.
        transaction_datetime: datetime of the transaction, or None to use the current timestamp.
            If the job is still running, it's used also to calculate the duration to be charged.
    """

    def _on_error() -> None:
        L.exception("Error processing storage job {}", job.id)
        result.failure += 1

    def _on_success() -> None:
        result.success += 1

    now = transaction_datetime or utcnow()
    result = ChargeStorageResult()
    for job in jobs:
        async with try_nested(repos.db, on_error=_on_error, on_success=_on_success):
            await _charge_one(
                repos=repos,
                job=job,
                transaction_datetime=now,
                min_charging_interval=min_charging_interval,
                min_charging_amount=min_charging_amount,
            )
    return result
