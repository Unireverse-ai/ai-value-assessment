import copy
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assess import build_report, evaluate, load_json, markdown, validate_inputs

ROOT = Path(__file__).resolve().parents[1]


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "examples/manufacturing.json").read_text())
        self.inputs = self.document["inputs"]

    def test_base_arithmetic_is_independently_checkable(self):
        result = evaluate(self.inputs)
        self.assertAlmostEqual(result["processed_items_per_month"], 672)
        self.assertAlmostEqual(result["gross_handling_hours_released"], 123.2)
        self.assertAlmostEqual(result["net_capacity_hours_after_oversight"], 115.2)
        self.assertAlmostEqual(result["gross_monthly_cash_reduction"], 985.6)
        self.assertAlmostEqual(result["monthly_incremental_recurring_cost"], 708)
        self.assertAlmostEqual(result["monthly_net_cash_benefit"], 277.6)
        self.assertAlmostEqual(result["simple_payback_months"], 12000 / 277.6)
        self.assertAlmostEqual(result["first_year_net_cash_benefit"], -8668.8)
        self.assertAlmostEqual(result["first_year_roi_on_total_cost_pct"], -8668.8 / 20496 * 100)

    def test_capacity_does_not_automatically_become_cash(self):
        result = evaluate(dict(self.inputs, cash_realization_rate=0))
        self.assertGreater(result["net_capacity_hours_after_oversight"], 0)
        self.assertEqual(result["gross_monthly_cash_reduction"], 0)
        self.assertEqual(result["monthly_net_cash_benefit"], -708)
        self.assertIsNone(result["simple_payback_months"])

    def test_existing_payroll_oversight_reduces_capacity_but_adds_no_cash_cost(self):
        result = evaluate(dict(self.inputs, oversight_incremental_hourly_cost=0))
        self.assertAlmostEqual(result["net_capacity_hours_after_oversight"], 115.2)
        self.assertEqual(result["monthly_oversight_cash_cost"], 0)
        self.assertAlmostEqual(result["monthly_net_cash_benefit"], 565.6)

    def test_extra_oversight_counted_once_in_cash_cost(self):
        result = evaluate(dict(self.inputs, oversight_hours=9))
        self.assertAlmostEqual(result["gross_monthly_cash_reduction"], 985.6)
        self.assertAlmostEqual(result["monthly_net_cash_benefit"], 277.6 - 36)
        self.assertAlmostEqual(result["net_capacity_hours_after_oversight"], 114.2)

    def test_zero_volume_or_adoption_has_no_handling_benefit(self):
        for field in ("monthly_volume", "eligible_share", "adoption"):
            with self.subTest(field=field):
                result = evaluate(dict(self.inputs, **{field: 0}))
                self.assertEqual(result["gross_handling_hours_released"], 0)
                self.assertEqual(result["monthly_net_cash_benefit"], -708)

    def test_no_time_improvement_has_no_handling_benefit(self):
        result = evaluate(dict(self.inputs, minutes_after=self.inputs["minutes_before"]))
        self.assertEqual(result["gross_handling_hours_released"], 0)

    def test_slower_handling_is_not_hidden(self):
        result = evaluate(dict(self.inputs, minutes_after=25))
        self.assertLess(result["gross_handling_hours_released"], 0)
        self.assertLess(result["gross_monthly_cash_reduction"], 0)
        self.assertIsNone(result["simple_payback_months"])

    def test_non_positive_net_has_no_payback(self):
        for cash in (0, 100):
            p = dict(self.inputs, monthly_volume=60, eligible_share=1, adoption=1,
                     minutes_before=60, minutes_after=0, loaded_hourly_cost=1,
                     cash_realization_rate=1, recurring_ops=cash,
                     model_and_infra=0, oversight_hours=0)
            if cash == 0:
                p["recurring_ops"] = 60  # Exactly zero monthly net.
            self.assertIsNone(evaluate(p)["simple_payback_months"])

    def test_zero_investment_and_positive_net_returns_zero_payback(self):
        result = evaluate(dict(self.inputs, one_time_implementation=0))
        self.assertEqual(result["simple_payback_months"], 0)

    def test_zero_total_cost_yields_undefined_roi(self):
        result = evaluate(dict(self.inputs, one_time_implementation=0, recurring_ops=0,
                               model_and_infra=0, oversight_incremental_hourly_cost=0))
        self.assertIsNone(result["first_year_roi_on_total_cost_pct"])

    def test_fractions_are_bounded(self):
        for field in ("eligible_share", "adoption", "cash_realization_rate"):
            for value in (-0.01, 1.01):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    evaluate(dict(self.inputs, **{field: value}))

    def test_negative_non_numeric_boolean_and_non_finite_rejected(self):
        for value in (-1, "1200", True, float("inf"), float("nan"), None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate(dict(self.inputs, monthly_volume=value))

    def test_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(dict(self.inputs, monthly_volume=1e308, minutes_before=1e308))

    def test_very_large_integer_has_a_clear_validation_error(self):
        with self.assertRaisesRegex(ValueError, "numeric range"):
            evaluate(dict(self.inputs, monthly_volume=10 ** 1000))

    def test_roi_does_not_overflow_a_finite_ratio(self):
        p = dict(self.inputs, monthly_volume=1, eligible_share=1, adoption=1,
                 minutes_before=60, minutes_after=0, loaded_hourly_cost=1e306,
                 cash_realization_rate=1, one_time_implementation=1e307,
                 recurring_ops=0, model_and_infra=0, oversight_hours=0)
        self.assertAlmostEqual(evaluate(p)["first_year_roi_on_total_cost_pct"], 20)

    def test_negative_capacity_with_positive_cash_is_flagged_not_hidden(self):
        p = dict(self.inputs, oversight_hours=200, oversight_incremental_hourly_cost=0)
        report = build_report(dict(self.document, inputs=p, scenarios=[{"name": "Review load"}]))
        self.assertLess(report["base_results"]["net_capacity_hours_after_oversight"], 0)
        self.assertGreater(report["base_results"]["monthly_net_cash_benefit"], 0)
        self.assertTrue(any("operational feasibility" in line for line in report["base_interpretation_flags"]))
        self.assertIn("net human effort increases", markdown(report))

    def test_json_rejects_duplicate_keys_and_nonstandard_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.json"
            for text in ('{"inputs":{"adoption":0.1,"adoption":0.9}}',
                         '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}'):
                with self.subTest(text=text), self.assertRaises(ValueError):
                    source.write_text(text)
                    load_json(source)

    def test_document_version_labels_and_unknown_fields_are_strict(self):
        for change in ({"schema_version": True}, {"schema_version": 1.0},
                       {"title": []}, {"evidence_status": ""}, {"scenario_typo": []},
                       {"scenarios": [{"name": "A", "override_typo": {}}]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_report(dict(self.document, **change))

    def test_cli_duplicate_input_fails_without_writing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "duplicate.json"
            source.write_text('{"schema_version":1,"schema_version":1}')
            out = Path(directory) / "out"
            run = subprocess.run([sys.executable, str(ROOT / "assess.py"), str(source),
                                  "--output-dir", str(out)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("Duplicate JSON object key", run.stderr)
            self.assertFalse(out.exists())

    def test_missing_unknown_inputs_are_rejected(self):
        p = dict(self.inputs)
        del p["adoption"]
        with self.assertRaisesRegex(ValueError, "Missing"):
            evaluate(p)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            evaluate(dict(self.inputs, adoption_typo=0.5))

    def test_scenarios_do_not_mutate_base_or_each_other(self):
        original = copy.deepcopy(self.document)
        report = build_report(self.document)
        self.assertEqual(self.document, original)
        self.assertEqual(report["scenarios"][1]["inputs"], self.inputs)
        self.assertAlmostEqual(report["scenarios"][0]["results"]["monthly_net_cash_benefit"], -685.6)
        self.assertAlmostEqual(report["scenarios"][2]["results"]["monthly_net_cash_benefit"], 1999.68)

    def test_bad_scenario_overrides_and_names_rejected(self):
        for scenarios in (
            [], [{"name": "A", "overrides": {"made_up": 1}}],
            [{"name": "A"}, {"name": "A"}], [{"name": ""}],
            [{"name": "A", "overrides": []}], ["A"],
        ):
            with self.subTest(scenarios=scenarios), self.assertRaises(ValueError):
                build_report(dict(self.document, scenarios=scenarios))

    def test_sensitivity_changes_only_one_factor(self):
        report = build_report(self.document)
        self.assertEqual(len(report["sensitivity"]), 10)
        for row in report["sensitivity"]:
            expected = evaluate(dict(self.inputs, **{row["varied_input"]: row["value"]}))
            self.assertEqual(row["results"], expected)

    def test_invalid_currency_and_schema_rejected(self):
        for currency in ("euro", "eur", "<x>", 1, "123"):
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                build_report(dict(self.document, currency=currency))
        with self.assertRaises(ValueError):
            build_report(dict(self.document, schema_version=2))

    def test_reports_preserve_evidence_labels_and_undefined_values(self):
        report = build_report(self.document)
        text = markdown(report)
        self.assertIn("Not measured results", text)
        self.assertIn("Not reached / undefined", text)
        self.assertIn("not a measured customer result", text)
        json.dumps(report, allow_nan=False)

    def test_cli_creates_reports_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / "assess.py"),
                                     str(ROOT / "examples/manufacturing.json"),
                                     "--output-dir", directory],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("277.60", result.stdout)
            report = json.loads((Path(directory) / "assessment.json").read_text())
            self.assertEqual(len(report["scenarios"]), 3)
            self.assertTrue((Path(directory) / "assessment.md").exists())

    def test_cli_bad_input_has_clear_failure_and_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.json"
            source.write_text('{"schema_version": 1}')
            out = Path(directory) / "out"
            result = subprocess.run([sys.executable, str(ROOT / "assess.py"), str(source),
                                     "--output-dir", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("inputs must be an object", result.stderr)
            self.assertFalse(out.exists())

    @unittest.skipUnless(shutil.which("node"), "Optional Node.js is needed only to verify browser parity")
    def test_browser_model_and_presets_match_python(self):
        inputs = [dict(self.inputs, **s["overrides"]) for s in self.document["scenarios"]]
        inputs += [dict(self.inputs, **change) for change in (
            {"cash_realization_rate": 0}, {"adoption": 0}, {"monthly_volume": 0},
            {"minutes_after": 25}, {"oversight_incremental_hourly_cost": 0},
            {"one_time_implementation": 0},
            {"one_time_implementation": 0, "recurring_ops": 0, "model_and_infra": 0,
             "oversight_incremental_hourly_cost": 0},
        )]
        inputs.append(dict(self.inputs, monthly_volume=1, eligible_share=1, adoption=1,
                           minutes_before=60, minutes_after=0, loaded_hourly_cost=1e306,
                           cash_realization_rate=1, one_time_implementation=1e307,
                           recurring_ops=0, model_and_infra=0, oversight_hours=0))
        script = """
const model = require('./calculator.js');
const sample = require('./calculator-example.js');
let input = '';
process.stdin.on('data', data => input += data);
process.stdin.on('end', () => {
  const cases = JSON.parse(input);
  const values = cases.map(value => model.evaluate(value));
  let rejected = 0;
  for (const invalid of [
    {...cases[0], adoption: 1.1}, {...cases[0], monthly_volume: true},
    {...cases[0], minutes_after: -1}, {...cases[0], made_up: 1}
  ]) {try {model.evaluate(invalid);} catch (error) {rejected++;}}
  process.stdout.write(JSON.stringify({sample, values, rejected}));
});
"""
        result = subprocess.run([shutil.which("node"), "-e", script], cwd=str(ROOT),
                                input=json.dumps(inputs), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["sample"], self.document)
        self.assertEqual(payload["rejected"], 4)
        for actual, p in zip(payload["values"], inputs):
            expected = evaluate(p)
            self.assertEqual(set(actual), set(expected))
            for name, value in expected.items():
                with self.subTest(field=name, inputs=p):
                    if value is None:
                        self.assertIsNone(actual[name])
                    else:
                        self.assertTrue(math.isclose(actual[name], value, rel_tol=1e-12, abs_tol=1e-8), (actual[name], value))


if __name__ == "__main__":
    unittest.main()
