# Methodology

## Decision being supported

For a defined workflow, do plausible changes in handling effort justify their implementation and ongoing cash costs? The output helps frame a pilot decision. It is not evidence that the pilot will achieve the entered improvements.

The unit of analysis must be stable: for example, an incoming manufacturing enquiry, rather than alternating between enquiries, quotes, and orders in the same calculation.

## Inputs and units

| Field | Unit | Meaning |
|---|---|---|
| `monthly_volume` | items/month | All items entering the defined workflow |
| `eligible_share` | fraction 0–1 | Share that meets the automation or assistance criteria |
| `adoption` | fraction 0–1 | Share of eligible items that actually use the new workflow |
| `minutes_before` | minutes/item | Baseline human handling time for the same process boundary |
| `minutes_after` | minutes/item | Remaining human handling time; excludes additional oversight entered separately |
| `loaded_hourly_cost` | currency/hour | Fully loaded baseline cost of the released handling work |
| `cash_realization_rate` | fraction 0–1 | Share of gross handling cost potential expected to change cash spend |
| `one_time_implementation` | currency | Incremental discovery, integration, setup, migration, and training cash cost |
| `recurring_ops` | currency/month | Incremental operational cash costs excluding model/infrastructure and oversight |
| `model_and_infra` | currency/month | Incremental model, hosting, storage, and related usage costs |
| `oversight_hours` | hours/month | Additional review, monitoring, and exception work outside `minutes_after` |
| `oversight_incremental_hourly_cost` | currency/hour | Additional cash spend per oversight hour; zero for unchanged payroll |

All numeric inputs must be finite and non-negative. The three fractions are bounded by zero and one. Inputs are not rounded to integers: average volume and average handling times can be fractional. `minutes_after` may exceed `minutes_before`; the resulting deterioration remains visible.

JSON input uses an integer `schema_version: 1` and the documented fields only. Duplicate keys and non-standard `NaN`/`Infinity` constants are rejected instead of silently accepting a later value. Very large inputs and derived results must stay within finite floating-point range. Python and browser formulas are checked against the same representative cases, including a large-value ROI ratio.

`currency` is a label, defaulting to EUR in the example. The calculator does not perform exchange-rate conversion. Use one currency and a consistent cost period throughout.

## Formulas

Let `V` be monthly volume, `E` eligible share, `A` adoption, `B` baseline minutes, `N` new handling minutes, `L` baseline loaded hourly cost, `R` cash realization rate, `I` implementation cash cost, `O` recurring operations, `M` model/infrastructure, `H` additional oversight hours, and `C` additional cash cost per oversight hour.

```text
Processed items                       P = V × E × A
Gross handling hours released         G = P × (B − N) / 60
Net capacity hours                    K = G − H
Handling cost potential               T = G × L
Gross cash reduction                  S = T × R
Additional oversight cash cost        Q = H × C
Monthly incremental recurring cost    F = O + M + Q
Monthly net cash benefit              X = S − F
Year-one total cost                   Y = I + 12 × F
Year-one net cash benefit             Z = 12 × X − I
Year-one ROI on total cost            ROI = 100 × Z / Y, only when Y > 0
Simple payback months                 I / X, only when X > 0
```

The first-year ROI denominator is **implementation plus twelve months of all incremental recurring costs**. This differs from an implementation-only ROI calculation; the field name makes the chosen denominator explicit. A zero total cost produces an undefined ROI rather than infinity. A non-positive monthly net cash benefit produces no simple payback. Zero implementation cost with positive monthly cash benefit produces zero-month payback.

Simple payback assumes the same monthly net benefit from the start and allows fractional months. It excludes discounting and does not mean a project has recovered its cost within year one. For a staged rollout, use the separate [monthly cash-flow model](cashflow.md), which records payment timing and changes in adoption, volume and cost.

## Capacity and cash are different views

A person handling fewer routine enquiries may use the released time for sales, quality, or exception handling. That can be useful without reducing payroll. A fully loaded hourly cost is therefore not itself a cash saving.

The cash realization rate must have an operational explanation, such as a documented reduction in externally purchased processing hours or overtime spend. Use zero when no reduction in cash spending is supported. Any staffing assumption needs the business owner's explicit confirmation and its own implementation costs.

Do not add `handling_cost_potential`, `gross_monthly_cash_reduction`, or a monetized version of `net_capacity_hours_after_oversight` together. They describe overlapping aspects of the same handling change.

## Oversight without double counting

1. Measure the remaining per-item handling effort in `minutes_after`.
2. Add only review, monitoring, or exception work that is outside those measured minutes to `oversight_hours`.
3. For the capacity view, subtract those additional hours from the released handling hours.
4. For the cash view, apply cash realization to **gross handling hours**, then subtract the additional cash cost of oversight once.

If an existing salaried team adds eight hours of monitoring without additional payment, enter eight oversight hours and an incremental oversight rate of zero. Capacity decreases by eight hours; unchanged payroll is not invented as an additional cash expense. If additional paid review is purchased for those eight hours, enter the actual incremental rate.

The model applies the cash realization rate symmetrically when handling becomes slower. A negative gross cash reduction represents increased handling cost under the same realization assumption. For a real deterioration, check whether that cash response is plausible rather than accepting the input mechanically.

Additional oversight can exceed released handling time while the cash calculation remains positive, for example if external processing spend is reduced and an existing salaried team absorbs extra work. The report flags this combination. It is not automatically a mathematical contradiction, but it requires a separate staffing and quality assessment; a cash benefit cannot establish operational feasibility.

## Worked base example: synthetic assumptions

```text
1,200 incoming items × 80% eligible × 70% adopted = 672 processed items/month
672 × (18 − 7) / 60 = 123.20 gross handling hours released
123.20 − 8 additional oversight hours = 115.20 net capacity hours
123.20 × EUR 32 × 25% cash realization = EUR 985.60 gross monthly cash reduction
EUR 240 operations + EUR 180 model/infra + 8 × EUR 36 oversight = EUR 708 monthly cost
EUR 985.60 − EUR 708 = EUR 277.60 monthly net cash benefit
EUR 12,000 / EUR 277.60 = 43.23 months simple payback
12 × EUR 277.60 − EUR 12,000 = −EUR 8,668.80 first-year net benefit
−EUR 8,668.80 / (EUR 12,000 + 12 × EUR 708) = −42.30% first-year ROI
```

Every number above is illustrative. The unfavorable first-year result is deliberate: the assessment exposes where a business case needs stronger evidence, a narrower scope, lower cost, or a different workflow.

## Scenarios and sensitivity

The input file defines conservative, base, and optimistic alternatives by overriding named inputs. No scenario carries a probability. Overrides are validated after merging with the base; omitted inputs keep their base values. An unknown input name fails validation rather than silently changing the model.

The generated sensitivity table varies cash realization and adoption one factor at a time. It holds all other base inputs fixed, including fixed recurring costs. It does not model cost growth at higher usage automatically. Enter usage-dependent model costs separately or use a different cash-flow model when they are material.

## Evidence needed before a decision

Use the [evidence checklist](evidence-checklist.md) to record baseline sampling, changed work effort, quality gates, adoption, incremental costs, and the source of cash savings. Recalculate when those assumptions change. A technically correct calculation cannot repair an unsupported baseline.
