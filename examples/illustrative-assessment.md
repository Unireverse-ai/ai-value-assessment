# Synthetic manufacturing enquiry workflow — investment assessment

**Evidence status:** Illustrative assumptions only. Not measured results, a client quote, or a UniReverseAI deployment.

Reproducible calculation of supplied assumptions. This is not a measured customer result.

## Scenario comparison

| Scenario | Net capacity h/month | Gross cash reduction EUR/month | Recurring cost EUR/month | Net cash EUR/month | Payback months | Year-one net EUR | Year-one ROI on total cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Conservative | 40.00 | 166.40 | 852.00 | -685.60 | Not reached / undefined | -20,227.20 | -91.02% |
| Base | 115.20 | 985.60 | 708.00 | 277.60 | 43.23 | -8,668.80 | -42.30% |
| Optimistic | 204.60 | 2,695.68 | 696.00 | 1,999.68 | 6.00 | 11,996.16 | 58.94% |

## Base inputs

| Input | Value |
|---|---:|
| monthly_volume | 1200 |
| eligible_share | 0.8 |
| adoption | 0.7 |
| minutes_before | 18 |
| minutes_after | 7 |
| loaded_hourly_cost | 32 |
| cash_realization_rate | 0.25 |
| one_time_implementation | 12000 |
| recurring_ops | 240 |
| model_and_infra | 180 |
| oversight_hours | 8 |
| oversight_incremental_hourly_cost | 36 |

## One-factor sensitivity

Each row changes one base input; all other base inputs stay fixed.

| Changed input | Value | Net cash EUR/month | Payback months |
|---|---:|---:|---:|
| cash_realization_rate | 0 | -708.00 | Not reached / undefined |
| cash_realization_rate | 0.25 | 277.60 | 43.23 |
| cash_realization_rate | 0.5 | 1,263.20 | 9.50 |
| cash_realization_rate | 0.75 | 2,248.80 | 5.34 |
| cash_realization_rate | 1 | 3,234.40 | 3.71 |
| adoption | 0.3 | -285.60 | Not reached / undefined |
| adoption | 0.5 | -4.00 | Not reached / undefined |
| adoption | 0.7 | 277.60 | 43.23 |
| adoption | 0.9 | 559.20 | 21.46 |
| adoption | 1 | 700.00 | 17.14 |

## Interpretation and boundaries

- All volumes, costs and usage are steady-state monthly assumptions from month one.
- Handling minutes after the change exclude separately budgeted oversight hours.
- The cash realization rate applies to gross handling cost potential, not net capacity.
- Oversight cash cost counts only additional cash spend; use zero for existing payroll with no incremental payment.
- Capacity hours and cash benefits describe different views and must not be added together.
- No revenue uplift, growth, tax, financing, discounting or ramp-up period is included.
- A non-positive monthly net cash benefit has no simple payback. A positive monthly result can still have a negative first-year return.
- When handling becomes slower, the model preserves the negative change instead of clipping it to zero.
- A zero first-year total cost gives an undefined ROI; it does not imply an infinite return.

See `docs/methodology.md` for formulas and the evidence needed before a purchasing decision.
