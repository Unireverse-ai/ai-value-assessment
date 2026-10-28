# Synthetic staged rollout — optimistic steady state with delayed adoption

**Evidence status:** Entirely illustrative assumptions. Not a measured rollout, customer result or service quote.

Calculation of supplied assumptions. The shipped example is synthetic; this tool does not verify customer results.

## Horizon summary

| Measure | Result |
|---|---:|
| Modelled months | 12 |
| Gross cash reduction, EUR | 26,807.04 |
| Recurring cash cost, EUR | 8,744.00 |
| Implementation budget paid, EUR | 12,000.00 |
| Total cash cost, EUR | 20,744.00 |
| Net cumulative cash flow, EUR | 6,063.04 |
| ROI on total cash cost | 29.23% |
| Largest modelled funding gap, EUR | 9,794.64 |
| First nonnegative closing month | 9 |
| First recovery after a deficit | 9 |
| Nonnegative through this horizon from month | 9 |
| Full budget paid and nonnegative through this horizon from month | 9 |

These recovery measures are confined to the supplied horizon. They are not a guarantee about later cash flow.

## Monthly cash flow

Month 0 implementation payment: EUR 5,000.00; opening cumulative cash flow: EUR -5,000.00.

| Month | Volume | Adoption | Model/infra EUR | Net capacity h | Gross cash EUR | Recurring EUR | Implementation EUR | Net flow EUR | Cumulative EUR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1,200.00 | 15.00% | 80.00 | 19.10 | 449.28 | 896.00 | 0.00 | -446.72 | -5,446.72 |
| 2 | 1,200.00 | 35.00% | 120.00 | 69.90 | 1,048.32 | 792.00 | 4,000.00 | -3,743.68 | -9,190.40 |
| 3 | 1,200.00 | 55.00% | 160.00 | 118.70 | 1,647.36 | 760.00 | 0.00 | 887.36 | -8,303.04 |
| 4 | 1,200.00 | 75.00% | 210.00 | 167.50 | 2,246.40 | 738.00 | 3,000.00 | -1,491.60 | -9,794.64 |
| 5 | 1,200.00 | 85.00% | 230.00 | 192.90 | 2,545.92 | 686.00 | 0.00 | 1,859.92 | -7,934.72 |
| 6 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | -5,935.04 |
| 7 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | -3,935.36 |
| 8 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | -1,935.68 |
| 9 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | 64.00 |
| 10 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | 2,063.68 |
| 11 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | 4,063.36 |
| 12 | 1,200.00 | 90.00% | 240.00 | 204.60 | 2,695.68 | 696.00 | 0.00 | 1,999.68 | 6,063.04 |

## Boundaries

- All months, adoption, volumes and costs are supplied assumptions; no adoption curve is inferred.
- Each monthly override merges with the same base inputs, not with the previous month.
- Implementation payments must cover the entire declared budget within months 0 to the horizon; they are counted once.
- The same capacity, cash realization and incremental oversight definitions as assess.py apply in each month.
- A nonnegative month is not an investment payback claim. A later loss or payment can reverse an earlier recovery.
- Through-horizon recovery describes only the supplied period, after all scheduled implementation payments; it does not guarantee future payback.
- Funding gap uses undiscounted cumulative incremental cash flows with a starting balance of zero. It is not a complete working-capital or financing requirement.
- No revenue uplift, tax, financing, discounting, terminal value or activity beyond the last supplied month is included.

See `docs/cashflow.md` for the schema, payment and recovery definitions. Exact monthly assumptions are recorded in the companion JSON report.
