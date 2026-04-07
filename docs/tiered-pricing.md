# Tiered Pricing

## Overview

Prices are defined using a tiered model. Each price has one or more tiers that determine the cost based on usage.

The cost formula for a charge is:

```
cost = tier.fixed_cost + tier.multiplier × (usage_in_tier)
```

Where:

- `tier` is the tier whose range contains the usage value.
- `tier.fixed_cost` is a flat cost added once when entering that tier.
- `tier.multiplier` is the per-unit rate within that tier.

A linear price is simply a price with a single tier.

## Price structure

A price is composed of:

- `service_type`: oneshot, longrun, or storage.
- `service_subtype`: the specific service (e.g. ml-llm, single-cell-sim).
- `valid_from` / `valid_to`: the validity window.
- `vlab_id`: optional, to define a vlab-specific price. When absent, the price is the system-wide default.
- `tiers`: one or more tiers, each with:
  - `min_quantity`: lower bound (inclusive).
  - `max_quantity`: upper bound (exclusive), or null for the last tier.
  - `fixed_cost`: a flat cost added once when usage enters this tier.
  - `multiplier`: the per-unit rate within this tier.

## How tiers work

Tiers must be **contiguous**: each tier's `min_quantity` must equal the previous tier's `max_quantity`, and the first tier must start at 0. Only the last tier can have `max_quantity = null` (unbounded).

The cost for a charge from `previous_usage` to `current_usage` is computed by iterating over the tiers that overlap with the range `[previous_usage, current_usage)`. For each tier entered:

- The tier's `fixed_cost` is added once (only if the usage enters that tier during this charge).
- The tier's `multiplier` is applied to the portion of usage within that tier's range.

## fixed_cost

The `fixed_cost` of a tier is a flat cost added once when usage enters that tier. For example, it can be used as a setup fee (on the first tier) or as a surcharge for crossing into a higher usage bracket.

For the first tier (min_quantity=0), `fixed_cost` is charged on the first charge of a job (when `previous_usage == 0`). For longrun jobs with periodic charging, this means it is only charged once — on the first charge.

## Examples

### Linear pricing (single tier)

A simple per-unit rate of 0.00001 with no setup cost:

```json
{
  "service_type": "oneshot",
  "service_subtype": "ml-llm",
  "valid_from": "2024-01-01T00:00:00Z",
  "valid_to": null,
  "vlab_id": null,
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": null,
      "fixed_cost": "0",
      "multiplier": "0.00001"
    }
  ]
}
```

| Usage   | Cost                              |
| ------- | --------------------------------- |
| 100     | 0 + 0.00001 × 100 = **0.001**    |
| 1000000 | 0 + 0.00001 × 1000000 = **10.00** |

### Graduated pricing (decreasing rate)

First 1000 units at 0.10/unit, above 1000 at 0.05/unit:

```json
{
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 1000,
      "fixed_cost": "0",
      "multiplier": "0.10"
    },
    {
      "min_quantity": 1000,
      "max_quantity": null,
      "fixed_cost": "0",
      "multiplier": "0.05"
    }
  ]
}
```

| Usage | Tier | Cost                                         |
| ----- | ---- | -------------------------------------------- |
| 500   | 1    | 0 + 0.10 × 500 = **50**                     |
| 1500  | 2    | 0.10 × 1000 + 0.05 × (1500 − 1000) = **125** |

### Flat pricing by tier (step function)

Up to 20 units → 5 credits flat, above 20 → 50 credits flat:

```json
{
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 21,
      "fixed_cost": "5",
      "multiplier": "0"
    },
    {
      "min_quantity": 21,
      "max_quantity": null,
      "fixed_cost": "45",
      "multiplier": "0"
    }
  ]
}
```

Since the multiplier is 0, the cost is entirely determined by `fixed_cost`. Tier 2's `fixed_cost` of 45 is the incremental cost added when entering that tier, bringing the total to 50 (5 + 45).

| Usage | Tier | Cost       |
| ----- | ---- | ---------- |
| 10    | 1    | 5 = **5**  |
| 20    | 1    | 5 = **5**  |
| 100   | 2    | 5 + 45 = **50** |

### Graduated pricing with a setup fee

Setup fee of 2.0 (via first tier's `fixed_cost`) plus 0.10/unit for the first 100, then 0.05/unit above:

```json
{
  "tiers": [
    {
      "min_quantity": 0,
      "max_quantity": 100,
      "fixed_cost": "2.0",
      "multiplier": "0.10"
    },
    {
      "min_quantity": 100,
      "max_quantity": null,
      "fixed_cost": "0",
      "multiplier": "0.05"
    }
  ]
}
```

| Usage | Tier | Cost                                       |
| ----- | ---- | ------------------------------------------ |
| 50    | 1    | 2.0 + 0.10 × 50 = **7.0**                 |
| 200   | 2    | 2.0 + 0.10 × 100 + 0.05 × 100 = **17.0** |

The setup fee of 2.0 is the first tier's `fixed_cost`, so it is only charged when usage enters that tier (i.e., on the first charge when `previous_usage == 0`).

## Discounts

Discounts are applied **after** the full cost calculation. A discount of 0.2 (20%) on a cost of 10.0 results in a final cost of 8.0.

## Incremental charging (longrun jobs)

Longrun jobs are charged periodically. Each charge covers the usage increment since the last charge, but the tier is determined by the cumulative usage from the start of the job.

Example with the graduated pricing above (tier 1: 0-100 at 0.10 with `fixed_cost=2.0`, tier 2: 100+ at 0.05):

| Charge         | previous_usage | current_usage | Calculation                                                  | Amount  |
| -------------- | -------------- | ------------- | ------------------------------------------------------------ | ------- |
| 1st (0–60s)    | 0              | 60            | fixed_cost + 0.10 × 60 = 2.0 + 6.0                           | **8.0** |
| 2nd (60–130s)  | 60             | 130           | 0.10 × (100 − 60) + 0.05 × (130 − 100) = 4.0 + 1.5          | **5.5** |
| 3rd (130–200s) | 130            | 200           | 0.05 × (200 − 130) = 3.5                                     | **3.5** |

The 2nd charge crosses the tier boundary at 100: the first 40 units (60–100) are charged at 0.10, and the next 30 units (100–130) at 0.05. The first tier's `fixed_cost` is not charged again because usage already entered that tier on the 1st charge.

Total across all charges: 8.0 + 5.5 + 3.5 = **17.0**, which equals `2.0 + 0.10 × 100 + 0.05 × 100 = 17.0`.
