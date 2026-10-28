/* Synthetic presets; kept in parity with examples/manufacturing.json. */
(function(root) {
  const sample = {
  "schema_version": 1,
  "title": "Synthetic manufacturing enquiry workflow — investment assessment",
  "evidence_status": "Illustrative assumptions only. Not measured results, a client quote, or a UniReverseAI deployment.",
  "currency": "EUR",
  "inputs": {
    "monthly_volume": 1200,
    "eligible_share": 0.8,
    "adoption": 0.7,
    "minutes_before": 18,
    "minutes_after": 7,
    "loaded_hourly_cost": 32,
    "cash_realization_rate": 0.25,
    "one_time_implementation": 12000,
    "recurring_ops": 240,
    "model_and_infra": 180,
    "oversight_hours": 8,
    "oversight_incremental_hourly_cost": 36
  },
  "scenarios": [
    {
      "name": "Conservative",
      "overrides": {
        "eligible_share": 0.65,
        "adoption": 0.5,
        "minutes_after": 10,
        "cash_realization_rate": 0.1,
        "oversight_hours": 12
      }
    },
    {
      "name": "Base",
      "overrides": {}
    },
    {
      "name": "Optimistic",
      "overrides": {
        "eligible_share": 0.9,
        "adoption": 0.9,
        "minutes_after": 5,
        "cash_realization_rate": 0.4,
        "model_and_infra": 240,
        "oversight_hours": 6
      }
    }
  ]
};
  if (typeof module !== "undefined" && module.exports) module.exports = sample;
  else root.ValueExample = sample;
})(typeof globalThis === "undefined" ? this : globalThis);
