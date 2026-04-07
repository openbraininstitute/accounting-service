# Tiered Pricing

## Overview

Prices are defined using a tiered model. Each price has one or more tiers that determine the cost based on usage. A linear price is simply a price with a single tier.

The total cost for a charge is the sum of the costs across all tiers that the charged usage spans. For each tier traversed:

- The tier's `fixed_cost` is added once, only when usage enters that tier for the first time.
- The tier's `multiplier` is applied to the portion of usage within that tier's range.

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

## Tier constraints

- Tiers must be **contiguous**: each tier's `min_quantity` must equal the previous tier's `max_quantity`.
- The first tier must start at `min_quantity = 0`.
- Only the last tier can have `max_quantity = null` (unbounded).

## Discounts

Discounts are applied after the full cost calculation. A discount of 0.2 (20%) on a cost of 10.0 results in a final cost of 8.0.

## Incremental charging

Longrun jobs are charged periodically. Each charge covers only the usage increment since the last charge, but the tier boundaries are determined by the cumulative usage from the start of the job.

A tier's `fixed_cost` is added only when usage enters that tier for the first time. If a previous charge already covered that tier, the `fixed_cost` is not added again.

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

| Usage   | Cost       |
| ------- | ---------- |
| 100     | **0.001**  |
| 1000000 | **10.00**  |

### Graduated pricing (decreasing rate)

First 1000 units at 0.10/unit, above 1000 at 0.05/unit:

```json
{
  "tiers": [
    {"min_quantity": 0, "max_quantity": 1000, "fixed_cost": "0", "multiplier": "0.10"},
    {"min_quantity": 1000, "max_quantity": null, "fixed_cost": "0", "multiplier": "0.05"}
  ]
}
```

| Usage | Cost                                         |
| ----- | -------------------------------------------- |
| 500   | 0.10 × 500 = **50**                          |
| 1500  | 0.10 × 1000 + 0.05 × 500 = **125**          |

### Flat pricing by tier (step function)

Up to 20 units → 5 credits flat, above 20 → 50 credits flat:

```json
{
  "tiers": [
    {"min_quantity": 0, "max_quantity": 20, "fixed_cost": "5", "multiplier": "0"},
    {"min_quantity": 20, "max_quantity": null, "fixed_cost": "45", "multiplier": "0"}
  ]
}
```

Since the multiplier is 0, the cost is entirely determined by `fixed_cost`. Tier 2's `fixed_cost` of 45 is the incremental cost added when entering that tier, bringing the total to 50 (5 + 45).

| Usage | Cost            |
| ----- | --------------- |
| 10    | 5 = **5**       |
| 20    | 5 = **5**       |
| 21    | 5 + 45 = **50** |

### Graduated pricing with a setup fee

Setup fee of 2.0 (via first tier's `fixed_cost`) plus 0.10/unit for the first 100, then 0.05/unit above:

```json
{
  "tiers": [
    {"min_quantity": 0, "max_quantity": 100, "fixed_cost": "2.0", "multiplier": "0.10"},
    {"min_quantity": 100, "max_quantity": null, "fixed_cost": "0", "multiplier": "0.05"}
  ]
}
```

| Usage | Cost                                      |
| ----- | ----------------------------------------- |
| 50    | 2.0 + 0.10 × 50 = **7.0**                |
| 200   | 2.0 + 0.10 × 100 + 0.05 × 100 = **17.0** |

### Incremental charging across tier boundaries

Using the setup fee example above, a longrun job charged periodically:

| Charge       | Cumulative usage | Calculation                                         | Amount  |
| ------------ | ---------------- | --------------------------------------------------- | ------- |
| 1st (0–60)   | 0 → 60           | fixed_cost + 0.10 × 60 = 2.0 + 6.0                 | **8.0** |
| 2nd (60–130) | 60 → 130         | 0.10 × 40 + 0.05 × 30 = 4.0 + 1.5                  | **5.5** |
| 3rd (130–200)| 130 → 200        | 0.05 × 70 = 3.5                                     | **3.5** |

The 2nd charge crosses the tier boundary at 100: 40 units (60–100) at 0.10, then 30 units (100–130) at 0.05. The setup fee is not charged again because usage already entered the first tier on the 1st charge.

Total: 8.0 + 5.5 + 3.5 = **17.0**, matching the full cost of `2.0 + 0.10 × 100 + 0.05 × 100 = 17.0`.
