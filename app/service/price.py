"""Price service."""

from decimal import Decimal

from app.db.model import Discount, Price
from app.errors import ensure_result
from app.repository.group import RepositoryGroup
from app.schema.api import AddPriceIn, EstimateCostOut, EstimateOneshotCostIn
from app.service.usage import calculate_oneshot_usage_value
from app.utils import utcnow


def calculate_cost(
    price: Price,
    usage_value: int,
    *,
    include_fixed_cost: bool,
    discount: Discount | None,
) -> Decimal:
    """Return the cost for a job."""
    cost = price.multiplier * usage_value
    if include_fixed_cost:
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
        accounts = await repos.account.get_accounts_by_proj_id(
            proj_id=estimate_request.proj_id
        )
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
        price=price, usage_value=usage_value, discount=discount, include_fixed_cost=True
    )

    return EstimateCostOut(cost=cost)
