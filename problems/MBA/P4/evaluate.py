"""
MBA-P4: LaunchPad — Submission Evaluator
=========================================
Usage:
    python evaluate.py --submission <path_to_submission.json>

REQUIRED SUBMISSION JSON SCHEMA
--------------------------------
{
  "market_sizing": {
    "tam_usd_b": float,                              // must be 15.0 (given)
    "sam_usd_b": float,                              // 1.0–5.0 expected range
    "som_18month_usd_m": float,                      // 18-month reachable revenue
    "tam_methodology": "str",                        // top-down source/rationale
    "sam_methodology": "str",
    "som_bottom_up": {
      "sales_reps": int,
      "active_deals_per_rep": int,
      "win_rate_pct": float,
      "acv_usd_k": float,
      "sales_cycle_months": float,
      "total_closed_deals": float
    },
    "icp_definition": {
      "industry": ["str", ...],                      // min 2 industries
      "company_size": "str",
      "pain_point": "str",
      "budget_authority": "str"
    }
  },
  "gtm_strategy": {
    "positioning_statement": "str",                  // 1–3 sentences
    "competitive_matrix": {                          // at least 3 competitors
      "<competitor>": {
        "<criterion>": "str"
      }
    },
    "sales_methodology": "str",                      // e.g. "MEDDIC"
    "sales_playbook_stages": ["str", ...],           // min 4 stages
    "value_proposition": "str"
  },
  "channel_strategy": {
    "direct_vs_plg_vs_partner_decision": "str",
    "budget_by_channel": {                           // must sum to ~500K
      "<channel>": float
    },
    "expected_leads_by_channel": {
      "<channel>": int
    },
    "rationale": "str"
  },
  "financial_projections": {
    "monthly_arr_usd_k": [float, ...],               // 18 values (one per month)
    "month_18_arr_usd_m": float,
    "cac_usd_k": float,                              // Customer Acquisition Cost
    "ltv_usd_k": float,                              // Lifetime Value
    "ltv_cac_ratio": float,                          // must be >= 3.0
    "payback_period_months": int,
    "series_b_arr_threshold_usd_m": float,           // your estimate of Series B target
    "series_b_achievable": bool
  },
  "action_plan_90_days": {
    "sprint_1_days_1_30": [                          // min 3 actions
      {"action": "str", "owner": "str", "success_metric": "str"}
    ],
    "sprint_2_days_31_60": [                         // min 3 actions
      {"action": "str", "owner": "str", "success_metric": "str"}
    ],
    "sprint_3_days_61_90": [                         // min 3 actions
      {"action": "str", "owner": "str", "success_metric": "str"}
    ]
  }
}
"""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "market_sizing",
    "gtm_strategy",
    "channel_strategy",
    "financial_projections",
    "action_plan_90_days",
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

        if section == "market_sizing":
            required_keys = ["tam_usd_b", "sam_usd_b", "som_18month_usd_m", "icp_definition"]
            missing_keys = [k for k in required_keys if k not in sec]
            if missing_keys:
                details[section] = f"PARTIAL (missing: {missing_keys})"
                continue
            bottom_up = sec.get("som_bottom_up", {})
            if not bottom_up or not bottom_up.get("acv_usd_k"):
                details[section] = "PARTIAL (missing som_bottom_up calculation)"
                continue

        elif section == "gtm_strategy":
            if not sec.get("positioning_statement"):
                details[section] = "PARTIAL (missing positioning_statement)"
                continue
            playbook = sec.get("sales_playbook_stages", [])
            if len(playbook) < 4:
                details[section] = f"PARTIAL (only {len(playbook)} playbook stages, need 4+)"
                continue
            comp_matrix = sec.get("competitive_matrix", {})
            if len(comp_matrix) < 3:
                details[section] = f"PARTIAL (only {len(comp_matrix)} competitors in matrix, need 3+)"
                continue

        elif section == "channel_strategy":
            budget = sec.get("budget_by_channel", {})
            if not budget or len(budget) < 3:
                details[section] = f"PARTIAL (only {len(budget)} channels with budget, need 3+)"
                continue

        elif section == "financial_projections":
            arr_monthly = sec.get("monthly_arr_usd_k", [])
            if len(arr_monthly) < 18:
                details[section] = f"PARTIAL (only {len(arr_monthly)} monthly ARR values, need 18)"
                continue
            required_fp = ["cac_usd_k", "ltv_usd_k", "ltv_cac_ratio", "series_b_arr_threshold_usd_m"]
            missing_fp = [k for k in required_fp if sec.get(k) is None]
            if missing_fp:
                details[section] = f"PARTIAL (missing: {missing_fp})"
                continue

        elif section == "action_plan_90_days":
            sprints = ["sprint_1_days_1_30", "sprint_2_days_31_60", "sprint_3_days_61_90"]
            for sprint in sprints:
                if len(sec.get(sprint, [])) < 3:
                    details[section] = f"PARTIAL ({sprint} has fewer than 3 actions)"
                    break
            else:
                details[section] = "OK"
            if details.get(section) != "OK":
                continue

        if section not in details:
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

    ms = submission.get("market_sizing", {})
    fp = submission.get("financial_projections", {})
    cs = submission.get("channel_strategy", {})

    # 2a. TAM is anchored at $15B
    tam = ms.get("tam_usd_b", None)
    if isinstance(tam, (int, float)) and abs(tam - 15.0) < 2.0:
        checks.append((f"TAM = ${tam}B correctly anchored at $15B", True))
    else:
        checks.append((f"TAM = ${tam}B — should be ~$15B as given in problem", False))
        errors.append("market_sizing.tam_usd_b should be 15.0 ($15B as given in problem statement)")

    # 2b. SAM is a plausible fraction of TAM (1–7B)
    sam = ms.get("sam_usd_b", None)
    if isinstance(sam, (int, float)) and 1.0 <= sam <= 7.0:
        checks.append((f"SAM = ${sam}B in plausible range [$1B–$7B]", True))
    else:
        checks.append((f"SAM = ${sam}B outside plausible range [$1B–$7B]", False))
        errors.append("market_sizing.sam_usd_b should be 1–7B (20–50% of $15B TAM for cloud API logistics segment)")

    # 2c. SOM (18-month) is realistic — should be < $50M
    som = ms.get("som_18month_usd_m", None)
    if isinstance(som, (int, float)) and 0.5 <= som <= 50.0:
        checks.append((f"SOM 18-month = ${som}M in realistic range [$0.5M–$50M]", True))
    else:
        checks.append((f"SOM 18-month = ${som}M outside realistic range [$0.5M–$50M]", False))
        errors.append("market_sizing.som_18month_usd_m should be $0.5M–$50M (18-month reachable from 5 customers/$50K ARR)")

    # 2d. LTV/CAC ratio >= 3.0
    ltv_cac = fp.get("ltv_cac_ratio", None)
    if isinstance(ltv_cac, (int, float)) and ltv_cac >= 3.0:
        checks.append((f"LTV/CAC = {ltv_cac}x meets minimum threshold (3x)", True))
    else:
        checks.append((f"LTV/CAC = {ltv_cac}x below 3x minimum or not computed", False))
        errors.append("financial_projections.ltv_cac_ratio must be >= 3.0 (industry standard minimum for SaaS)")

    # 2e. Monthly ARR list has 18 entries and is non-decreasing (mostly)
    arr_list = fp.get("monthly_arr_usd_k", [])
    if len(arr_list) == 18:
        # Check that Month 18 > Month 1 (growing)
        if isinstance(arr_list[0], (int, float)) and isinstance(arr_list[-1], (int, float)):
            if arr_list[-1] > arr_list[0]:
                checks.append((f"ARR grows from ${arr_list[0]}K to ${arr_list[-1]}K over 18 months", True))
            else:
                checks.append(("ARR does not grow over 18 months", False))
                errors.append("financial_projections.monthly_arr_usd_k should show growth from Month 1 to Month 18")
        else:
            checks.append(("ARR list contains non-numeric values", False))
            errors.append("monthly_arr_usd_k must be a list of 18 numbers")
    else:
        checks.append((f"ARR list has {len(arr_list)} entries (need 18)", False))
        errors.append("financial_projections.monthly_arr_usd_k must have exactly 18 values")

    # 2f. Channel budget sums to ~$500K
    budget = cs.get("budget_by_channel", {})
    budget_total = sum(v for v in budget.values() if isinstance(v, (int, float)))
    if 400 <= budget_total <= 600:
        checks.append((f"Channel budget total ${budget_total}K ≈ $500K marketing budget", True))
    else:
        checks.append((f"Channel budget total ${budget_total}K diverges from $500K budget", False))
        errors.append("channel_strategy.budget_by_channel values must sum to approximately $500K")

    # 2g. Series B threshold is stated and plausible (3–15M ARR)
    sb_target = fp.get("series_b_arr_threshold_usd_m", None)
    if isinstance(sb_target, (int, float)) and 3.0 <= sb_target <= 15.0:
        checks.append((f"Series B ARR target ${sb_target}M in range [$3M–$15M]", True))
    else:
        checks.append((f"Series B target ${sb_target}M outside range [$3M–$15M] or missing", False))
        errors.append("financial_projections.series_b_arr_threshold_usd_m must be $3M–$15M for B2B deep-tech")

    # 2h. ACV is present and in plausible range ($50K–$500K for Fortune 500 B2B)
    acv = ms.get("som_bottom_up", {}).get("acv_usd_k", None)
    if isinstance(acv, (int, float)) and 50 <= acv <= 500:
        checks.append((f"ACV ${acv}K in plausible range [$50K–$500K]", True))
    else:
        checks.append((f"ACV ${acv}K outside Fortune 500 B2B range [$50K–$500K]", False))
        errors.append("market_sizing.som_bottom_up.acv_usd_k should be $50K–$500K for Fortune 500 enterprise B2B")

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

    # 3a. Positioning statement differentiates from free alternative (OR-Tools) (+5)
    positioning = submission.get("gtm_strategy", {}).get("positioning_statement", "")
    gtm_text = json.dumps(submission.get("gtm_strategy", {})).lower()
    if any(kw in gtm_text for kw in ["or-tools", "gurobi", "cplex", "competitor", "unlike", "outperform"]):
        pts += 5
        notes.append("[+5] GTM strategy explicitly addresses competitive differentiation")
    else:
        notes.append("[+0] GTM strategy lacks competitive differentiation vs. free/open-source alternatives")

    # 3b. Sales methodology is named (MEDDIC, Challenger, SPIN, etc.) (+5)
    methodology = submission.get("gtm_strategy", {}).get("sales_methodology", "")
    named_methods = ["meddic", "challenger", "spin", "sandler", "gap selling", "force management"]
    if any(m in str(methodology).lower() for m in named_methods):
        pts += 5
        notes.append(f"[+5] Named sales methodology: '{methodology}'")
    else:
        notes.append("[+0] No named sales methodology — enterprise B2B requires structured qualification")

    # 3c. Channel strategy addresses the long sales cycle constraint (+5)
    cs_text = json.dumps(submission.get("channel_strategy", {})).lower()
    if any(kw in cs_text for kw in ["enterprise", "outbound", "abm", "account-based", "direct sales", "sales cycle"]):
        pts += 5
        notes.append("[+5] Channel strategy accounts for enterprise B2B sales cycle dynamics")
    else:
        notes.append("[+0] Channel strategy lacks enterprise B2B context (long sales cycle, high ACV)")

    # 3d. 90-day plan has concrete first actions related to pipeline building (+5)
    plan_text = json.dumps(submission.get("action_plan_90_days", {})).lower()
    if any(kw in plan_text for kw in ["outreach", "champion", "icp", "account", "pipeline", "prospect"]):
        pts += 5
        notes.append("[+5] 90-day plan includes pipeline/prospecting actions")
    else:
        notes.append("[+0] 90-day plan lacks immediate pipeline-building actions")

    return round(pts, 1), max_score, notes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P4 LaunchPad — Submission Evaluator"
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
