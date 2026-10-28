import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assess import evaluate
from cashflow import build_cashflow, markdown

ROOT = Path(__file__).resolve().parents[1]


class CashflowTests(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads((ROOT / "examples/staged-rollout.json").read_text())
        # Independently simple example: 10 hours at 1 EUR, 2 EUR recurring => 8 EUR/month.
        self.base = {
            "monthly_volume": 10, "eligible_share": 1, "adoption": 1,
            "minutes_before": 60, "minutes_after": 0, "loaded_hourly_cost": 1,
            "cash_realization_rate": 1, "one_time_implementation": 24,
            "recurring_ops": 2, "model_and_infra": 0, "oversight_hours": 0,
            "oversight_incremental_hourly_cost": 0,
        }
        self.document = {"schema_version": 1, "currency": "EUR", "inputs": self.base,
                         "implementation_payments": [{"month": 0, "amount": 24}],
                         "months": [{"month": i, "overrides": {}} for i in range(1, 13)]}

    def test_constant_year_matches_existing_model_and_budget_counted_once(self):
        report = build_cashflow(self.document)
        s = report["summary"]
        self.assertEqual(s["gross_cash_reduction_total"], 120)
        self.assertEqual(s["recurring_cash_cost_total"], 24)
        self.assertEqual(s["total_cash_cost"], 48)
        self.assertEqual(s["net_cash_flow_total"], 72)
        self.assertEqual(s["roi_on_total_cash_cost_pct"], 150)
        self.assertEqual(s["largest_modelled_funding_gap"], 24)
        self.assertEqual(s["first_nonnegative_closing_month"], 3)
        self.assertEqual(s["first_recovery_after_deficit_month"], 3)
        self.assertEqual(s["full_budget_recovered_through_horizon_from_month"], 3)
        annual = evaluate(self.base)
        self.assertEqual(s["net_cash_flow_total"], annual["first_year_net_cash_benefit"])
        self.assertEqual(s["total_cash_cost"], annual["first_year_total_cost"])

    def test_delayed_payment_separates_first_positive_from_recovery(self):
        self.document["implementation_payments"] = [{"month": 2, "amount": 24}]
        s = build_cashflow(self.document)["summary"]
        self.assertEqual(s["first_nonnegative_closing_month"], 1)
        self.assertEqual(s["first_recovery_after_deficit_month"], 3)
        self.assertEqual(s["nonnegative_through_horizon_from_month"], 3)

    def test_full_budget_recovery_waits_for_all_scheduled_payments(self):
        self.base["one_time_implementation"] = 5
        self.document["implementation_payments"] = [{"month": 4, "amount": 5}]
        s = build_cashflow(self.document)["summary"]
        self.assertEqual(s["first_nonnegative_closing_month"], 1)
        self.assertIsNone(s["first_recovery_after_deficit_month"])
        self.assertEqual(s["nonnegative_through_horizon_from_month"], 1)
        self.assertEqual(s["full_budget_recovered_through_horizon_from_month"], 4)

    def test_later_loss_can_reverse_earlier_recovery(self):
        self.document["months"][4]["overrides"] = {"recurring_ops": 102}
        s = build_cashflow(self.document)["summary"]
        self.assertEqual(s["first_recovery_after_deficit_month"], 3)
        self.assertIsNone(s["nonnegative_through_horizon_from_month"])
        self.assertIsNone(s["full_budget_recovered_through_horizon_from_month"])
        self.assertEqual(s["net_cash_flow_total"], -28)

    def test_overrides_do_not_stick_to_following_month_or_mutate_source(self):
        self.document["months"][0]["overrides"] = {"adoption": 0}
        original = copy.deepcopy(self.document)
        report = build_cashflow(self.document)
        self.assertEqual(self.document, original)
        self.assertEqual(report["months"][0]["processed_items"], 0)
        self.assertEqual(report["months"][1]["processed_items"], 10)
        self.assertEqual(report["summary"]["net_cash_flow_total"], 62)

    def test_zero_budget_no_cash_benefit_has_undefined_roi_and_no_recovery(self):
        self.base.update(one_time_implementation=0, recurring_ops=0, cash_realization_rate=0)
        self.document["implementation_payments"] = []
        s = build_cashflow(self.document)["summary"]
        self.assertIsNone(s["roi_on_total_cash_cost_pct"])
        self.assertIsNone(s["first_recovery_after_deficit_month"])
        self.assertEqual(s["largest_modelled_funding_gap"], 0)
        self.assertEqual(s["full_budget_recovered_through_horizon_from_month"], 1)

    def test_payment_budget_uses_decimal_representations(self):
        self.base["one_time_implementation"] = 0.3
        self.document["implementation_payments"] = [{"month": 0, "amount": 0.1}, {"month": 1, "amount": 0.2}]
        self.assertEqual(build_cashflow(self.document)["summary"]["implementation_budget"], 0.3)
        self.document["implementation_payments"][1]["amount"] = 0.21
        with self.assertRaisesRegex(ValueError, "equal"):
            build_cashflow(self.document)

    def test_payment_shape_types_bounds_and_duplicates_are_rejected(self):
        for schedule in (
            None, [{"month": 0, "amount": 24, "note": "ignored?"}],
            [{"month": True, "amount": 24}], [{"month": 13, "amount": 24}],
            [{"month": -1, "amount": 24}], [{"month": 0, "amount": True}],
            [{"month": 0, "amount": float("nan")}],
            [{"month": 0, "amount": 12}, {"month": 0, "amount": 12}],
        ):
            with self.subTest(schedule=schedule), self.assertRaises(ValueError):
                build_cashflow(dict(self.document, implementation_payments=schedule))

    def test_month_sequence_horizon_and_overrides_rejected(self):
        for change in (
            {"months": self.document["months"][:11]},
            {"months": [{"month": i} for i in range(1, 62)]},
            {"months": [{"month": True}] + self.document["months"][1:]},
            {"months": [{"month": 2}] + self.document["months"][1:]},
            {"months": [{"month": 1, "overrides": {"one_time_implementation": 1}}] + self.document["months"][1:]},
            {"months": [{"month": 1, "overrides": {"adoption": 2}}] + self.document["months"][1:]},
            {"months": [{"month": 1, "overrides": []}] + self.document["months"][1:]},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_cashflow(dict(self.document, **change))

    def test_schema_labels_and_unknown_fields_rejected(self):
        for change in ({"schema_version": True}, {"schema_version": 1.0},
                       {"currency": "eur"}, {"title": []}, {"evidence_status": ""},
                       {"payments_typo": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_cashflow(dict(self.document, **change))

    def test_cumulative_overflow_rejected_even_when_each_month_is_finite(self):
        self.base.update(monthly_volume=1, loaded_hourly_cost=1e307,
                         recurring_ops=0, one_time_implementation=0)
        self.document["implementation_payments"] = []
        self.document["months"] = [{"month": i} for i in range(1, 61)]
        with self.assertRaisesRegex(ValueError, "numeric range"):
            build_cashflow(self.document)

    def test_synthetic_rollout_is_reproducible_and_ramp_changes_the_result(self):
        report = build_cashflow(self.sample)
        s = report["summary"]
        self.assertAlmostEqual(s["net_cash_flow_total"], 6063.04)
        self.assertAlmostEqual(s["largest_modelled_funding_gap"], 9794.64)
        self.assertEqual(s["full_budget_recovered_through_horizon_from_month"], 9)
        self.assertLess(s["net_cash_flow_total"], evaluate(self.sample["inputs"])["first_year_net_cash_benefit"])
        self.assertIn("synthetic", markdown(report))
        self.assertIn("not a guarantee", markdown(report))
        json.dumps(report, allow_nan=False)

    def test_cli_writes_companion_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, str(ROOT / "cashflow.py"),
                                  str(ROOT / "examples/staged-rollout.json"),
                                  "--output-dir", directory], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("6,063.04", run.stdout)
            self.assertEqual(json.loads((Path(directory) / "cashflow.json").read_text())["summary"]["horizon_months"], 12)
            self.assertTrue((Path(directory) / "cashflow.md").exists())


if __name__ == "__main__":
    unittest.main()
