#!/usr/bin/env python3
"""A small, explicit workflow investment model. No network or third-party packages."""

import argparse
import json
import math
from pathlib import Path

FIELDS = {
    "monthly_volume": "Items entering the workflow each month",
    "eligible_share": "Fraction of incoming items eligible for the change",
    "adoption": "Fraction of eligible items actually using the change",
    "minutes_before": "Baseline human handling minutes per item",
    "minutes_after": "Human handling minutes after the change, excluding separate oversight",
    "loaded_hourly_cost": "Baseline fully loaded handling cost per hour",
    "cash_realization_rate": "Fraction of handling cost reduction that actually changes cash spend",
    "one_time_implementation": "One-time implementation and setup cash cost",
    "recurring_ops": "Monthly incremental operations cash cost, excluding model and oversight",
    "model_and_infra": "Monthly incremental model and infrastructure cash cost",
    "oversight_hours": "Additional human review and monitoring hours per month",
    "oversight_incremental_hourly_cost": "Actual additional cash cost per oversight hour",
}
FRACTIONS = {"eligible_share", "adoption", "cash_realization_rate"}


def validate_inputs(inputs):
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be an object")
    missing = set(FIELDS) - set(inputs)
    unknown = set(inputs) - set(FIELDS)
    if missing:
        raise ValueError("Missing input(s): " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("Unknown input(s): " + ", ".join(sorted(unknown)))
    result = {}
    for name in FIELDS:
        value = inputs[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(name + " must be a number")
        if not math.isfinite(value) or value < 0:
            raise ValueError(name + " must be finite and non-negative")
        if name in FRACTIONS and value > 1:
            raise ValueError(name + " must be between 0 and 1")
        result[name] = float(value)
    return result


def evaluate(inputs):
    """Calculate without intermediate rounding. Negative changes remain visible."""
    p = validate_inputs(inputs)
    processed = p["monthly_volume"] * p["eligible_share"] * p["adoption"]
    handling_hours = processed * (p["minutes_before"] - p["minutes_after"]) / 60
    net_capacity = handling_hours - p["oversight_hours"]
    handling_cost_potential = handling_hours * p["loaded_hourly_cost"]
    cash_reduction = handling_cost_potential * p["cash_realization_rate"]
    oversight_cost = p["oversight_hours"] * p["oversight_incremental_hourly_cost"]
    recurring = p["recurring_ops"] + p["model_and_infra"] + oversight_cost
    monthly_net = cash_reduction - recurring
    first_year_cost = p["one_time_implementation"] + 12 * recurring
    first_year_net = 12 * monthly_net - p["one_time_implementation"]
    result = {
        "processed_items_per_month": processed,
        "gross_handling_hours_released": handling_hours,
        "net_capacity_hours_after_oversight": net_capacity,
        "handling_cost_potential": handling_cost_potential,
        "gross_monthly_cash_reduction": cash_reduction,
        "monthly_oversight_cash_cost": oversight_cost,
        "monthly_incremental_recurring_cost": recurring,
        "monthly_net_cash_benefit": monthly_net,
        "simple_payback_months": p["one_time_implementation"] / monthly_net if monthly_net > 0 else None,
        "first_year_total_cost": first_year_cost,
        "first_year_net_cash_benefit": first_year_net,
        "first_year_roi_on_total_cost_pct": 100 * first_year_net / first_year_cost if first_year_cost > 0 else None,
    }
    # Finite inputs can still overflow when multiplied. Never emit invalid JSON.
    if any(value is not None and not math.isfinite(value) for value in result.values()):
        raise ValueError("Inputs produce results outside the supported numeric range")
    return result


def build_report(document):
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Expected an object with schema_version: 1")
    currency = document.get("currency", "EUR")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isupper() or not currency.isalpha():
        raise ValueError("currency must be a three-letter uppercase label")
    base = validate_inputs(document.get("inputs"))
    scenarios = document.get("scenarios", [{"name": "Base", "overrides": {}}])
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")
    rows = []
    used = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("Each scenario must be an object")
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip() or name in used:
            raise ValueError("Each scenario needs a non-empty, unique name")
        overrides = scenario.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError("Scenario overrides must be an object")
        current = validate_inputs(dict(base, **overrides))
        rows.append({"name": name, "inputs": current, "results": evaluate(current)})
        used.add(name)
    sensitivity = []
    for field, values in (
        ("cash_realization_rate", [0, 0.25, 0.5, 0.75, 1]),
        ("adoption", [0.3, 0.5, 0.7, 0.9, 1]),
    ):
        for value in values:
            inputs = dict(base, **{field: value})
            sensitivity.append({"varied_input": field, "value": value, "results": evaluate(inputs)})
    return {
        "schema_version": 1,
        "title": document.get("title", "Workflow value assessment"),
        "evidence_status": document.get("evidence_status", "User-supplied assumptions; not verified by this tool"),
        "currency": currency,
        "base_inputs": base,
        "base_results": evaluate(base),
        "scenarios": rows,
        "sensitivity": sensitivity,
        "assumptions": [
            "All volumes, costs and usage are steady-state monthly assumptions from month one.",
            "Handling minutes after the change exclude separately budgeted oversight hours.",
            "The cash realization rate applies to gross handling cost potential, not net capacity.",
            "Oversight cash cost counts only additional cash spend; use zero for existing payroll with no incremental payment.",
            "Capacity hours and cash benefits describe different views and must not be added together.",
            "No revenue uplift, growth, tax, financing, discounting or ramp-up period is included.",
        ],
    }


def fmt(value):
    return "Not reached / undefined" if value is None else f"{value:,.2f}"


def markdown(report):
    # Escape supplied text so document labels cannot break the table layout.
    def clean(value):
        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    currency = report["currency"]
    rows = [
        "# " + clean(report["title"]),
        "",
        "**Evidence status:** " + clean(report["evidence_status"]),
        "",
        "Reproducible calculation of supplied assumptions. This is not a measured customer result.",
        "",
        "## Scenario comparison",
        "",
        f"| Scenario | Net capacity h/month | Gross cash reduction {currency}/month | Recurring cost {currency}/month | Net cash {currency}/month | Payback months | Year-one net {currency} | Year-one ROI on total cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in report["scenarios"]:
        p = scenario["results"]
        roi = fmt(p["first_year_roi_on_total_cost_pct"])
        if p["first_year_roi_on_total_cost_pct"] is not None:
            roi += "%"
        rows.append("| " + " | ".join([
            clean(scenario["name"]), fmt(p["net_capacity_hours_after_oversight"]),
            fmt(p["gross_monthly_cash_reduction"]), fmt(p["monthly_incremental_recurring_cost"]),
            fmt(p["monthly_net_cash_benefit"]), fmt(p["simple_payback_months"]),
            fmt(p["first_year_net_cash_benefit"]), roi,
        ]) + " |")
    rows += ["", "## Base inputs", "", "| Input | Value |", "|---|---:|"]
    rows += [f"| {name} | {value:g} |" for name, value in report["base_inputs"].items()]
    rows += ["", "## One-factor sensitivity", "", "Each row changes one base input; all other base inputs stay fixed.", "", f"| Changed input | Value | Net cash {currency}/month | Payback months |", "|---|---:|---:|---:|"]
    for row in report["sensitivity"]:
        rows.append(f"| {row['varied_input']} | {row['value']:g} | {fmt(row['results']['monthly_net_cash_benefit'])} | {fmt(row['results']['simple_payback_months'])} |")
    rows += ["", "## Interpretation and boundaries", ""]
    rows += ["- " + line for line in report["assumptions"]]
    rows += ["- A non-positive monthly net cash benefit has no simple payback. A positive monthly result can still have a negative first-year return.", "- When handling becomes slower, the model preserves the negative change instead of clipping it to zero.", "- A zero first-year total cost gives an undefined ROI; it does not imply an infinite return.", "", "See `docs/methodology.md` for formulas and the evidence needed before a purchasing decision.", ""]
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input JSON file")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        report = build_report(document)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "assessment.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        (args.output_dir / "assessment.md").write_text(markdown(report), encoding="utf-8")
    except (OSError, ValueError, TypeError, OverflowError) as error:
        parser.exit(2, f"Assessment failed: {error}\n")
    result = report["base_results"]
    print("Evidence: " + str(report["evidence_status"]))
    print(f"Base monthly net cash benefit: {report['currency']} {fmt(result['monthly_net_cash_benefit'])}")
    print(f"Simple payback months: {fmt(result['simple_payback_months'])}")
    print(f"Reports written to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
