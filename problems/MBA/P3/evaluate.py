"""
MBA-P3: SupplyZen — Submission Evaluator
=========================================
Usage:
    python evaluate.py --submission <path_to_submission.json>

REQUIRED SUBMISSION JSON SCHEMA
--------------------------------
{
  "risk_assessment": {
    "single_source_critical_count": int,           // components that are both single-source AND critical
    "country_concentration_pct": {                 // top countries by % of procurement spend
      "<country>": float
    },
    "top_10_risk_exposures": [                     // min 5 entries
      {
        "component_id": "str",
        "risk_score": float,                       // 0–100
        "annual_spend_usd_m": float,
        "disruption_cost_estimate_usd_m": float,
        "is_single_source": int,                   // 0 or 1
        "critical_component": int                  // 0 or 1
      }
    ],
    "risk_score_formula": "str",                   // explicit formula used to compute risk scores
    "total_spend_at_risk_usd_m": float
  },
  "optimization_model": {
    "objective_function": "str",                   // explicit math statement
    "decision_variables": ["str", ...],            // min 2 variables
    "constraints": ["str", ...],                   // min 4 constraints
    "optimal_dual_source_candidates": [
      {
        "component_id": "str",
        "current_supplier": "str",
        "recommended_split": "str",                // e.g. "60/40 primary/alternate"
        "estimated_cost_premium_pct": float
      }
    ],
    "total_optimisation_cost_usd_m": float,        // incremental cost of optimised solution
    "service_level_achieved_pct": float            // expected service level post-optimisation
  },
  "scenario_analysis": {
    "base_case": {
      "probability_pct": float,                    // sum of all 3 scenarios should be ~100
      "description": "str",
      "revenue_at_risk_usd_m": float,
      "total_cost_impact_usd_m": float
    },
    "moderate_disruption": {
      "probability_pct": float,
      "description": "str",
      "revenue_at_risk_usd_m": float,
      "total_cost_impact_usd_m": float
    },
    "severe_disruption": {
      "probability_pct": float,
      "description": "str",
      "revenue_at_risk_usd_m": float,
      "total_cost_impact_usd_m": float
    },
    "expected_value_cost_usd_m": float             // probability-weighted total cost
  },
  "mitigation_strategies": [                       // min 4 strategies evaluated
    {
      "strategy_name": "str",
      "annual_cost_usd_m": float,
      "implementation_months": int,
      "expected_risk_reduction_pct": float,        // 0–100
      "roi_3yr": float,                            // 3-year ROI as decimal (e.g. 1.5 = 150%)
      "recommended_priority": int                  // 1=highest priority
    }
  ],
  "implementation_plan": {
    "phases": [                                    // min 3 phases
      {
        "phase_name": "str",
        "months": "str",                           // e.g. "1-3"
        "actions": ["str", ...],                   // min 2 actions
        "kpis": ["str", ...],                      // min 1 KPI
        "investment_usd_m": float
      }
    ],
    "total_investment_usd_m": float,
    "payback_period_months": int
  }
}
"""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "risk_assessment",
    "optimization_model",
    "scenario_analysis",
    "mitigation_strategies",
    "implementation_plan",
]


def load_submission(path: str):
    p = Path(path)
    if not p.exists():
        return None, f"File not found: {path}"
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1: SECTION COMPLETENESS  (max 40 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_section_completeness(submission: dict) -> tuple:
    max_score = 40
    missing_sections = []
    details = {}
    pts_per_section = max_score / len(REQUIRED_SECTIONS)

    for section in REQUIRED_SECTIONS:
        if section not in submission:
            missing_sections.append(section)
            details[section] = "MISSING"
            continue

        sec = submission[section]

        if section == "risk_assessment":
            if not sec.get("risk_score_formula"):
                details[section] = "PARTIAL (missing risk_score_formula)"
                continue
            exposures = sec.get("top_10_risk_exposures", [])
            if len(exposures) < 5:
                details[section] = f"PARTIAL (only {len(exposures)} risk exposures, need 5+)"
                continue

        elif section == "optimization_model":
            constraints = sec.get("constraints", [])
            if len(constraints) < 4:
                details[section] = f"PARTIAL (only {len(constraints)} constraints, need 4+)"
                continue
            dvars = sec.get("decision_variables", [])
            if len(dvars) < 2:
                details[section] = f"PARTIAL (only {len(dvars)} decision variables, need 2+)"
                continue

        elif section == "scenario_analysis":
            required_scenarios = ["base_case", "moderate_disruption", "severe_disruption"]
            missing_sc = [s for s in required_scenarios if s not in sec]
            if missing_sc:
                details[section] = f"PARTIAL (missing scenarios: {missing_sc})"
                continue

        elif section == "mitigation_strategies":
            if not isinstance(sec, list) or len(sec) < 4:
                count = len(sec) if isinstance(sec, list) else 0
                details[section] = f"PARTIAL (only {count} strategies, need 4+)"
                continue

        elif section == "implementation_plan":
            phases = sec.get("phases", [])
            if len(phases) < 3:
                details[section] = f"PARTIAL (only {len(phases)} phases, need 3+)"
                continue

        details[section] = "OK"

    ok_count = sum(1 for v in details.values() if v == "OK")
    score = round(ok_count * pts_per_section, 1)
    return score, max_score, details, missing_sections


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2: QUANTITATIVE VALIDITY  (max 40 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_quantitative_validity(submission: dict) -> tuple:
    max_score = 40
    errors = []
    checks = []

    ra = submission.get("risk_assessment", {})
    om = submission.get("optimization_model", {})
    sa = submission.get("scenario_analysis", {})
    ms = submission.get("mitigation_strategies", []) if isinstance(
        submission.get("mitigation_strategies"), list) else []

    # 2a. Risk scores in valid range (0–100)
    exposures = ra.get("top_10_risk_exposures", [])
    valid_scores = [
        e for e in exposures
        if isinstance(e.get("risk_score"), (int, float)) and 0 <= e["risk_score"] <= 100
    ]
    if len(valid_scores) >= 5:
        checks.append((f"{len(valid_scores)} risk exposures with valid scores [0–100]", True))
    else:
        checks.append((f"Only {len(valid_scores)} valid risk scores (need 5+ in [0, 100])", False))
        errors.append("risk_assessment.top_10_risk_exposures entries need risk_score in [0, 100]")

    # 2b. Single-source critical count is a positive integer
    ss_count = ra.get("single_source_critical_count", None)
    if isinstance(ss_count, int) and ss_count > 0:
        checks.append((f"Single-source critical count: {ss_count}", True))
    else:
        checks.append(("single_source_critical_count not provided or zero", False))
        errors.append("risk_assessment.single_source_critical_count must be a positive integer")

    # 2c. Service level achieved >= 90% (conservative floor)
    svc_level = om.get("service_level_achieved_pct", None)
    if isinstance(svc_level, (int, float)) and svc_level >= 90:
        checks.append((f"Service level achieved: {svc_level}%", True))
    else:
        checks.append((f"Service level {svc_level}% below 90% or not reported", False))
        errors.append("optimization_model.service_level_achieved_pct must be >= 90%")

    # 2d. Scenario probabilities sum to ~100%
    sc_probs = sum(
        float(sa.get(s, {}).get("probability_pct", 0))
        for s in ["base_case", "moderate_disruption", "severe_disruption"]
    )
    if 90 <= sc_probs <= 110:
        checks.append((f"Scenario probabilities sum to {sc_probs:.1f}% (~100%)", True))
    else:
        checks.append((f"Scenario probabilities sum to {sc_probs:.1f}% (expected ~100%)", False))
        errors.append("Scenario probabilities should sum to approximately 100%")

    # 2e. Expected value is computed and positive
    ev = sa.get("expected_value_cost_usd_m", None)
    if isinstance(ev, (int, float)) and ev > 0:
        checks.append((f"Expected value disruption cost: ${ev}M", True))
    else:
        checks.append(("Expected value cost not computed or zero", False))
        errors.append("scenario_analysis.expected_value_cost_usd_m must be positive — use probability × impact")

    # 2f. Mitigation strategies have ROI values
    strategies_with_roi = [
        s for s in ms
        if isinstance(s.get("roi_3yr"), (int, float)) and s["roi_3yr"] > 0
    ]
    if len(strategies_with_roi) >= 3:
        checks.append((f"{len(strategies_with_roi)} strategies with positive ROI computed", True))
    else:
        checks.append((f"Only {len(strategies_with_roi)} strategies have ROI > 0 (need 3+)", False))
        errors.append("mitigation_strategies entries need roi_3yr > 0")

    # 2g. Risk reduction percentages are in [0, 100]
    valid_risk_red = [
        s for s in ms
        if isinstance(s.get("expected_risk_reduction_pct"), (int, float))
        and 0 < s["expected_risk_reduction_pct"] <= 100
    ]
    if len(valid_risk_red) >= 3:
        checks.append((f"{len(valid_risk_red)} strategies with valid risk reduction %", True))
    else:
        checks.append((f"Only {len(valid_risk_red)} valid risk reduction values (need 3+)", False))
        errors.append("mitigation_strategies.expected_risk_reduction_pct must be in (0, 100]")

    # 2h. Implementation plan total investment is reported
    impl = submission.get("implementation_plan", {})
    total_inv = impl.get("total_investment_usd_m", None)
    if isinstance(total_inv, (int, float)) and total_inv > 0:
        checks.append((f"Implementation total investment: ${total_inv}M", True))
    else:
        checks.append(("Implementation plan total investment not reported", False))
        errors.append("implementation_plan.total_investment_usd_m must be positive")

    pts_per_check = max_score / len(checks)
    pts = round(sum(pts_per_check for _, passed in checks if passed), 1)
    return pts, max_score, errors, checks


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: STRATEGIC COHERENCE  (max 20 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_strategic_coherence(submission: dict) -> tuple:
    max_score = 20
    notes = []
    pts = 0.0

    # 3a. Optimisation model references semiconductor shortage and tariff risk (+5)
    om_text = json.dumps(submission.get("optimization_model", {})).lower()
    if any(kw in om_text for kw in ["semiconductor", "tariff", "single_source", "dual", "resilience"]):
        pts += 5
        notes.append("[+5] Optimisation model references key disruption drivers")
    else:
        notes.append("[+0] Optimisation model lacks specific disruption context")

    # 3b. Country concentration highlights China/Taiwan risk (+5)
    conc = submission.get("risk_assessment", {}).get("country_concentration_pct", {})
    high_risk_countries = ["China", "Taiwan", "South Korea"]
    if any(c in conc for c in high_risk_countries):
        top_country_pct = max((conc.get(c, 0) for c in high_risk_countries), default=0)
        if top_country_pct > 20:
            pts += 5
            notes.append(f"[+5] Country concentration correctly shows Asia-Pacific exposure ({top_country_pct:.1f}%)")
        else:
            pts += 2
            notes.append(f"[+2] High-risk countries mentioned but concentration appears low")
    else:
        notes.append("[+0] Risk assessment doesn't show Asia-Pacific concentration")

    # 3c. Scenario analysis has plausible cost impacts (+5)
    sa = submission.get("scenario_analysis", {})
    severe = sa.get("severe_disruption", {})
    sev_cost = severe.get("total_cost_impact_usd_m", 0)
    # Severe disruption on $10B company should be at least $100M
    if isinstance(sev_cost, (int, float)) and sev_cost >= 100:
        pts += 5
        notes.append(f"[+5] Severe scenario cost impact ${sev_cost}M is material (>=$100M)")
    else:
        notes.append(f"[+0] Severe scenario cost ${sev_cost}M appears too low for a $10B company")

    # 3d. Mitigation strategies are prioritised with numeric rank (+5)
    ms = submission.get("mitigation_strategies", [])
    if isinstance(ms, list):
        ranked = [s for s in ms if isinstance(s.get("recommended_priority"), int)]
        if len(ranked) >= 3:
            pts += 5
            notes.append(f"[+5] {len(ranked)} mitigation strategies have numeric priority ranking")
        else:
            notes.append(f"[+0] Only {len(ranked)} strategies have priority ranking")
    else:
        notes.append("[+0] Mitigation strategies not a list")

    return round(pts, 1), max_score, notes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P3 SupplyZen — Submission Evaluator"
    )
    parser.add_argument("--submission", required=True, help="Path to submission JSON file")
    args = parser.parse_args()

    submission, load_error = load_submission(args.submission)

    if load_error:
        result = {
            "total": 0,
            "breakdown": {
                "section_completeness":           {"score": 0, "max": 40},
                "quantitative_validity":          {"score": 0, "max": 40},
                "strategic_coherence_indicators": {"score": 0, "max": 20},
            },
            "errors": [load_error],
            "missing_sections": REQUIRED_SECTIONS,
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    sc_score, sc_max, sc_details, missing = check_section_completeness(submission)
    qv_score, qv_max, qv_errors, qv_checks = check_quantitative_validity(submission)
    coh_score, coh_max, coh_notes = check_strategic_coherence(submission)

    total = round(sc_score + qv_score + coh_score, 1)

    result = {
        "total": total,
        "breakdown": {
            "section_completeness": {"score": sc_score, "max": sc_max, "details": sc_details},
            "quantitative_validity": {
                "score": qv_score,
                "max": qv_max,
                "checks": [{"check": c, "passed": p} for c, p in qv_checks],
            },
            "strategic_coherence_indicators": {"score": coh_score, "max": coh_max, "notes": coh_notes},
        },
        "errors": qv_errors,
        "missing_sections": missing,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
