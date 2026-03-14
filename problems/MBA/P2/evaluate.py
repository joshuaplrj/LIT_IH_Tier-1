"""
MBA-P2: PricingGenius — Submission Evaluator
=============================================
Usage:
    python evaluate.py --submission <path_to_submission.json>

REQUIRED SUBMISSION JSON SCHEMA
--------------------------------
{
  "demand_model": {
    "model_type": "str",                         // e.g. "log-log OLS", "XGBoost"
    "features_used": ["str", ...],               // min 5 features
    "elasticity_estimates": [                    // min 2 segments
      {
        "segment": "str",                        // e.g. "peak", "offpeak"
        "elasticity": float,                     // expected range: -2.0 to -0.1
        "n_observations": int,
        "r_squared": float                       // 0.0 – 1.0
      }
    ],
    "accuracy_metrics": {
      "mae": float,                              // Mean Absolute Error on holdout
      "rmse": float,                             // Root Mean Squared Error
      "r_squared": float
    }
  },
  "pricing_strategy": {
    "surge_formula": "str",                      // explicit formula or description
    "surge_multiplier_cap": float,               // max surge allowed
    "competitor_price_cap_pct": float,           // e.g. 115.0 means max 115% of competitor
    "segment_discounts": [                       // at least 1 discount rule
      {"segment": "str", "discount_pct": float, "trigger": "str"}
    ],
    "driver_incentive_policy": "str"
  },
  "simulation_results": {
    "holdout_period": "str",
    "baseline_revenue_usd": float,
    "new_strategy_revenue_usd": float,
    "revenue_uplift_pct": float,                 // must be > 0 to score on this metric
    "cancellation_rate_baseline_pct": float,
    "cancellation_rate_new_pct": float,
    "avg_utilisation_change_pct": float
  },
  "ab_testing_plan": {
    "experiment_design": "str",                  // e.g. "switchback" or "geo-split"
    "randomisation_unit": "str",
    "minimum_detectable_effect_pct": float,
    "required_sample_size_per_arm": int,
    "test_duration_days": int,
    "primary_metric": "str",
    "guardrail_metrics": ["str", ...],           // min 2 guardrail metrics
    "statistical_test": "str"
  },
  "ethical_considerations": {
    "emergency_surge_policy": "str",
    "fairness_policy": "str",
    "clv_protection_policy": "str"
  }
}
"""

import argparse
import json
import sys
from pathlib import Path


SCORE_WEIGHTS = {
    "section_completeness":            40,
    "quantitative_validity":           40,
    "strategic_coherence_indicators":  20,
}

REQUIRED_SECTIONS = [
    "demand_model",
    "pricing_strategy",
    "simulation_results",
    "ab_testing_plan",
    "ethical_considerations",
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
        if not isinstance(sec, dict) or len(sec) == 0:
            missing_sections.append(f"{section} (empty)")
            details[section] = "EMPTY"
            continue

        if section == "demand_model":
            feats = sec.get("features_used", [])
            elas = sec.get("elasticity_estimates", [])
            if len(feats) < 5:
                details[section] = f"PARTIAL (only {len(feats)} features, need 5+)"
                continue
            if len(elas) < 2:
                details[section] = f"PARTIAL (only {len(elas)} elasticity segments, need 2+)"
                continue

        if section == "pricing_strategy":
            if not sec.get("surge_formula"):
                details[section] = "PARTIAL (missing surge_formula)"
                continue
            discounts = sec.get("segment_discounts", [])
            if len(discounts) < 1:
                details[section] = "PARTIAL (missing segment_discounts)"
                continue

        if section == "simulation_results":
            required_fields = ["revenue_uplift_pct", "baseline_revenue_usd", "new_strategy_revenue_usd"]
            missing_fields = [f for f in required_fields if f not in sec]
            if missing_fields:
                details[section] = f"PARTIAL (missing: {missing_fields})"
                continue

        if section == "ab_testing_plan":
            guardrails = sec.get("guardrail_metrics", [])
            if len(guardrails) < 2:
                details[section] = f"PARTIAL (only {len(guardrails)} guardrail metrics, need 2+)"
                continue

        if section == "ethical_considerations":
            required_policies = ["emergency_surge_policy", "fairness_policy", "clv_protection_policy"]
            missing_pol = [p for p in required_policies if not sec.get(p)]
            if missing_pol:
                details[section] = f"PARTIAL (missing policies: {missing_pol})"
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

    dm = submission.get("demand_model", {})
    ps = submission.get("pricing_strategy", {})
    sr = submission.get("simulation_results", {})
    ab = submission.get("ab_testing_plan", {})

    # 2a. Elasticity values are in realistic range (-2.0 to -0.1)
    elas_list = dm.get("elasticity_estimates", [])
    valid_elas = [
        e for e in elas_list
        if isinstance(e.get("elasticity"), (int, float)) and -2.0 <= e["elasticity"] <= -0.1
    ]
    if len(valid_elas) >= 2:
        checks.append((f"{len(valid_elas)} elasticity estimates in valid range [-2.0, -0.1]", True))
    else:
        checks.append((f"Only {len(valid_elas)} valid elasticity estimates (need 2+ in [-2.0, -0.1])", False))
        errors.append("Price elasticity must be negative (demand falls as price rises); expected range -2.0 to -0.1")

    # 2b. R-squared of demand model is reported and reasonable (>0.1)
    acc = dm.get("accuracy_metrics", {})
    r2 = acc.get("r_squared", None)
    if isinstance(r2, (int, float)) and r2 > 0.1:
        checks.append((f"Model R² = {r2:.3f} (acceptable)", True))
    else:
        checks.append((f"Model R² = {r2} — not reported or below 0.10", False))
        errors.append("demand_model.accuracy_metrics.r_squared must be > 0.1")

    # 2c. Surge cap does not exceed 3.0 (platform safety constraint)
    surge_cap = ps.get("surge_multiplier_cap", None)
    if isinstance(surge_cap, (int, float)) and 1.5 <= surge_cap <= 3.0:
        checks.append((f"Surge cap {surge_cap}x in acceptable range [1.5x, 3.0x]", True))
    else:
        checks.append((f"Surge cap {surge_cap} outside [1.5, 3.0] or not provided", False))
        errors.append("pricing_strategy.surge_multiplier_cap must be between 1.5 and 3.0")

    # 2d. Competitor price cap <= 120% (problem constraint: max 15% premium)
    comp_cap = ps.get("competitor_price_cap_pct", None)
    if isinstance(comp_cap, (int, float)) and comp_cap <= 120.0:
        checks.append((f"Competitor price cap {comp_cap}% within 120% constraint", True))
    else:
        checks.append((f"Competitor price cap {comp_cap}% exceeds 115% constraint", False))
        errors.append("pricing_strategy.competitor_price_cap_pct must be <= 115 (problem states max 15% premium)")

    # 2e. Revenue uplift is positive
    uplift = sr.get("revenue_uplift_pct", None)
    if isinstance(uplift, (int, float)) and uplift > 0:
        checks.append((f"Revenue uplift {uplift}% is positive", True))
    else:
        checks.append((f"Revenue uplift {uplift}% is not positive or missing", False))
        errors.append("simulation_results.revenue_uplift_pct must be > 0")

    # 2f. Revenue uplift is plausible (not > 50% — that would suggest data snooping)
    if isinstance(uplift, (int, float)) and 0 < uplift <= 50:
        checks.append((f"Revenue uplift {uplift}% in plausible range (0–50%)", True))
    elif isinstance(uplift, (int, float)) and uplift > 50:
        checks.append((f"Revenue uplift {uplift}% exceeds 50% — may be over-optimistic", False))
        errors.append("Revenue uplift > 50% is implausible for a pricing-only change; review simulation assumptions")

    # 2g. A/B test has required sample size documented
    sample_size = ab.get("required_sample_size_per_arm", None)
    if isinstance(sample_size, int) and sample_size >= 1000:
        checks.append((f"A/B test sample size {sample_size:,} rides documented", True))
    else:
        checks.append((f"A/B test sample size {sample_size} insufficient or missing (need 1000+)", False))
        errors.append("ab_testing_plan.required_sample_size_per_arm must be an int >= 1000")

    # 2h. Cancellation rates are reported
    can_base = sr.get("cancellation_rate_baseline_pct", None)
    can_new = sr.get("cancellation_rate_new_pct", None)
    if isinstance(can_base, (int, float)) and isinstance(can_new, (int, float)):
        checks.append(("Cancellation rates reported for both baseline and new strategy", True))
    else:
        checks.append(("Cancellation rates not fully reported", False))
        errors.append("simulation_results must include cancellation_rate_baseline_pct and cancellation_rate_new_pct")

    pts_per_check = max_score / len(checks)
    pts = round(sum(pts_per_check for _, passed in checks if passed), 1)
    return pts, max_score, errors, checks


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: STRATEGIC COHERENCE INDICATORS  (max 20 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_strategic_coherence(submission: dict) -> tuple:
    max_score = 20
    notes = []
    pts = 0.0

    # 3a. Surge formula is explicit and includes elasticity (+5)
    surge_formula = submission.get("pricing_strategy", {}).get("surge_formula", "")
    if isinstance(surge_formula, str) and len(surge_formula) > 20:
        if any(kw in surge_formula.lower() for kw in ["elasticity", "demand", "supply", "multiplier", "ratio"]):
            pts += 5
            notes.append("[+5] Surge formula references demand/supply mechanics")
        else:
            pts += 2
            notes.append("[+2] Surge formula provided but lacks demand/supply language")
    else:
        notes.append("[+0] Surge formula missing or too brief")

    # 3b. CLV segmentation is present (+5)
    clv_policy = submission.get("ethical_considerations", {}).get("clv_protection_policy", "")
    discounts = submission.get("pricing_strategy", {}).get("segment_discounts", [])
    has_clv = any("clv" in str(d).lower() or "loyal" in str(d).lower() for d in discounts)
    has_clv = has_clv or ("clv" in str(clv_policy).lower() or "loyal" in str(clv_policy).lower())
    if has_clv:
        pts += 5
        notes.append("[+5] CLV/loyalty-based pricing segmentation present")
    else:
        notes.append("[+0] No CLV segmentation — loyal customers unprotected from surge")

    # 3c. Driver incentive policy is non-trivial (+5)
    driver_policy = submission.get("pricing_strategy", {}).get("driver_incentive_policy", "")
    if isinstance(driver_policy, str) and len(driver_policy) > 30:
        if any(kw in driver_policy.lower() for kw in ["supply", "incentive", "bonus", "threshold", "trigger"]):
            pts += 5
            notes.append("[+5] Driver incentive policy has supply-side logic")
        else:
            pts += 2
            notes.append("[+2] Driver incentive policy present but lacks trigger conditions")
    else:
        notes.append("[+0] Driver incentive policy missing or trivial")

    # 3d. Ethical section addresses all 3 required policies (+5)
    eth = submission.get("ethical_considerations", {})
    policies = ["emergency_surge_policy", "fairness_policy", "clv_protection_policy"]
    present_policies = sum(1 for p in policies if eth.get(p) and len(str(eth[p])) > 20)
    if present_policies == 3:
        pts += 5
        notes.append("[+5] All 3 ethical policies substantively addressed")
    else:
        notes.append(f"[+0] Only {present_policies}/3 ethical policies are substantive")

    return round(pts, 1), max_score, notes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P2 PricingGenius — Submission Evaluator"
    )
    parser.add_argument("--submission", required=True,
                        help="Path to submission JSON file")
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
            "section_completeness": {
                "score": sc_score,
                "max": sc_max,
                "details": sc_details,
            },
            "quantitative_validity": {
                "score": qv_score,
                "max": qv_max,
                "checks": [{"check": c, "passed": p} for c, p in qv_checks],
            },
            "strategic_coherence_indicators": {
                "score": coh_score,
                "max": coh_max,
                "notes": coh_notes,
            },
        },
        "errors": qv_errors,
        "missing_sections": missing,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
