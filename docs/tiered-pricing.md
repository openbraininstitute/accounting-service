# Tiered Pricing

## Overview

Prices are defined using a tiered model. Each price has one or more tiers that determine the usage-based cost, plus a price-level fixed cost that is charged once per job.

The full cost formula for a single-tier charge is:

```
cost = price.fixed_cost + tier.base_cost + tier.multiplier × (usage_in_tier)
```

Where:

- `price.fixed_cost` is a one-time job cost (e.g. setup fee), included only on the first charge.
- `tier` is the tier whose range contains the usage value.
- `tier.base_cost` is a flat cost added when entering that tier.
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
  - `base_cost`: a flat cost added once when usage enters this tier.
  - `multiplier`: the per-unit rate within this tier.

## How tiers work

Tiers must be **contiguous**: each tier's `min_quantity` must equal the previous tier's `max_quantity`, and the first tier must start at 0. Only the last tier can have `max_quantity = null` (unbounded).

The cost for a charge from `previous_usage` to `current_usage` is computed by iterating over the tiers that overlap with the range `[previous_usage, current_usage)`. For each tier entered:

- The tier's `base_cost` is added once (only if the usage enters that tier during this charge).
- The tier's `multiplier` is applied to the portion of usage within that tier's range.

The `price.fixed_cost` is added only on the first charge.

## fixed_cost vs base_cost

These are two distinct concepts:

- `price.fixed_cost`: a one-time cost for the job (e.g. setup fee). It is included or excluded depending on whether it's the first charge for a job. For oneshot jobs, it's always included. For longrun jobs, it's included on the first charge and excluded on subsequent periodic charges.
- `tier.base_cost`: a flat cost added once when usage enters that tier. For example, a surcharge for crossing into a higher usage bracket. This is purely incremental — it is not an accumulated total.

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
      "base_cost": "0",
      "multiplier": "0.05"
    }
  ]
}
```

Tier 2's `base_cost` is 0 here because there's no surcharge for entering tier 2 — the rate simply decreases.

| Usage | Tier | Cost                                 |
| ----- | ---- | ------------------------------------ |
| 500   | 1    | 0 + 0.10 × 500 = **50**              |
| 1000  | 2    | 0.10 × 1000 + 0.05 × (1000 − 1000) = **100** |
| 1500  | 2    | 0.10 × 1000 + 0.05 × (1500 − 1000) = **125** |

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
      "base_cost": "45",
      "multiplier": "0"
    }
  ]
}
```

Since the multiplier is 0, the cost is entirely determined by `base_cost`. Tier 2's `base_cost` of 45 is the incremental cost added when entering that tier, bringing the total to 50 (5 + 45).

| Usage | Tier | Cost       |
| ----- | ---- | ---------- |
| 10    | 1    | 5 = **5**  |
| 20    | 1    | 5 = **5**  |
| 100   | 2    | 5 + 45 = **50** |

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
      "base_cost": "0",
      "multiplier": "0.05"
    }
  ]
}
```

| Usage | Tier | Cost (first charge)                        | Cost (subsequent charges)            |
| ----- | ---- | ------------------------------------------ | ------------------------------------ |
| 50    | 1    | 2.0 + 0.10 × 50 = **7.0**                  | 0.10 × 50 = **5.0**                  |
| 200   | 2    | 2.0 + 0.10 × 100 + 0.05 × 100 = **17.0**   | 0.10 × 100 + 0.05 × 100 = **15.0**   |

The setup fee of 2.0 is only included on the first charge (`include_fixed_cost=True`).

## Discounts

Discounts are applied **after** the full cost calculation (including both `fixed_cost` and tier cost). A discount of 0.2 (20%) on a cost of 10.0 results in a final cost of 8.0.

## Incremental charging (longrun jobs)

Longrun jobs are charged periodically. Each charge covers the usage increment since the last charge, but the tier is determined by the cumulative usage from the start of the job.

Example with the graduated pricing above (`fixed_cost=2.0`, tier 1: 0-100 at 0.10, tier 2: 100+ at 0.05 with `base_cost=0`):

| Charge         | previous_usage | current_usage | Calculation                                                  | Amount  |
| -------------- | -------------- | ------------- | ------------------------------------------------------------ | ------- |
| 1st (0–60s)    | 0              | 60            | fixed_cost + 0.10 × 60 = 2.0 + 6.0                           | **8.0** |
| 2nd (60–130s)  | 60             | 130           | 0.10 × (100 − 60) + 0.05 × (130 − 100) = 4.0 + 1.5          | **5.5** |
| 3rd (130–200s) | 130            | 200           | 0.05 × (200 − 130) = 3.5                                     | **3.5** |

The 2nd charge crosses the tier boundary at 100: the first 40 units (60–100) are charged at 0.10, and the next 30 units (100–130) at 0.05. The iteration handles this automatically.

Total across all charges: 8.0 + 5.5 + 3.5 = **17.0**, which equals `2.0 + 0.10 × 100 + 0.05 × 100 = 17.0`.
