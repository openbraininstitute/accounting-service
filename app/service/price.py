"""Price service."""

from decimal import Decimal

from app.db.model import Discount, Price, PriceTier
from app.errors import ensure_result
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, EstimateCostOut, EstimateOneshotCostIn
from app.service.usage import calculate_oneshot_usage_value
from app.utils import utcnow


def _find_tier(price: Price, usage_value: int) -> PriceTier:
    """Return the tier matching the given usage_value."""
    for tier in reversed(price.tiers):
        if usage_value >= tier.min_quantity:
            return tier
    return price.tiers[0]


def _tier_cost(price: Price, usage_value: int) -> Decimal:
    """Return the usage cost at a given cumulative usage, excluding price.fixed_cost."""
    tier = _find_tier(price, usage_value)
    return tier.base_cost + tier.multiplier * (usage_value - tier.min_quantity)


def calculate_cost(
    price: Price,
    *,
    previous_usage: int,
    current_usage: int,
    include_fixed_cost: bool,
    discount: Discount | None,
) -> Decimal:
    """Return the incremental cost between previous_usage and current_usage.

    The cost is computed as tier_cost(current_usage) - tier_cost(previous_usage),
    which correctly handles charges that span multiple tier boundaries.

    Args:
        price: the price with tiers.
        previous_usage: cumulative usage already charged (0 for first charge).
        current_usage: cumulative usage including the new increment.
        include_fixed_cost: whether to include the one-time price.fixed_cost.
        discount: optional discount to apply.
    """
    cost = _tier_cost(price, current_usage) - _tier_cost(price, previous_usage)
    if include_fixed_cost:
        # Fixed cost doesn't depend on the tier
        cost += price.fixed_cost
    if discount:
        # Discount applies to the final cost - not to the separate cost components individually.
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
        include_fixed_cost=True,
    )

    return EstimateCostOut(cost=cost)
