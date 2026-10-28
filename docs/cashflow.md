# Monthly cash flow and rollout assumptions

The steady-state model answers “what would a representative month look like?” A rollout model asks “when is money spent and recovered while adoption changes?” The two questions need different time boundaries.

```sh
python3 cashflow.py examples/staged-rollout.json
```

This writes `artifacts/cashflow/cashflow.json` and `cashflow.md`. The [committed example report](../examples/staged-rollout-report.md) can be read without running code; its full assumptions are in [staged-rollout.json](../examples/staged-rollout.json).

## Reuse one economic definition

Each month uses `assess.evaluate` with the same definitions of eligible volume, adoption, handling minutes, cash realization and incremental oversight. Capacity remains an hours measure; no capacity value is added to cash benefit. Review time in `minutes_after` is not repeated in `oversight_hours`.

The full `one_time_implementation` budget belongs to the input once. Each month is evaluated with that input temporarily set to zero; the actual cash payments are then deducted from the specified months. This avoids charging both a full setup fee and its instalments.

```text
Month 0 cumulative cash flow = − implementation payment at month 0
Month m net cash flow = gross cash reduction(m) − recurring cost(m) − implementation payment(m)
Month m cumulative cash flow = month 0 cash flow + sum of net cash flows through m
Horizon cash cost = full implementation budget + sum of recurring costs
Horizon ROI = total cumulative net cash flow / horizon cash cost × 100, if cost > 0
```

## Input contract

The top-level object allows `schema_version` (integer `1`), `title`, `evidence_status`, `currency`, `inputs`, `implementation_payments` and `months`. The [steady-state input definitions](methodology.md) apply to `inputs`. Unknown fields, duplicate JSON keys, booleans in numeric fields and non-standard `NaN`/`Infinity` constants are rejected.

| Field | Contract |
|---|---|
| `implementation_payments` | A list of `{ "month": 0, "amount": 5000 }` objects. Month 0 means before operations begin. Months must be distinct integers within 0 to the supplied horizon. Amounts must be finite and non-negative. Their decimal representations must sum to the full declared implementation budget. Use `[]` for a zero budget. |
| `months` | Between 12 and 60 entries, numbered consecutively from 1. Each entry allows only `month` and `overrides`. |
| `overrides` | Any monthly economic input except `one_time_implementation`. Each entry merges with the original base independently; an override does not carry into the next month. |

Explicitly enter expected monthly volume, adoption and usage-dependent model cost rather than assuming that one causes another. An increase in adoption does not automatically increase `model_and_infra`. The example records all three inputs in every month and lowers extra oversight as the illustrative rollout progresses.

The payment schedule must include all declared implementation costs within the horizon. Later committed fees cannot be omitted to make a short forecast look positive. If work outside the declared budget is likely, revise the budget before relying on the output. The tool can check arithmetic consistency, not completeness of the commercial scope.

## Four different recovery observations

All observations use unrounded closing balances. The model deliberately does not compress them into one “payback” number.

| Output | Meaning and limitation |
|---|---|
| `first_nonnegative_closing_month` | The first operating month with cumulative cash flow at least zero. A later payment may still make the balance negative. This alone does not establish investment recovery. |
| `first_recovery_after_deficit_month` | The first nonnegative closing month after an earlier negative balance, including a month 0 deficit. `null` means no such recovery occurred, or no deficit arose. A later loss can reverse it. |
| `nonnegative_through_horizon_from_month` | The earliest month whose balance and every later supplied closing balance remain nonnegative. It does not check that all implementation payments have already been made at that month. |
| `full_budget_recovered_through_horizon_from_month` | The earliest such month at or after the final nonzero implementation payment. All declared implementation costs are paid and the balance remains nonnegative through the specified horizon. It is not a guarantee about later months. |

For example, with EUR 8 monthly benefit and a EUR 24 implementation payment in month 2, month 1 closes at EUR 8, month 2 at −EUR 8, and month 3 at zero. First nonnegative is month 1; recovery after a deficit is month 3. A material later operating cost can reverse either observation. Tests exercise both cases.

When no funding deficit occurs, “recovery after a deficit” is not applicable. The largest modelled funding gap is the greatest negative cumulative balance, including month 0, expressed as a positive amount. It omits existing working capital, financing charges, payment delays outside this schedule and other company cash flows.

## What the shipped example shows

The example starts with the optimistic steady-state inputs from `manufacturing.json`, then explicitly stages adoption from 15% to 90%. It includes extra early oversight, changing model costs and EUR 12,000 implementation payments in months 0, 2 and 4. These are invented planning assumptions, not a forecast derived from operating evidence.

- The steady-state optimistic calculation displays about 6.00 months of simple, fractional payback.
- The staged twelve-month calculation produces EUR 6,063.04 cumulative net cash flow and a largest modelled funding gap of EUR 9,794.64.
- Full declared implementation cost is paid and closing cash stays nonnegative from month 9 through month 12. The first-year result is lower than the immediate steady-state comparison because adoption takes time.

The comparison illustrates a timing effect. It does not establish that this adoption trajectory, cash realization or service quality is achievable. Record the evidence behind the changed inputs before making a pilot or purchasing decision.

## Boundaries

No adoption curve, monthly cost growth, probability, revenue increase, tax, financing, discounting or terminal value is inferred. Monthly volume can vary because it is explicitly supplied. The steady-state browser calculator remains a separate single-month tool; it does not execute the monthly schedule. Both tools reject results outside finite floating-point range.

Monthly cash effects can be positive while net human effort increases, for example when purchased handling work is reduced but existing staff absorb more oversight. Such months receive an interpretation flag; they still need a separate staffing and quality assessment. A positive cash flow does not validate operational feasibility.
