# SupplyZen — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

Supply chain resilience is fundamentally about **reducing variance in outcomes** — not just minimising expected cost. A supply chain optimised purely for cost efficiency will be brittle under disruption. Your task is to find the efficient frontier between cost and resilience: how much are you willing to pay in normal conditions to protect against extreme disruption scenarios? The key insight is that **safety stock, dual sourcing, and nearshoring are insurance policies** — you pay a premium every year to avoid catastrophic cost spikes during disruptions. Start by quantifying the cost of disruption (how much does a 6-week shortage of a critical component cost in lost production?) and compare it to the annual cost of each mitigation option.

## Tier 2 — Framework Guidance (-10% score penalty)

Use a **risk exposure matrix** to prioritise components:
`Risk Score = (1 - financial_stability/100) × geopolitical_risk/100 × (1 if single_source else 0.3) × (2 if critical else 1)`

For the **optimisation model**, formulate as a mixed-integer linear programme (MILP) or use a simpler heuristic model:
- **Decision variables**: `x[component, supplier]` = fraction of component volume from each supplier; `I[component]` = inventory buffer level (weeks of supply)
- **Objective**: Minimise `Σ (unit_cost × volume × x) + Σ (holding_cost × I)` subject to disruption scenarios
- **Key constraints**: `Σ x[component, supplier] = 1` (full coverage), `I[component] >= safety_stock_weeks` for critical components, `lead_time × (1-x[alt_supplier]) <= max_acceptable_lead_time`

For **scenario analysis**, use three scenarios: (1) Base case (current disruptions continue), (2) Moderate (tariff + semiconductor shortage), (3) Severe (tariff + shortage + Red Sea + Taiwan earthquake). For each, compute: probability (your estimate), total cost impact ($M), production volume impact (units), revenue at risk ($B).

For **mitigation strategy scoring**, use a weighted scorecard: cost of implementation, expected risk reduction (%), implementation time (months), operational complexity.

## Tier 3 — Structural Guidance (-15% score penalty)

Structure your `submission.json` as follows:

**`risk_assessment`**: Report `single_source_critical_count` (number of components that are both single-source and critical), a `top_10_risk_exposures` list (component_id, risk_score, annual_volume, estimated_disruption_cost_usd_m), and a `country_concentration` table showing % of procurement spend by country.

**`optimization_model`**: Write the mathematical formulation explicitly — objective function (minimize Z = procurement cost + inventory cost), decision variables (x, I), and at least 4 named constraints. Report the optimal solution: which suppliers to dual-source first, recommended inventory buffer by component tier, total incremental cost of the optimised solution.

**`scenario_analysis`**: Three scenarios, each with: `probability_pct`, `description`, `disrupted_components_count`, `production_shortfall_units`, `revenue_at_risk_usd_m`, `total_cost_impact_usd_m`. Compute `expected_value = Σ probability × cost_impact` for comparison.

**`mitigation_strategies`**: Evaluate all 6 strategies from the problem statement (dual sourcing, nearshoring, inventory buffering, product redesign, vertical integration, digital twin). For each: `annual_cost_usd_m`, `implementation_months`, `expected_risk_reduction_pct`, `roi_3yr`, `recommended_priority` (1-6).

**`implementation_plan`**: 18-month Gantt-style roadmap with 6 phases. Each phase: `phase_name`, `months`, `actions` (list), `kpis` (list), `investment_usd_m`.
