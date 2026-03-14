# SupplyZen — Quick Start

## Objective
You are the Chief Supply Chain Officer at ElectraTech, a $10B consumer electronics company. Simultaneously facing semiconductor shortages, Red Sea disruption, a supplier factory fire, and potential tariffs, you must design a resilient supply chain optimisation model that minimises total cost while maintaining a 95%+ service level.

## Inputs
All data files are in `prerequisites/MBA/MBA-P3/` — run `generate_mba_p3.py` first if files are absent.

- **supply_chain.csv** (2,000 rows): `component_id`, `component_name`, `component_type`, `sku`, `tier_level` (1/2/3), `supplier_id`, `supplier_name`, `supplier_country`, `annual_volume`, `unit_cost_usd`, `lead_time_days`, `is_single_source` (0/1), `critical_component` (0/1)
- **supplier_risk_matrix.csv** (500 rows): `supplier_id`, `supplier_name`, `country`, `financial_stability_score` (0–100), `geopolitical_risk_score` (0–100), `natural_disaster_risk` (0–100), `single_customer_dependency_pct`, `quality_score` (0–100), `on_time_delivery_pct` (0–100), `risk_tier` (Low/Medium/High/Critical)
- **disruption_events.csv** (50 rows): `event_id`, `event_date`, `event_type`, `affected_supplier_ids`, `affected_regions`, `impact_severity`, `duration_weeks`, `cost_impact_usd_million`, `recovery_status`
- **inventory_levels.csv** (2,000 rows): `component_id`, `current_stock_units`, `weeks_of_supply`, `reorder_point`, `safety_stock_units`, `last_replenishment_date`

## Expected Output
A structured JSON file (`submission.json`) with:
```
submission.json
├── risk_assessment         (single-source analysis, risk heatmap, top-10 risk exposures)
├── optimization_model      (mathematical formulation, decision variables, constraints)
├── scenario_analysis       (3 disruption scenarios: base/moderate/severe, financial impact)
├── mitigation_strategies   (scored comparison of dual-sourcing, nearshoring, inventory, etc.)
└── implementation_plan     (18-month prioritised roadmap with KPIs and milestones)
```

## Recommended First Steps
1. Run `python starter.py --data-dir <path_to_MBA-P3>` to load all datasets and generate a risk exposure summary in `analysis.json` — this will identify your highest-priority critical/single-source components
2. Filter `supply_chain.csv` for `is_single_source=1` AND `critical_component=1` — these are your maximum-risk components; count them and note their component types and supplier countries
3. Join `supply_chain.csv` with `supplier_risk_matrix.csv` on `supplier_id` to compute a combined component-level risk score (financial × geopolitical × dependency)

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Risk Identification (single-points-of-failure, exposure quantification, heatmap) | 30% |
| Optimization Model (mathematical formulation, objective function, constraints) | 30% |
| Scenario Analysis (3 scenarios, financial impact, probability-weighted EV) | 25% |
| Implementation Plan (prioritised 18-month roadmap with milestones and KPIs) | 15% |

## Common Pitfalls
- Treating all 2,000 components as equally important — triage by `critical_component` and `is_single_source` first; the top 50 components drive 80% of risk exposure
- Omitting the financial quantification — risk identification without expected cost (probability × impact) is insufficient
- Building a purely qualitative "risk heatmap" without numerical scores — judges expect a risk score formula
- Ignoring Tier 2 and Tier 3 dependencies — the semiconductor shortage is a Tier 2 problem; Tier 1 supplier may look fine while Tier 2 fails
- Recommending all mitigation strategies without cost-benefit analysis — each strategy has a cost and expected value; rank them explicitly
