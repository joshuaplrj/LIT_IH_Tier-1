"""
MBA-P3: SupplyZen — Supply Chain Risk & Optimisation Scaffold
=============================================================
ElectraTech: $10B consumer electronics company facing multiple simultaneous
supply chain disruptions. Identify risks, score suppliers, and build
an optimisation model for resilient supply chain design.

Data directory (default): prerequisites/MBA/MBA-P3/

Usage:
    python starter.py [--data-dir <path>] [--output analysis.json]

Outputs:
    analysis.json  — risk scores, exposure quantification, optimisation skeleton
"""

import argparse
import csv
import json
import os
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY / PROBLEM CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
COMPANY = {
    "name": "ElectraTech",
    "revenue_usd_b": 10.0,
    "annual_units_m": 100,
    "products": ["smartphone", "tablet", "laptop"],
    "n_components": 2_000,
    "n_suppliers": 500,
    "current_inventory_weeks": 3,
    "target_inventory_weeks": 8,
    "service_level_target_pct": 95,
    "max_lead_time_weeks": 4,
    "quality_defect_target_pct": 0.1,
}

# Annual revenue loss per week of production stoppage (rough: $10B / 52)
REVENUE_LOSS_PER_WEEK_USD_M = round(COMPANY["revenue_usd_b"] * 1_000 / 52, 1)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: str) -> list:
    if not os.path.exists(path):
        print(f"  [WARNING] File not found: {path}")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: RISK SCORING
# ─────────────────────────────────────────────────────────────────────────────

def compute_component_risk_scores(supply_chain: list, risk_matrix: dict) -> list:
    """
    Compute a composite risk score for each component.

    Risk Score Formula (0–100 scale):
        base = (geopolitical_risk / 100) × (1 - financial_stability / 100)
        single_source_multiplier = 3.0 if is_single_source else 1.0
        critical_multiplier = 2.0 if critical_component else 1.0
        raw_score = base × single_source_multiplier × critical_multiplier
        risk_score = min(raw_score × 100, 100)

    TODO: Refine the formula based on your risk framework. You may add:
          - lead_time_risk (normalised lead time as fraction of max acceptable)
          - country_concentration_risk (% of spend in single country)
          - disaster_risk contribution
    """
    scored = []

    for row in supply_chain:
        try:
            sid = row.get("supplier_id", "")
            sup_risk = risk_matrix.get(sid, {})

            fin_stability = float(sup_risk.get("financial_stability_score", 70))
            geo_risk = float(sup_risk.get("geopolitical_risk_score", 50))
            disaster_risk = float(sup_risk.get("natural_disaster_risk", 40))
            is_single = int(row.get("is_single_source", 0))
            is_critical = int(row.get("critical_component", 0))
            lead_time = int(row.get("lead_time_days", 30))
            unit_cost = float(row.get("unit_cost_usd", 1.0))
            annual_vol = float(row.get("annual_volume", 1000))

            # Base risk: combination of geopolitical and financial instability
            base = (geo_risk / 100) * (1.0 - fin_stability / 100) * (disaster_risk / 100) ** 0.5

            # Multipliers for supply chain structure
            ss_mult = 3.0 if is_single else 1.0
            crit_mult = 2.0 if is_critical else 1.0

            raw_score = base * ss_mult * crit_mult
            risk_score = min(round(raw_score * 100, 1), 100.0)

            # Disruption cost estimate: unit_cost × annual_volume × 4 weeks of exposure
            disruption_cost_usd_m = round(unit_cost * annual_vol * (lead_time / 365) / 1_000_000, 3)

            scored.append({
                "component_id": row.get("component_id"),
                "component_type": row.get("component_type"),
                "supplier_id": sid,
                "supplier_country": row.get("supplier_country"),
                "is_single_source": is_single,
                "critical_component": is_critical,
                "tier_level": row.get("tier_level"),
                "lead_time_days": lead_time,
                "unit_cost_usd": unit_cost,
                "annual_volume": int(annual_vol),
                "annual_spend_usd_m": round(unit_cost * annual_vol / 1_000_000, 3),
                "risk_score": risk_score,
                "disruption_cost_estimate_usd_m": disruption_cost_usd_m,
                "financial_stability": fin_stability,
                "geopolitical_risk": geo_risk,
                "risk_tier": sup_risk.get("risk_tier", "Unknown"),
            })

        except (ValueError, TypeError) as e:
            continue

    # Sort by risk_score descending
    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    return scored


def build_risk_matrix_lookup(risk_matrix_rows: list) -> dict:
    """Build a dict: {supplier_id: risk_row}."""
    return {row["supplier_id"]: row for row in risk_matrix_rows}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: EXPOSURE QUANTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def quantify_exposure(scored_components: list) -> dict:
    """
    Aggregate risk exposure metrics across the supply chain.
    """
    total_components = len(scored_components)
    single_source_count = sum(1 for c in scored_components if c["is_single_source"])
    critical_count = sum(1 for c in scored_components if c["critical_component"])
    single_critical_count = sum(
        1 for c in scored_components if c["is_single_source"] and c["critical_component"]
    )

    # Country concentration
    spend_by_country = defaultdict(float)
    for c in scored_components:
        spend_by_country[c["supplier_country"]] += c["annual_spend_usd_m"]
    total_spend = sum(spend_by_country.values()) or 1
    country_concentration = {
        k: round(v / total_spend * 100, 1)
        for k, v in sorted(spend_by_country.items(), key=lambda x: -x[1])
    }

    # Top-10 riskiest components
    top_10 = [
        {
            "component_id": c["component_id"],
            "component_type": c["component_type"],
            "supplier_country": c["supplier_country"],
            "risk_score": c["risk_score"],
            "is_single_source": c["is_single_source"],
            "critical_component": c["critical_component"],
            "annual_spend_usd_m": c["annual_spend_usd_m"],
            "disruption_cost_estimate_usd_m": c["disruption_cost_estimate_usd_m"],
        }
        for c in scored_components[:10]
    ]

    # Risk tier distribution
    tier_dist = defaultdict(int)
    for c in scored_components:
        tier_dist[c["risk_tier"]] += 1

    return {
        "total_components": total_components,
        "single_source_count": single_source_count,
        "critical_count": critical_count,
        "single_source_and_critical_count": single_critical_count,
        "pct_single_source": round(single_source_count / total_components * 100, 1) if total_components else 0,
        "pct_critical": round(critical_count / total_components * 100, 1) if total_components else 0,
        "revenue_loss_per_disruption_week_usd_m": REVENUE_LOSS_PER_WEEK_USD_M,
        "country_concentration_pct_spend": country_concentration,
        "top_10_risk_exposures": top_10,
        "risk_tier_distribution": dict(tier_dist),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: DISRUPTION EVENT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyse_disruptions(disruptions: list) -> dict:
    """
    Summarise historical disruption events.
    """
    if not disruptions:
        return {"note": "No disruption data loaded"}

    by_type = defaultdict(list)
    by_severity = defaultdict(int)
    total_cost = 0.0

    for ev in disruptions:
        ev_type = ev.get("event_type", "unknown")
        severity = ev.get("impact_severity", "Low")
        cost = 0.0
        try:
            cost = float(ev.get("cost_impact_usd_million", 0))
        except (ValueError, TypeError):
            pass

        by_type[ev_type].append(cost)
        by_severity[severity] += 1
        total_cost += cost

    type_summary = {
        t: {
            "count": len(costs),
            "total_cost_usd_m": round(sum(costs), 1),
            "avg_cost_usd_m": round(sum(costs) / len(costs), 1) if costs else 0,
        }
        for t, costs in by_type.items()
    }

    return {
        "total_disruption_events": len(disruptions),
        "total_historical_cost_usd_m": round(total_cost, 1),
        "events_by_severity": dict(by_severity),
        "events_by_type": type_summary,
        "highest_cost_event": max(
            disruptions,
            key=lambda e: float(e.get("cost_impact_usd_million", 0))
        ).get("event_id", "N/A"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: OPTIMISATION MODEL SKELETON
# ─────────────────────────────────────────────────────────────────────────────

def build_optimisation_skeleton(scored_components: list, inventory: list) -> dict:
    """
    Build a skeleton optimisation model for supply chain resilience.

    MATHEMATICAL FORMULATION:
    ─────────────────────────
    Decision Variables:
        x[i, s] ∈ [0, 1]: fraction of component i's volume sourced from supplier s
        I[i] ∈ Z+: weeks of safety stock for component i

    Objective (minimise total supply chain cost):
        min Z = Σ_i Σ_s (unit_cost[i,s] × annual_vol[i] × x[i,s])
              + Σ_i (unit_cost[i] × weekly_usage[i] × I[i] × holding_cost_rate)

    Constraints:
        1. Volume coverage:  Σ_s x[i,s] = 1  for all i
        2. Min safety stock: I[i] >= 8       for critical_component[i] = 1
        3. Max lead time:    lead_time[i,s] × x[i,s] ≤ 28 days  for critical
        4. Dual source:      x[i,s] ≤ 0.7   for single_source[i] = 1  (force alt supplier)
        5. Service level:    Prob(stockout) ≤ 1 - 0.95 = 0.05

    TODO: Implement using scipy.optimize.linprog or PuLP for exact solution.
    This skeleton computes a greedy heuristic: prioritise dual-sourcing
    the top-N riskiest critical/single-source components.
    """
    # Build inventory lookup
    inv_lookup = {row["component_id"]: row for row in inventory}

    # Identify components that need dual-sourcing (single-source + critical)
    priority_for_dual_source = [
        c for c in scored_components
        if c["is_single_source"] == 1 and c["critical_component"] == 1
    ][:20]  # Focus on top 20 by risk score

    # Identify components below safety stock threshold
    below_safety_stock = []
    for c in scored_components:
        cid = c["component_id"]
        inv = inv_lookup.get(cid, {})
        try:
            wos = float(inv.get("weeks_of_supply", 3))
            if wos < COMPANY["target_inventory_weeks"] and c["critical_component"] == 1:
                below_safety_stock.append({
                    "component_id": cid,
                    "current_weeks_of_supply": wos,
                    "target_weeks": COMPANY["target_inventory_weeks"],
                    "gap_weeks": round(COMPANY["target_inventory_weeks"] - wos, 1),
                    "annual_spend_usd_m": c["annual_spend_usd_m"],
                    "incremental_buffer_cost_usd_m": round(
                        c["unit_cost_usd"] * c["annual_volume"] / 52
                        * (COMPANY["target_inventory_weeks"] - wos) / 1_000_000, 3
                    ),
                })
        except (ValueError, TypeError):
            continue

    below_safety_stock.sort(key=lambda x: x.get("incremental_buffer_cost_usd_m", 0), reverse=True)

    # Total incremental cost of building safety stock to 8 weeks
    total_buffer_cost = sum(
        row.get("incremental_buffer_cost_usd_m", 0) for row in below_safety_stock
    )

    return {
        "formulation": {
            "objective": "Minimise total supply chain cost (procurement + inventory carrying)",
            "decision_variables": ["x[component, supplier] = sourcing fraction", "I[component] = safety stock weeks"],
            "constraints": [
                "Volume coverage: sum(x[i,s]) = 1 for each component",
                "Critical safety stock: I[i] >= 8 weeks for critical components",
                "Lead time: weighted avg lead time <= 28 days for critical components",
                "Dual source cap: x[i,s] <= 0.7 to force alternative supplier",
                "Service level: stockout probability <= 5%",
            ],
            "note": "TODO: Implement using PuLP (pip install pulp) or scipy.optimize.linprog",
        },
        "greedy_dual_source_recommendations": [
            {
                "component_id": c["component_id"],
                "component_type": c["component_type"],
                "current_supplier": c["supplier_id"],
                "supplier_country": c["supplier_country"],
                "risk_score": c["risk_score"],
                "annual_spend_usd_m": c["annual_spend_usd_m"],
                "action": "Qualify alternative supplier — reduce to 60/40 split",
                "estimated_cost_premium_pct": "TODO: Estimate 5-15% premium for dual sourcing",
            }
            for c in priority_for_dual_source[:10]
        ],
        "safety_stock_gaps": below_safety_stock[:15],
        "total_buffer_investment_usd_m": round(total_buffer_cost, 2),
        "note": "TODO: Replace greedy heuristic with MILP using PuLP or OR-Tools",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: SCENARIO ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def scenario_analysis(exposure: dict) -> dict:
    """
    Compute financial impact under three disruption scenarios.

    TODO: Calibrate probabilities and impact multipliers based on your
          analysis of the disruption_events.csv historical data.
    """
    revenue_per_week = REVENUE_LOSS_PER_WEEK_USD_M

    scenarios = {
        "base": {
            "description": "Current disruptions continue (semiconductor shortage + Red Sea)",
            "probability_pct": 50.0,                 # TODO: adjust
            "affected_components_count": 400,         # TODO: derive from data
            "production_shortfall_pct": 5.0,          # TODO: adjust
            "disruption_duration_weeks": 26,
            "note": "TODO: Derive from supply_chain.csv — count components from affected regions",
        },
        "moderate": {
            "description": "Base + 25% tariff on Country X imports",
            "probability_pct": 30.0,                 # TODO: adjust
            "affected_components_count": 600,
            "production_shortfall_pct": 12.0,
            "disruption_duration_weeks": 52,
            "note": "TODO: Identify Country X components from supply_chain.csv",
        },
        "severe": {
            "description": "Base + tariff + Taiwan earthquake + factory fire",
            "probability_pct": 20.0,                 # TODO: adjust
            "affected_components_count": 900,
            "production_shortfall_pct": 30.0,
            "disruption_duration_weeks": 12,
            "note": "TODO: Cross-reference Taiwan-sourced critical components",
        },
    }

    results = {}
    for name, sc in scenarios.items():
        prod_loss = sc["production_shortfall_pct"] / 100
        duration = sc["disruption_duration_weeks"]
        revenue_at_risk = round(revenue_per_week * prod_loss * duration, 1)
        cost_impact = round(revenue_at_risk * 0.6, 1)  # ~60% drops to margin/cost

        results[name] = {
            **sc,
            "revenue_at_risk_usd_m": revenue_at_risk,
            "total_cost_impact_usd_m": cost_impact,
        }

    # Expected value (probability-weighted)
    ev = round(sum(
        r["probability_pct"] / 100 * r["total_cost_impact_usd_m"]
        for r in results.values()
    ), 1)

    return {
        "scenarios": results,
        "expected_value_cost_usd_m": ev,
        "revenue_loss_per_week_assumption_usd_m": revenue_per_week,
        "note": "TODO: Calibrate all scenario parameters against disruption_events.csv historical data",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P3 SupplyZen — Supply Chain Risk Analysis Scaffold"
    )
    parser.add_argument(
        "--data-dir",
        default=r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P3",
        help="Directory containing supply chain CSV files",
    )
    parser.add_argument("--output", default="analysis.json",
                        help="Output path for analysis JSON (default: analysis.json)")

    args = parser.parse_args()

    print(f"[MBA-P3] SupplyZen Analysis — ElectraTech")
    print(f"  Data directory: {args.data_dir}")

    # Load data
    print("\n[1/5] Loading datasets...")
    supply_chain = load_csv(os.path.join(args.data_dir, "supply_chain.csv"))
    risk_rows = load_csv(os.path.join(args.data_dir, "supplier_risk_matrix.csv"))
    disruptions = load_csv(os.path.join(args.data_dir, "disruption_events.csv"))
    inventory = load_csv(os.path.join(args.data_dir, "inventory_levels.csv"))
    print(f"  Components: {len(supply_chain)}  Suppliers: {len(risk_rows)}  "
          f"Disruptions: {len(disruptions)}  Inventory: {len(inventory)}")

    risk_lookup = build_risk_matrix_lookup(risk_rows)

    # Risk scoring
    print("[2/5] Scoring component risks...")
    scored = compute_component_risk_scores(supply_chain, risk_lookup)
    print(f"  Scored {len(scored)} components. Top risk score: {scored[0]['risk_score'] if scored else 'N/A'}")

    # Exposure quantification
    print("[3/5] Quantifying risk exposure...")
    exposure = quantify_exposure(scored)
    print(f"  Single-source+critical components: {exposure['single_source_and_critical_count']}")
    print(f"  Largest country concentration: "
          + (list(exposure['country_concentration_pct_spend'].items())[0][0]
             + f" {list(exposure['country_concentration_pct_spend'].items())[0][1]}%"
             if exposure['country_concentration_pct_spend'] else 'N/A'))

    # Disruption analysis
    print("[4/5] Analysing disruption history...")
    disruption_summary = analyse_disruptions(disruptions)
    print(f"  Total historical cost: ${disruption_summary.get('total_historical_cost_usd_m', 0)}M")

    # Optimisation skeleton
    print("[5/5] Building optimisation skeleton...")
    opt_model = build_optimisation_skeleton(scored, inventory)
    print(f"  Dual-source candidates: {len(opt_model['greedy_dual_source_recommendations'])}")
    print(f"  Safety stock gap components: {len(opt_model['safety_stock_gaps'])}")
    print(f"  Total buffer investment needed: ${opt_model['total_buffer_investment_usd_m']}M")

    # Scenario analysis
    scenarios = scenario_analysis(exposure)
    print(f"  Expected disruption cost (prob-weighted): ${scenarios['expected_value_cost_usd_m']}M")

    analysis = {
        "problem": "MBA-P3: SupplyZen",
        "company": COMPANY["name"],
        "exposure_summary": exposure,
        "disruption_history": disruption_summary,
        "optimisation_model": opt_model,
        "scenario_analysis": scenarios,
        "summary": {
            "single_source_critical_count": exposure["single_source_and_critical_count"],
            "top_risk_component": scored[0]["component_id"] if scored else "N/A",
            "top_risk_score": scored[0]["risk_score"] if scored else None,
            "expected_disruption_cost_usd_m": scenarios["expected_value_cost_usd_m"],
            "buffer_investment_needed_usd_m": opt_model["total_buffer_investment_usd_m"],
            "next_steps": [
                "TODO: Implement MILP using PuLP for exact dual-source optimisation",
                "TODO: Calibrate scenario probabilities from disruption_events.csv",
                "TODO: Build supplier risk heatmap (country × risk tier matrix)",
                "TODO: Score all 6 mitigation strategies with ROI calculations",
                "TODO: Build 18-month implementation roadmap",
            ],
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
