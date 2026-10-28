(function () {
  "use strict";
  const model = window.ValueModel;
  const sample = window.ValueExample;
  let current = null;
  let result = null;
  const number = value => new Intl.NumberFormat("en-GB", {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(value);
  const eur = value => "EUR " + number(value);
  const node = id => document.getElementById(id);
  const text = (id, value) => {node(id).textContent = value;};
  function amount(id, value, unit) {
    const target = node(id);
    target.replaceChildren(document.createTextNode(number(value) + " "));
    const small = document.createElement("small");
    small.textContent = unit;
    target.append(small);
  }
  function load(index) {
    const preset = sample.scenarios[index];
    const inputs = {...sample.inputs, ...preset.overrides};
    for (const name of model.fields) node(name).value = inputs[name] * (model.fractions.has(name) ? 100 : 1);
    for (const button of document.querySelectorAll("[data-preset]")) {
      const active = Number(button.dataset.preset) === index;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    text("preset-name", preset.name + " assumptions");
    update();
  }
  function update() {
    try {
      const inputs = {};
      for (const name of model.fields) {
        const input = node(name);
        if (!input.value.trim()) throw new Error("Complete every input to calculate a result.");
        inputs[name] = Number(input.value) / (model.fractions.has(name) ? 100 : 1);
      }
      const r = model.evaluate(inputs);
      current = inputs;
      result = r;
      text("error", "");
      node("results").hidden = false;
      for (const button of document.querySelectorAll(".download button")) button.disabled = false;
      amount("capacity", r.net_capacity_hours_after_oversight, "h / month");
      amount("monthly", r.monthly_net_cash_benefit, "EUR");
      if (r.simple_payback_months === null) text("payback", "Not reached");
      else amount("payback", r.simple_payback_months, "months");
      amount("year-net", r.first_year_net_cash_benefit, "EUR");
      text("roi-line", r.first_year_roi_on_total_cost_pct === null ? "Year-one ROI is undefined (zero total cost)." : number(r.first_year_roi_on_total_cost_pct) + "% year-one ROI on total cost.");
      const interpretation = r.monthly_net_cash_benefit <= 0
        ? "The current assumptions do not produce positive monthly cash benefit. More capacity alone does not establish a cash return."
        : r.first_year_net_cash_benefit < 0
          ? "The current assumptions produce a positive monthly benefit, but the implementation cost is not recovered within the first year."
          : "The current assumptions recover the implementation cost within the first year. Confirm the quality, adoption, and cash mechanism with measured evidence.";
      text("interpretation", interpretation);
      text("processed", number(r.processed_items_per_month));
      text("gross-hours", number(r.gross_handling_hours_released) + " h");
      text("potential", eur(r.handling_cost_potential));
      text("gross-cash", eur(r.gross_monthly_cash_reduction));
      text("operations", eur(inputs.recurring_ops + inputs.model_and_infra));
      text("oversight", eur(r.monthly_oversight_cash_cost));
      text("net-line", eur(r.monthly_net_cash_benefit));
      const body = node("sensitivity");
      body.replaceChildren();
      const values = [...new Set([0, .25, .5, .75, 1, inputs.cash_realization_rate])].sort((a,b) => a-b);
      for (const rate of values) {
        const varied = model.evaluate({...inputs, cash_realization_rate:rate});
        const row = document.createElement("tr");
        if (rate === inputs.cash_realization_rate) row.classList.add("current");
        for (const value of [number(rate * 100) + "%" + (rate === inputs.cash_realization_rate ? " · current" : ""), eur(varied.monthly_net_cash_benefit), varied.simple_payback_months === null ? "Not reached" : number(varied.simple_payback_months) + " mo"]) {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.append(cell);
        }
        body.append(row);
      }
    } catch (error) {
      current = result = null;
      text("error", error.message);
      node("results").hidden = true;
      for (const button of document.querySelectorAll(".download button")) button.disabled = true;
    }
  }
  function download(data, filename) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + "\n"], {type:"application/json"}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  for (const button of document.querySelectorAll("[data-preset]")) button.addEventListener("click", () => load(Number(button.dataset.preset)));
  node("inputs").addEventListener("submit", event => event.preventDefault());
  node("inputs").addEventListener("input", () => {
    for (const button of document.querySelectorAll("[data-preset]")) {
      button.classList.remove("active");
      button.setAttribute("aria-pressed", "false");
    }
    text("preset-name", "Custom assumptions");
    update();
  });
  node("download-inputs").addEventListener("click", () => {
    if (!current) return;
    download({schema_version:1, title:"Custom workflow investment assumptions", evidence_status:"User-edited assumptions; not verified by the calculator", currency:"EUR", inputs:current, scenarios:[{name:"Custom",overrides:{}}]}, "workflow-assumptions.json");
  });
  node("download-results").addEventListener("click", () => {
    if (!current) return;
    download({schema_version:1, evidence_status:"Calculation of user-edited assumptions; not measured customer results", currency:"EUR", inputs:current, results:result, method:"See docs/methodology.md; capacity and cash must not be added together."}, "workflow-calculation.json");
  });
  load(1);
})();
