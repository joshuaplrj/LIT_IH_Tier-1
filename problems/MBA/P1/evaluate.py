"""
MBA-P1: MarketPivot — Submission Evaluator
===========================================
Usage:
    python evaluate.py --submission <path_to_submission.json>

Exit codes:
    0  — evaluation complete (result printed to stdout as JSON)
    1  — usage error

REQUIRED SUBMISSION JSON SCHEMA
--------------------------------
{
  "strategic_analysis": {
    "competitive_landscape": {
      "description": "str",
      "key_threats": ["str", ...],          // min 3 threats
      "competitive_forces": {               // Porter's 5 Forces (or equivalent)
        "threat_of_new_entrants": "str",
        "supplier_power": "str",
        "buyer_power": "str",
        "threat_of_substitutes": "str",
        "competitive_rivalry": "str"
      }
    },
    "strategic_options_scorecard": {       // at least 3 options evaluated
      "<option_name>": {
        "weighted_score": float,           // 0–10
        "rationale": "str"
      }
    }
  },
  "recommended_strategy": {
    "option": "str",                       // e.g. "Partner-first with selective Build"
    "rationale": "str",
    "key_tradeoffs": ["str", ...],         // min 2 trade-offs acknowledged
    "three_year_milestones": [             // min 3 milestones
      {"year": int, "milestone": "str", "success_metric": "str"}
    ]
  },
  "gtm_transformation": {
    "license_to_saas_plan": "str",
    "customer_retention_plan": "str",
    "pricing_strategy": "str",
    "new_customer_acquisition": "str"
  },
  "financial_plan": {
    "year_1": {"revenue_usd_m": float, "ebitda_usd_m": float, "ebitda_margin_pct": float},
    "year_2": {"revenue_usd_m": float, "ebitda_usd_m": float, "ebitda_margin_pct": float},
    "year_3": {"revenue_usd_m": float, "ebitda_usd_m": float, "ebitda_margin_pct": float},
    "capital_allocation_usd_m": {
      "rd": float,
      "ma_or_partnerships": float,
      "talent_and_org": float,
      "debt_management": float
    },
    "debt_management_plan": "str",
    "break_even_year": int                 // year 1, 2, or 3 for AI product break-even
  },
  "org_transformation": {
    "new_roles_required": ["str", ...],    // min 3 new role types
    "talent_plan": "str",
    "culture_change_plan": "str"
  },
  "risk_analysis": {
    "risk_register": [                     // min 5 risks
      {
        "risk": "str",
        "probability": "Low|Medium|High",
        "impact": "Low|Medium|High",
        "mitigation": "str"
      }
    ],
    "contingency_plan_b": "str",
    "contingency_plan_c": "str"
  }
}
"""

import argparse
import json
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# SCORING WEIGHTS (must sum to 100)
# ─────────────────────────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "section_completeness":            40,
    "quantitative_validity":           40,
    "strategic_coherence_indicators":  20,
}

REQUIRED_SECTIONS = [
    "strategic_analysis",
    "recommended_strategy",
    "gtm_transformation",
    "financial_plan",
    "org_transformation",
    "risk_analysis",
]


def load_submission(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return None, f"File not found: {path}"
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1: SECTION COMPLETENESS  (max 40 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_section_completeness(submission: dict) -> tuple:
    """
    Returns (score: float, max: int, details: dict, missing: list)
    """
    max_score = 40
    missing_sections = []
    details = {}
    pts_per_section = max_score / len(REQUIRED_SECTIONS)

    for section in REQUIRED_SECTIONS:
        if section not in submission:
            missing_sections.append(section)
            details[section] = "MISSING"
            continue

        sec_data = submission[section]
        if not isinstance(sec_data, dict) or len(sec_data) == 0:
            missing_sections.append(f"{section} (empty)")
            details[section] = "EMPTY"
            continue

        # Spot-check critical sub-fields
        if section == "strategic_analysis":
            if "strategic_options_scorecard" not in sec_data:
                details[section] = "PARTIAL (missing strategic_options_scorecard)"
                continue
            if "competitive_landscape" not in sec_data:
                details[section] = "PARTIAL (missing competitive_landscape)"
                continue

        if section == "recommended_strategy":
            if "option" not in sec_data or not sec_data.get("option"):
                details[section] = "PARTIAL (missing option field)"
                continue
            milestones = sec_data.get("three_year_milestones", [])
            if len(milestones) < 3:
                details[section] = f"PARTIAL (only {len(milestones)} milestones, need 3+)"
                continue

        if section == "financial_plan":
            required_years = ["year_1", "year_2", "year_3"]
            missing_yrs = [y for y in required_years if y not in sec_data]
            if missing_yrs:
                details[section] = f"PARTIAL (missing: {missing_yrs})"
                continue

        if section == "risk_analysis":
            risks = sec_data.get("risk_register", [])
            if len(risks) < 5:
                details[section] = f"PARTIAL (only {len(risks)} risks, need 5+)"
                continue

        details[section] = "OK"

    ok_count = sum(1 for v in details.values() if v == "OK")
    score = round(ok_count * pts_per_section, 1)
    return score, max_score, details, missing_sections


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2: QUANTITATIVE VALIDITY  (max 40 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_quantitative_validity(submission: dict) -> tuple:
    """
    Returns (score: float, max: int, errors: list)
    """
    max_score = 40
    errors = []
    pts = 0.0
    checks = []

    fp = submission.get("financial_plan", {})

    # 2a. Revenue trajectory — Y3 revenue must be between 1000 and 3500 ($M) to be realistic
    try:
        y1_rev = float(fp.get("year_1", {}).get("revenue_usd_m", 0))
        y3_rev = float(fp.get("year_3", {}).get("revenue_usd_m", 0))
        if 1_000 <= y3_rev <= 3_500:
            checks.append(("Y3 revenue in plausible range [1000–3500]M", True))
        else:
            checks.append((f"Y3 revenue {y3_rev}M out of plausible range [1000–3500]M", False))
            errors.append(f"Y3 revenue {y3_rev}M implausible — starting base is $2000M with -5% trend")
    except (TypeError, ValueError):
        checks.append(("Could not parse Y3 revenue", False))
        errors.append("financial_plan.year_3.revenue_usd_m must be a number")

    # 2b. EBITDA margin — Y3 must be between -10% and 35%
    try:
        y3_ebitda_m = float(fp.get("year_3", {}).get("ebitda_margin_pct", -999))
        if -10 <= y3_ebitda_m <= 35:
            checks.append(("Y3 EBITDA margin in plausible range [-10%, 35%]", True))
        else:
            checks.append((f"Y3 EBITDA margin {y3_ebitda_m}% out of range [-10%, 35%]", False))
            errors.append(f"Y3 EBITDA margin {y3_ebitda_m}% is unrealistic")
    except (TypeError, ValueError):
        checks.append(("Could not parse Y3 EBITDA margin", False))
        errors.append("financial_plan.year_3.ebitda_margin_pct must be a number")

    # 2c. Capital allocation must be present and sum to a reasonable amount
    cap_alloc = fp.get("capital_allocation_usd_m", {})
    if cap_alloc and all(isinstance(v, (int, float)) for v in cap_alloc.values()):
        total_alloc = sum(cap_alloc.values())
        if 200 <= total_alloc <= 900:
            checks.append((f"Capital allocation total ${total_alloc}M in range [200–900]M", True))
        else:
            checks.append((f"Capital allocation total ${total_alloc}M outside [200–900]M", False))
            errors.append(f"Capital allocation total ${total_alloc}M implausible given $500M cash + FCF")
    else:
        checks.append(("Capital allocation incomplete or non-numeric", False))
        errors.append("financial_plan.capital_allocation_usd_m must have numeric values")

    # 2d. Strategic options scorecard — at least 3 options with numeric scores
    scorecard = submission.get("strategic_analysis", {}).get("strategic_options_scorecard", {})
    numeric_options = [k for k, v in scorecard.items()
                       if isinstance(v, dict) and isinstance(v.get("weighted_score"), (int, float))]
    if len(numeric_options) >= 3:
        checks.append((f"{len(numeric_options)} options with numeric scores", True))
    else:
        checks.append((f"Only {len(numeric_options)} options scored numerically (need 3+)", False))
        errors.append("strategic_analysis.strategic_options_scorecard needs 3+ options with numeric weighted_score")

    # 2e. Risk register — probability/impact must use valid values
    risk_register = submission.get("risk_analysis", {}).get("risk_register", [])
    valid_levels = {"Low", "Medium", "High"}
    valid_risks = sum(
        1 for r in risk_register
        if r.get("probability") in valid_levels and r.get("impact") in valid_levels
    )
    if valid_risks >= 5:
        checks.append((f"{valid_risks} risks with valid probability/impact labels", True))
    else:
        checks.append((f"Only {valid_risks} risks with valid labels (need 5+)", False))
        errors.append("risk_analysis.risk_register needs 5+ entries with probability/impact = Low|Medium|High")

    # 2f. Three-year milestones are year-tagged
    milestones = submission.get("recommended_strategy", {}).get("three_year_milestones", [])
    year_tagged = sum(1 for m in milestones if isinstance(m.get("year"), int) and m["year"] in [1, 2, 3])
    if year_tagged >= 3:
        checks.append((f"{year_tagged} milestones year-tagged", True))
    else:
        checks.append((f"Only {year_tagged} milestones with valid year tag (need 3+)", False))
        errors.append("recommended_strategy.three_year_milestones need year=1|2|3 on each milestone")

    # 2g. Debt management plan exists
    debt_plan = fp.get("debt_management_plan", "")
    if isinstance(debt_plan, str) and len(debt_plan) > 30:
        checks.append(("Debt management plan provided", True))
    else:
        checks.append(("Debt management plan missing or too brief", False))
        errors.append("financial_plan.debt_management_plan must be a non-empty string explaining $800M debt strategy")

    pts_per_check = max_score / len(checks)
    pts = round(sum(pts_per_check for _, passed in checks if passed), 1)

    return pts, max_score, errors, checks


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: STRATEGIC COHERENCE INDICATORS  (max 20 pts)
# ─────────────────────────────────────────────────────────────────────────────

def check_strategic_coherence(submission: dict) -> tuple:
    """
    Heuristic checks for strategic thinking depth.
    Returns (score: float, max: int, notes: list)
    """
    max_score = 20
    notes = []
    pts = 0.0

    # 3a. Recommendation aligns with a real strategic option (+5)
    rec = submission.get("recommended_strategy", {})
    option = rec.get("option", "")
    tradeoffs = rec.get("key_tradeoffs", [])
    if option and len(option) > 5:
        pts += 5
        notes.append(f"[+5] Recommended option stated: '{option[:60]}'")
    else:
        notes.append("[+0] recommended_strategy.option missing or trivially short")

    # 3b. Trade-offs acknowledged (+5)
    if len(tradeoffs) >= 2:
        pts += 5
        notes.append(f"[+5] {len(tradeoffs)} trade-offs acknowledged")
    else:
        notes.append(f"[+0] Only {len(tradeoffs)} trade-off(s) — strategy appears overly optimistic")

    # 3c. GTM transformation has concrete pricing/retention language (+5)
    gtm = submission.get("gtm_transformation", {})
    gtm_text = " ".join(str(v) for v in gtm.values() if isinstance(v, str))
    pricing_terms = ["saas", "platform", "subscription", "per seat", "usage", "migration"]
    if any(t in gtm_text.lower() for t in pricing_terms):
        pts += 5
        notes.append("[+5] GTM plan mentions SaaS/pricing transformation mechanisms")
    else:
        notes.append("[+0] GTM plan lacks specific pricing/migration language")

    # 3d. Org plan has named new capability types (+5)
    org = submission.get("org_transformation", {})
    new_roles = org.get("new_roles_required", [])
    ai_roles = [r for r in new_roles
                if any(kw in str(r).lower() for kw in ["ai", "data", "engineer", "clinical", "scientist", "product"])]
    if len(ai_roles) >= 3:
        pts += 5
        notes.append(f"[+5] {len(ai_roles)} AI/tech-specific new roles identified")
    else:
        notes.append(f"[+0] Only {len(ai_roles)} AI/tech-specific roles (need 3+)")

    return round(pts, 1), max_score, notes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P1 MarketPivot — Submission Evaluator"
    )
    parser.add_argument(
        "--submission", required=True,
        help="Path to submission JSON file"
    )
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

    # Run checks
    sc_score, sc_max, sc_details, missing = check_section_completeness(submission)
    qv_score, qv_max, qv_errors, qv_checks = check_quantitative_validity(submission)
    coh_score, coh_max, coh_notes = check_strategic_coherence(submission)

    total = round(sc_score + qv_score + coh_score, 1)
    all_errors = qv_errors

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
        "errors": all_errors,
        "missing_sections": missing,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
