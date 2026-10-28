#!/usr/bin/env python3
"""Model a finite, explicitly supplied monthly rollout. Standard library only."""

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path

from assess import (FIELDS, evaluate, fmt, interpretation_flags, load_json,
                    validate_currency, validate_inputs, validate_label)


def finite(value, name):
    if not math.isfinite(value):
        raise ValueError(name + " is outside the supported numeric range")
    return value


def amount(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be a finite non-negative number")
    try:
        value = float(value)
    except (ValueError, OverflowError):
        raise ValueError(name + " is outside the supported numeric range") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(name + " must be a finite non-negative number")
    return value


def build_cashflow(document):
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise ValueError("Expected an object with schema_version: 1")
    allowed = {"schema_version", "title", "evidence_status", "currency", "inputs",
               "implementation_payments", "months"}
    if set(document) - allowed:
        raise ValueError("Unknown cash-flow document field")
    title = validate_label(document.get("title", "Monthly workflow cash flow"), "title")
    evidence = validate_label(document.get("evidence_status", "User-supplied assumptions; not verified by this tool"), "evidence_status")
    currency = validate_currency(document.get("currency", "EUR"))
    base = validate_inputs(document.get("inputs"))
    months = document.get("months")
    if not isinstance(months, list) or not 12 <= len(months) <= 60:
        raise ValueError("months must contain 12 to 60 consecutive monthly entries")
    horizon = len(months)

    schedule = document.get("implementation_payments")
    if not isinstance(schedule, list):
        raise ValueError("implementation_payments must be a list")
    payments = {}
    for payment in schedule:
        if not isinstance(payment, dict) or set(payment) != {"month", "amount"}:
            raise ValueError("Each implementation payment needs only month and amount")
        month = payment["month"]
        if type(month) is not int or not 0 <= month <= horizon or month in payments:
            raise ValueError("Payment months must be unique integers from 0 to the horizon")
        payments[month] = amount(payment["amount"], "payment amount")
    # Compare decimal representations: 0.1 + 0.2 should match a 0.3 budget.
    paid_decimal = sum((Decimal(str(value)) for value in payments.values()), Decimal(0))
    if paid_decimal != Decimal(str(base["one_time_implementation"])):
        raise ValueError("Implementation payments must equal the declared one_time_implementation budget")
    last_payment = max((month for month, value in payments.items() if value > 0), default=0)
    opening = -payments.get(0, 0.0)
    cashflows = [opening]
    rows = []
    for expected_month, entry in enumerate(months, 1):
        if not isinstance(entry, dict) or set(entry) - {"month", "overrides"}:
            raise ValueError("Each monthly entry allows only month and overrides")
        if type(entry.get("month")) is not int or entry["month"] != expected_month:
            raise ValueError("Months must be consecutive integers starting at 1")
        overrides = entry.get("overrides", {})
        if not isinstance(overrides, dict) or set(overrides) - (set(FIELDS) - {"one_time_implementation"}):
            raise ValueError("Monthly overrides must use known inputs; implementation cost belongs in the payment schedule")
        current = validate_inputs(dict(base, **overrides))
        # The full budget is represented once by actual scheduled cash payments.
        current["one_time_implementation"] = 0.0
        result = evaluate(current)
        payment = payments.get(expected_month, 0.0)
        net = finite(result["monthly_net_cash_benefit"] - payment, "Monthly net cash flow")
        cashflows.append(net)
        try:
            cumulative = finite(math.fsum(cashflows), "Cumulative cash flow")
        except OverflowError:
            raise ValueError("Cumulative cash flow is outside the supported numeric range") from None
        rows.append({
            "month": expected_month,
            "inputs": current,
            "processed_items": result["processed_items_per_month"],
            "gross_handling_hours_released": result["gross_handling_hours_released"],
            "net_capacity_hours_after_oversight": result["net_capacity_hours_after_oversight"],
            "gross_cash_reduction": result["gross_monthly_cash_reduction"],
            "recurring_cash_cost": result["monthly_incremental_recurring_cost"],
            "implementation_payment": payment,
            "net_cash_flow": net,
            "cumulative_cash_flow": cumulative,
            "interpretation_flags": interpretation_flags(current, result),
        })

    def first(predicate):
        return next((row["month"] for row in rows if predicate(row)), None)

    first_nonnegative = first(lambda row: row["cumulative_cash_flow"] >= 0)
    first_recovery = None
    had_deficit = opening < 0
    for row in rows:
        if had_deficit and row["cumulative_cash_flow"] >= 0:
            first_recovery = row["month"]
            break
        had_deficit = had_deficit or row["cumulative_cash_flow"] < 0
    # A later loss can reverse an earlier recovery. Look across the entire supplied horizon.
    sustained = first(lambda row: all(later["cumulative_cash_flow"] >= 0
                                      for later in rows[row["month"] - 1:]))
    full_budget_recovery = first(lambda row: row["month"] >= last_payment and
                                all(later["cumulative_cash_flow"] >= 0
                                    for later in rows[row["month"] - 1:]))
    try:
        gross = finite(math.fsum(row["gross_cash_reduction"] for row in rows), "Total cash reduction")
        recurring = finite(math.fsum(row["recurring_cash_cost"] for row in rows), "Total recurring cost")
        total_cost = finite(base["one_time_implementation"] + recurring, "Total cash cost")
        net_total = rows[-1]["cumulative_cash_flow"]
        roi = finite((net_total / total_cost) * 100, "Horizon ROI") if total_cost > 0 else None
    except OverflowError:
        raise ValueError("Horizon totals are outside the supported numeric range") from None
    lowest = min([opening] + [row["cumulative_cash_flow"] for row in rows])
    return {
        "schema_version": 1,
        "title": title,
        "evidence_status": evidence,
        "currency": currency,
        "base_inputs": base,
        "implementation_payments": [{"month": month, "amount": payments[month]} for month in sorted(payments)],
        "month_zero_cash_flow": opening,
        "months": rows,
        "summary": {
            "horizon_months": horizon,
            "gross_cash_reduction_total": gross,
            "recurring_cash_cost_total": recurring,
            "implementation_budget": base["one_time_implementation"],
            "total_cash_cost": total_cost,
            "net_cash_flow_total": net_total,
            "roi_on_total_cash_cost_pct": roi,
            "largest_modelled_funding_gap": max(0.0, -lowest),
            "first_nonnegative_closing_month": first_nonnegative,
            "first_recovery_after_deficit_month": first_recovery,
            "nonnegative_through_horizon_from_month": sustained,
            "full_budget_recovered_through_horizon_from_month": full_budget_recovery,
            "last_implementation_payment_month": last_payment,
        },
        "boundaries": [
            "All months, adoption, volumes and costs are supplied assumptions; no adoption curve is inferred.",
            "Each monthly override merges with the same base inputs, not with the previous month.",
            "Implementation payments must cover the entire declared budget within months 0 to the horizon; they are counted once.",
            "The same capacity, cash realization and incremental oversight definitions as assess.py apply in each month.",
            "A nonnegative month is not an investment payback claim. A later loss or payment can reverse an earlier recovery.",
            "Through-horizon recovery describes only the supplied period, after all scheduled implementation payments; it does not guarantee future payback.",
            "Funding gap uses undiscounted cumulative incremental cash flows with a starting balance of zero. It is not a complete working-capital or financing requirement.",
            "No revenue uplift, tax, financing, discounting, terminal value or activity beyond the last supplied month is included.",
        ],
    }


def markdown(report):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    def month(value):
        return "Not reached / not applicable" if value is None else str(value)

    s = report["summary"]
    c = report["currency"]
    lines = ["# " + clean(report["title"]), "", "**Evidence status:** " + clean(report["evidence_status"]), "",
             "Calculation of supplied assumptions. The shipped example is synthetic; this tool does not verify customer results.", "",
             "## Horizon summary", "", "| Measure | Result |", "|---|---:|",
             f"| Modelled months | {s['horizon_months']} |",
             f"| Gross cash reduction, {c} | {fmt(s['gross_cash_reduction_total'])} |",
             f"| Recurring cash cost, {c} | {fmt(s['recurring_cash_cost_total'])} |",
             f"| Implementation budget paid, {c} | {fmt(s['implementation_budget'])} |",
             f"| Total cash cost, {c} | {fmt(s['total_cash_cost'])} |",
             f"| Net cumulative cash flow, {c} | {fmt(s['net_cash_flow_total'])} |",
             f"| ROI on total cash cost | {fmt(s['roi_on_total_cash_cost_pct'])}{'%' if s['roi_on_total_cash_cost_pct'] is not None else ''} |",
             f"| Largest modelled funding gap, {c} | {fmt(s['largest_modelled_funding_gap'])} |",
             f"| First nonnegative closing month | {month(s['first_nonnegative_closing_month'])} |",
             f"| First recovery after a deficit | {month(s['first_recovery_after_deficit_month'])} |",
             f"| Nonnegative through this horizon from month | {month(s['nonnegative_through_horizon_from_month'])} |",
             f"| Full budget paid and nonnegative through this horizon from month | {month(s['full_budget_recovered_through_horizon_from_month'])} |", "",
             "These recovery measures are confined to the supplied horizon. They are not a guarantee about later cash flow.", "",
             "## Monthly cash flow", "",
             f"Month 0 implementation payment: {c} {fmt(-report['month_zero_cash_flow'])}; opening cumulative cash flow: {c} {fmt(report['month_zero_cash_flow'])}.", "",
             f"| Month | Volume | Adoption | Model/infra {c} | Net capacity h | Gross cash {c} | Recurring {c} | Implementation {c} | Net flow {c} | Cumulative {c} |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["months"]:
        p = row["inputs"]
        values = [str(row["month"]), fmt(p["monthly_volume"]), fmt(p["adoption"] * 100) + "%",
                  fmt(p["model_and_infra"]), fmt(row["net_capacity_hours_after_oversight"]),
                  fmt(row["gross_cash_reduction"]), fmt(row["recurring_cash_cost"]),
                  fmt(row["implementation_payment"]), fmt(row["net_cash_flow"]), fmt(row["cumulative_cash_flow"])]
        lines.append("| " + " | ".join(values) + " |")
    flags = [(row["month"], flag) for row in report["months"] for flag in row["interpretation_flags"]]
    if flags:
        lines += ["", "## Capacity and operating interpretation", ""]
        lines += [f"- Month {index}: {flag}" for index, flag in flags]
    lines += ["", "## Boundaries", ""]
    lines += ["- " + line for line in report["boundaries"]]
    lines += ["", "See `docs/cashflow.md` for the schema, payment and recovery definitions. Exact monthly assumptions are recorded in the companion JSON report.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Monthly rollout JSON file")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/cashflow"))
    args = parser.parse_args(argv)
    try:
        report = build_cashflow(load_json(args.input))
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "cashflow.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        (args.output_dir / "cashflow.md").write_text(markdown(report), encoding="utf-8")
    except (OSError, ValueError, TypeError, OverflowError) as error:
        parser.exit(2, f"Cash-flow assessment failed: {error}\n")
    s = report["summary"]
    print("Evidence: " + report["evidence_status"])
    print(f"Net cash flow over {s['horizon_months']} months: {report['currency']} {fmt(s['net_cash_flow_total'])}")
    print("Full budget paid and nonnegative through horizon from month: " + str(s["full_budget_recovered_through_horizon_from_month"]))
    print(f"Reports written to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
