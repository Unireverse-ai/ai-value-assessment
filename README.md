# AI Value Assessment

**Time saved is a capacity measure. Cash saved needs a separate explanation.**

A small, auditable model for deciding whether a workflow improvement has a defensible business case. Built by UniReverseAI as a public reference for AI opportunity assessment: explicit assumptions, three scenarios, a clear cost model, and reproducible calculations.

The supplied manufacturing enquiry example is **entirely synthetic**. It is neither a customer result nor a quotation. The calculator does not establish that a proposed AI system can achieve the entered handling time, quality, adoption, or savings.

## Inspect it in five minutes

Requires Python 3.9 or newer. No installation, API key, model access, or external data is needed.

```sh
python3 assess.py examples/manufacturing.json
python3 -m unittest discover -s tests -v
```

The first command writes `artifacts/assessment.md` and `artifacts/assessment.json`. Open the Markdown report to compare assumptions and results. Open `calculator.html` directly in a browser for the same model with editable inputs; it makes no network requests and saves nothing remotely.

For a quick read before running anything, inspect the [illustrative output report](examples/illustrative-assessment.md), generated from the supplied JSON inputs.

## What the example actually says

| Synthetic scenario | Net capacity recovered / month | Net cash benefit / month | Simple payback |
|---|---:|---:|---:|
| Conservative | 40.00 hours | −EUR 685.60 | Not reached |
| Base | 115.20 hours | EUR 277.60 | 43.23 months |
| Optimistic | 204.60 hours | EUR 1,999.68 | 6.00 months |

The base scenario has a **negative first-year net cash benefit of EUR 8,668.80**, despite a positive monthly benefit. Its value depends on whether the entered cash realization, adoption, and ongoing costs can be supported. The tool preserves unattractive results; it does not turn released hours into an automatic investment recommendation.

## How the model works

```text
Eligible, adopted volume = monthly volume × eligible share × adoption
Gross handling hours released = adopted volume × (minutes before − minutes after) / 60
Net capacity hours = gross handling hours released − additional oversight hours

Gross cash reduction = gross handling hours released × loaded hourly cost × cash realization rate
Recurring cash cost = operations + model/infrastructure + additional oversight cash cost
Monthly net cash benefit = gross cash reduction − recurring cash cost
Year-one net cash benefit = 12 × monthly net cash benefit − one-time implementation cost
```

These are two views of the same operational change. **Do not add capacity value to cash savings.** The handling cost potential is displayed to expose the calculation, not as an additional benefit.

The “minutes after” input excludes separately entered oversight. Oversight reduces capacity in hours and adds a cash cost only when it causes additional spend. Set its incremental cash rate to zero when existing staff perform that work without extra payment. See the [methodology](docs/methodology.md) for the worked example, payback and ROI definitions, and the treatment of double counting.

## Files worth reviewing

| File | Purpose |
|---|---|
| [`assess.py`](assess.py) | Validation, calculations, scenario generation, and report output |
| [`examples/manufacturing.json`](examples/manufacturing.json) | Every input behind the published sample |
| [`calculator.html`](calculator.html) | Offline, editable browser calculator |
| [`docs/methodology.md`](docs/methodology.md) | Formulas, units, measurement boundaries, and interpretation |
| [`docs/evidence-checklist.md`](docs/evidence-checklist.md) | What must be measured or agreed before relying on an assessment |
| [`tests/test_assess.py`](tests/test_assess.py) | Independently stated arithmetic, loss-making cases, validation, and CLI checks |

## Boundaries

- Steady-state monthly assumptions apply from month one. Ramp-up, seasonality, and varying monthly volumes require a separate cash-flow model.
- No revenue uplift, tax, financing, discounted cash flows, or growth is modeled.
- Costs are incremental cash costs for the proposed change. Existing sunk costs are outside the incremental comparison.
- Scenario names express alternative assumptions, not statistical confidence intervals or forecasts.
- Slower handling remains a negative change. No return is displayed when the relevant denominator is zero.
- This tool checks arithmetic and input ranges. It does not validate business evidence, technical feasibility, service quality, or employment-related cash changes.

## Reproducibility and maintenance

The model uses Python's standard library. Calculations retain full floating-point precision internally and reports display two decimal places; displayed values can therefore differ slightly when recomputed from already rounded numbers. Tests check the underlying values with tolerance.

GitHub Actions configuration is supplied in `.github/workflows/verify.yml`. Inspect the actual Actions run for the revision under review; configuration alone is not evidence of a successful hosted run.

## About UniReverseAI

We help companies understand workflows, assess where AI can create measurable value, and integrate systems into day-to-day operations. Learn more at [unireverseai.com](https://unireverseai.com).

Source and documentation are available for inspection. See [RIGHTS.md](RIGHTS.md) for rights and use; this package does not grant an open-source license.
