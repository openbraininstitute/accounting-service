"""Price service."""

from decimal import Decimal

from app.db.model import Discount, Price, PriceTier
from app.errors import ensure_result
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, EstimateCostOut, EstimateOneshotCostIn
from app.service.usage import calculate_oneshot_usage_value
from app.utils import utcnow


def _iter_cost(tiers: list[PriceTier], start: int, end: int) -> Decimal:
    """Return the usage cost from start to end by iterating over tiers.

    Each tier's fixed_cost is added once when the usage enters that tier.
    Each tier's multiplier applies to the portion of usage within that tier's range.
    """
    cost = Decimal(0)
    for tier in tiers:
        if end <= tier.min_quantity:
            break
        tier_start = max(start, tier.min_quantity)
        tier_end = end if tier.max_quantity is None else min(end, tier.max_quantity)
        if tier_start >= tier_end:
            continue
        if start <= tier.min_quantity:
            cost += tier.fixed_cost
        cost += tier.multiplier * (tier_end - tier_start)
    return cost


def calculate_cost(
    price: Price,
    *,
    previous_usage: int,
    current_usage: int,
    discount: Discount | None,
) -> Decimal:
    """Return the incremental cost between previous_usage and current_usage.

    Args:
        price: the price with tiers.
        previous_usage: cumulative usage already charged (0 for first charge).
        current_usage: cumulative usage including the new increment.
        discount: optional discount to apply to the final cost, not to the separate cost components.
    """
    cost = _iter_cost(price.tiers, start=previous_usage, end=current_usage)
    if discount:
        cost *= Decimal(1) - discount.discount
    return cost


async def add_price(repos: RepositoryGroup, price_request: AddPriceIn) -> Price:
    """Add a price."""
    if price_request.vlab_id:
        with ensure_result(error_message="Virtual lab not found"):
            await repos.account.get_vlab_account(vlab_id=price_request.vlab_id)
    return await repos.price.add_price(price_request.model_dump())


async def estimate_oneshot_cost(
    repos: RepositoryGroup, estimate_request: EstimateOneshotCostIn
) -> EstimateCostOut:
    """Estimate the cost for a oneshot job."""
    # Get vlab_id from proj_id
    with ensure_result(error_message="Project not found"):
        accounts = await repos.account.get_accounts_by_proj_id(proj_id=estimate_request.proj_id)
    vlab_id = accounts.vlab.id

    # Get price
    usage_datetime = utcnow()
    price = await repos.price.get_price(
        vlab_id=vlab_id,
        service_type=estimate_request.type,
        service_subtype=estimate_request.subtype,
        usage_datetime=usage_datetime,
    )

    # Get discount if applicable
    discount = await repos.discount.get_current_vlab_discount(vlab_id)

    # Calculate usage value
    usage_value = calculate_oneshot_usage_value(count=estimate_request.count)

    # Calculate cost
    cost = calculate_cost(
        price=price,
        previous_usage=0,
        current_usage=usage_value,
        discount=discount,
    )

    return EstimateCostOut(cost=cost)
