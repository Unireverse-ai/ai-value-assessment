/* The browser model mirrors assess.evaluate. No network access or dependencies. */
(function (root) {
  "use strict";
  const fields = ["monthly_volume", "eligible_share", "adoption", "minutes_before", "minutes_after", "loaded_hourly_cost", "cash_realization_rate", "one_time_implementation", "recurring_ops", "model_and_infra", "oversight_hours", "oversight_incremental_hourly_cost"];
  const fractions = new Set(["eligible_share", "adoption", "cash_realization_rate"]);
  function evaluate(p) {
    if (!p || typeof p !== "object" || Array.isArray(p)) throw new Error("Inputs must be an object.");
    if (Object.keys(p).some(key => !fields.includes(key))) throw new Error("Unknown input.");
    for (const key of fields) {
      if (typeof p[key] !== "number" || !Number.isFinite(p[key]) || p[key] < 0) throw new Error(key + " must be finite and non-negative.");
      if (fractions.has(key) && p[key] > 1) throw new Error(key + " must be between 0 and 1.");
    }
    const processed = p.monthly_volume * p.eligible_share * p.adoption;
    const hours = processed * (p.minutes_before - p.minutes_after) / 60;
    const potential = hours * p.loaded_hourly_cost;
    const cash = potential * p.cash_realization_rate;
    const oversight = p.oversight_hours * p.oversight_incremental_hourly_cost;
    const recurring = p.recurring_ops + p.model_and_infra + oversight;
    const net = cash - recurring;
    const yearCost = p.one_time_implementation + 12 * recurring;
    const yearNet = 12 * net - p.one_time_implementation;
    const result = {
      processed_items_per_month: processed,
      gross_handling_hours_released: hours,
      net_capacity_hours_after_oversight: hours - p.oversight_hours,
      handling_cost_potential: potential,
      gross_monthly_cash_reduction: cash,
      monthly_oversight_cash_cost: oversight,
      monthly_incremental_recurring_cost: recurring,
      monthly_net_cash_benefit: net,
      simple_payback_months: net > 0 ? p.one_time_implementation / net : null,
      first_year_total_cost: yearCost,
      first_year_net_cash_benefit: yearNet,
      first_year_roi_on_total_cost_pct: yearCost > 0 ? 100 * yearNet / yearCost : null
    };
    if (Object.values(result).some(value => value !== null && !Number.isFinite(value))) throw new Error("Inputs produce results outside the supported numeric range.");
    return result;
  }
  const api = {evaluate, fields, fractions};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ValueModel = api;
})(typeof globalThis === "undefined" ? this : globalThis);
