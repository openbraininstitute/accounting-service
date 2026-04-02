# Tiered Pricing

## Overview

Prices are defined using a tiered model. Each price has one or more tiers that determine the usage-based cost, plus a price-level fixed cost that is charged once per job.

The full cost formula is:

```
cost = price.fixed_cost + tier.base_cost + tier.multiplier × (usage_value - tier.min_quantity)
```

Where:

- `price.fixed_cost` is a one-time job cost (e.g. setup fee), included only on the first charge.
- `tier` is the tier whose range contains the usage value.
- `tier.base_cost` is the accumulated usage cost at the start of that tier.
- `tier.multiplier` is the per-unit rate within that tier.

A linear price is simply a price with a single tier.

## Price structure

A price is composed of:

- `service_type`: oneshot, longrun, or storage.
- `service_subtype`: the specific service (e.g. ml-llm, single-cell-sim).
- `valid_from` / `valid_to`: the validity window.
- `fixed_cost`: one-time cost per job, independent of usage.
- `vlab_id`: optional, to define a vlab-specific price. When absent, the price is the system-wide default.
- `tiers`: one or more tiers, each with:
  - `min_quantity`: lower bound (inclusive).
  - `max_quantity`: upper bound (exclusive), or null for the last tier.
  - `base_cost`: the total accumulated usage cost at the start of this tier.
  - `multiplier`: the per-unit rate within this tier.

## How tiers work

Tiers must be **contiguous**: each tier's `min_quantity` must equal the previous tier's `max_quantity`, and the first tier must start at 0. Only the last tier can have `max_quantity = null` (unbounded).

The usage cost at a given cumulative usage is:

```
tier_cost(usage) = tier.base_cost + tier.multiplier × (usage - tier.min_quantity)
```

For a full charge (e.g. oneshot), the total cost is:

```
cost = price.fixed_cost + tier_cost(usage)
```

For an incremental charge (e.g. longrun periodic charges), the cost of the increment is computed as the difference between the cumulative costs:

```
cost = tier_cost(current_usage) - tier_cost(previous_usage)
```

This correctly handles charges that span multiple tier boundaries without iterating over tiers. The `price.fixed_cost` is added only on the first charge.

## fixed_cost vs base_cost

These are two distinct concepts:

- `price.fixed_cost`: a one-time cost for the job (e.g. setup fee). It is included or excluded depending on whether it's the first charge for a job. For oneshot jobs, it's always included. For longrun jobs, it's included on the first charge and excluded on subsequent periodic charges.
- `tier.base_cost`: the accumulated usage cost at the tier's boundary. It encodes the total cost of all previous tiers at their upper bounds. This is purely a function of the tier structure and is always included in the calculation.

## Examples

### Linear pricing (single tier)

A simple per-unit rate of 0.00001 with no fixed cost:

```json
{
  "service_type": "oneshot",
  "service_subtype": "ml-llm",
  "valid_from": "2024-01-01T00:00:00Z",
  "valid_to": null,
  "fixed_cost": "0",
  "vlab_id": null,
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": null,
      "base_cost": "0",
      "multiplier": "0.00001"
    }
  ]
}
```

| Usage   | Cost                                  |
| ------- | ------------------------------------- |
| 100     | 0 + 0 + 0.00001 × 100 = **0.001**     |
| 1000000 | 0 + 0 + 0.00001 × 1000000 = **10.00** |

### Graduated pricing (decreasing rate)

First 1000 units at 0.10/unit, above 1000 at 0.05/unit:

```json
{
  "fixed_cost": "0",
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 1000,
      "base_cost": "0",
      "multiplier": "0.10"
    },
    {
      "min_quantity": 1000,
      "max_quantity": null,
      "base_cost": "100",
      "multiplier": "0.05"
    }
  ]
}
```

Tier 2's `base_cost` of 100 = the accumulated usage cost at the boundary (1000 × 0.10).

| Usage | Tier | Cost                                 |
| ----- | ---- | ------------------------------------ |
| 500   | 1    | 0 + 0.10 × 500 = **50**              |
| 1000  | 2    | 100 + 0.05 × (1000 − 1000) = **100** |
| 1500  | 2    | 100 + 0.05 × (1500 − 1000) = **125** |

### Flat pricing by tier (step function)

Up to 20 units → 5 credits flat, above 20 → 50 credits flat:

```json
{
  "fixed_cost": "0",
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 21,
      "base_cost": "5",
      "multiplier": "0"
    },
    {
      "min_quantity": 21,
      "max_quantity": null,
      "base_cost": "50",
      "multiplier": "0"
    }
  ]
}
```

Since the multiplier is 0, the cost is entirely determined by `base_cost`. Tier 2's `base_cost` of 50 is the actual price for that tier — not an accumulation of tier 1, since the multiplier in tier 1 is also 0.

| Usage | Tier | Cost                         |
| ----- | ---- | ---------------------------- |
| 10    | 1    | 5 + 0 × 10 = **5**           |
| 20    | 1    | 5 + 0 × 20 = **5**           |
| 21    | 2    | 50 + 0 × (21 − 21) = **50**  |
| 100   | 2    | 50 + 0 × (100 − 21) = **50** |

### Graduated pricing with a setup fee

Fixed cost of 2.0 (charged once per job) plus 0.10/unit for the first 100, then 0.05/unit above:

```json
{
  "fixed_cost": "2.0",
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 100,
      "base_cost": "0",
      "multiplier": "0.10"
    },
    {
      "min_quantity": 100,
      "max_quantity": null,
      "base_cost": "10",
      "multiplier": "0.05"
    }
  ]
}
```

| Usage | Tier | Cost (first charge)              | Cost (subsequent charges)  |
| ----- | ---- | -------------------------------- | -------------------------- |
| 50    | 1    | 2.0 + 0 + 0.10 × 50 = **7.0**    | 0 + 0.10 × 50 = **5.0**    |
| 200   | 2    | 2.0 + 10 + 0.05 × 100 = **17.0** | 10 + 0.05 × 100 = **15.0** |

The setup fee of 2.0 is only included on the first charge (`include_fixed_cost=True`).

## Discounts

Discounts are applied **after** the full cost calculation (including both `fixed_cost` and tier cost). A discount of 0.2 (20%) on a cost of 10.0 results in a final cost of 8.0.

## Incremental charging (longrun jobs)

Longrun jobs are charged periodically. Each charge covers the usage increment since the last charge, but the tier is determined by the cumulative usage from the start of the job.

Example with the graduated pricing above (`fixed_cost=2.0`, tier 1: 0-100 at 0.10, tier 2: 100+ at 0.05 with `base_cost=10`):

| Charge         | previous_usage | current_usage | Calculation                                               | Amount  |
| -------------- | -------------- | ------------- | --------------------------------------------------------- | ------- |
| 1st (0–60s)    | 0              | 60            | fixed_cost + tier_cost(60) - tier_cost(0) = 2.0 + 6.0 - 0 | **8.0** |
| 2nd (60–130s)  | 60             | 130           | tier_cost(130) - tier_cost(60) = 11.5 - 6.0               | **5.5** |
| 3rd (130–200s) | 130            | 200           | tier_cost(200) - tier_cost(130) = 15.0 - 11.5             | **3.5** |

The 2nd charge crosses the tier boundary at 100: the first 40 units (60–100) are charged at 0.10, and the next 30 units (100–130) at 0.05. The subtraction handles this automatically.

Total across all charges: 8.0 + 5.5 + 3.5 = **17.0**, which equals `2.0 + tier_cost(200) = 2.0 + 15.0 = 17.0`.
