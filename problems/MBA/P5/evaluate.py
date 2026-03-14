"""
MBA-P5: DealArchitect — Submission Evaluator
=============================================
Usage:
    python evaluate.py --submission <path_to_submission.json>

REQUIRED SUBMISSION JSON SCHEMA
--------------------------------
{
  "dcf_valuation": {
    "wacc_pct": float,                             // VALID RANGE: 7.0–15.0
    "terminal_growth_rate_pct": float,             // VALID RANGE: 1.0–5.0
    "pv_fcf_sum_usd_m": float,                     // sum of PV of projected FCFs
    "pv_terminal_value_usd_m": float,              // PV of terminal value
    "enterprise_value_usd_m": float,               // EV = PV_FCF + PV_TV
    "equity_value_usd_m": float,                   // EV - net debt
    "sensitivity_table": {                         // 3x3 WACC × TGR sensitivity
      "<wacc_label>": {
        "<tgr_label>": float                       // equity value for each cell
      }
    }
  },
  "comps_analysis": {
    "selected_comps": [                            // min 3 comparables
      {
        "company": "str",
        "ev_revenue_multiple": float,
        "rationale": "str"
      }
    ],
    "median_ev_revenue_multiple": float,
    "applied_multiple": float,
    "implied_ev_usd_m": float,
    "implied_equity_value_usd_m": float,
    "discount_rationale": "str"
  },
  "precedent_analysis": {
    "transactions": [                              // min 2 precedents
      {
        "deal": "str",
        "ev_revenue_multiple": float,
        "rationale": "str"
      }
    ],
    "median_multiple": float,
    "implied_ev_usd_m": float,
    "implied_equity_value_usd_m": float,
    "control_premium_applied_pct": float
  },
  "synergy_analysis": {
    "revenue_synergies": {
      "conservative_usd_m": float,
      "base_usd_m": float,
      "optimistic_usd_m": float,
      "key_driver": "str"
    },
    "cost_synergies": {
      "conservative_usd_m": float,
      "base_usd_m": float,
      "optimistic_usd_m": float,
      "key_driver": "str"
    },
    "total_synergy_npv_base_usd_m": float,
    "synergy_share_to_seller_pct": float           // % of synergy value offered to seller
  },
  "deal_structure": {
    "recommended_offer_price_usd_m": float,
    "walk_away_price_usd_m": float,
    "cash_vs_stock_mix": "str",                    // e.g. "70% cash / 30% CloudStack stock"
    "earnout_structure": "str",
    "key_employee_retention_pool_usd_m": float
  },
  "integration_plan": {
    "day_1_readiness": ["str", ...],               // min 3 Day 1 actions
    "phase_100_days": {
      "org_design": "str",
      "technology_integration": "str",
      "culture_plan": "str",
      "customer_communication": "str"
    },
    "key_risks": [                                 // min 3 risks
      {"risk": "str", "probability": "str", "mitigation": "str"}
    ]
  },
  "recommendation": {
    "decision": "Buy|Pass|Conditional",
    "rationale": "str",
    "key_conditions": ["str"],                     // if Conditional
    "risk_factors": ["str", ...]                   // min 3 risk factors
  }
}
"""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "dcf_valuation",
    "comps_analysis",
    "precedent_analysis",
    "synergy_analysis",
    "deal_structure",
    "integration_plan",
    "recommendation",
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

        if section == "dcf_valuation":
            required_keys = ["wacc_pct", "enterprise_value_usd_m", "equity_value_usd_m", "sensitivity_table"]
            missing_keys = [k for k in required_keys if sec.get(k) is None]
            if missing_keys:
                details[section] = f"PARTIAL (missing: {missing_keys})"
                continue
            # Sensitivity table must have at least 2×2 structure
            st = sec.get("sensitivity_table", {})
            if not isinstance(st, dict) or len(st) < 2:
                details[section] = "PARTIAL (sensitivity_table must have at least 2 WACC rows)"
                continue

        elif section == "comps_analysis":
            comps = sec.get("selected_comps", [])
            if len(comps) < 3:
                details[section] = f"PARTIAL (only {len(comps)} comps, need 3+)"
                continue
            if not sec.get("implied_equity_value_usd_m"):
                details[section] = "PARTIAL (missing implied_equity_value_usd_m)"
                continue

        elif section == "precedent_analysis":
            txns = sec.get("transactions", [])
            if len(txns) < 2:
                details[section] = f"PARTIAL (only {len(txns)} precedents, need 2+)"
                continue

        elif section == "synergy_analysis":
            rev_syn = sec.get("revenue_synergies", {})
            cost_syn = sec.get("cost_synergies", {})
            if not rev_syn.get("base_usd_m") or not cost_syn.get("base_usd_m"):
                details[section] = "PARTIAL (missing base_usd_m for revenue or cost synergies)"
                continue
            if not sec.get("total_synergy_npv_base_usd_m"):
                details[section] = "PARTIAL (missing total_synergy_npv_base_usd_m)"
                continue

        elif section == "deal_structure":
            required_keys = ["recommended_offer_price_usd_m", "walk_away_price_usd_m"]
            missing_keys = [k for k in required_keys if not sec.get(k)]
            if missing_keys:
                details[section] = f"PARTIAL (missing: {missing_keys})"
                continue

        elif section == "integration_plan":
            day1 = sec.get("day_1_readiness", [])
            risks = sec.get("key_risks", [])
            if len(day1) < 3:
                details[section] = f"PARTIAL (only {len(day1)} Day 1 actions, need 3+)"
                continue
            if len(risks) < 3:
                details[section] = f"PARTIAL (only {len(risks)} key risks, need 3+)"
                continue

        elif section == "recommendation":
            valid_decisions = {"Buy", "Pass", "Conditional"}
            if sec.get("decision") not in valid_decisions:
                details[section] = f"PARTIAL (decision must be one of {valid_decisions})"
                continue
            risk_factors = sec.get("risk_factors", [])
            if len(risk_factors) < 3:
                details[section] = f"PARTIAL (only {len(risk_factors)} risk factors, need 3+)"
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

    dcf = submission.get("dcf_valuation", {})
    comps = submission.get("comps_analysis", {})
    prec = submission.get("precedent_analysis", {})
    syn = submission.get("synergy_analysis", {})
    ds = submission.get("deal_structure", {})

    # 2a. WACC in valid range [7%, 15%]
    wacc = dcf.get("wacc_pct", None)
    if isinstance(wacc, (int, float)) and 7.0 <= wacc <= 15.0:
        checks.append((f"WACC = {wacc}% in valid range [7%–15%]", True))
    else:
        checks.append((f"WACC = {wacc}% outside valid range [7%–15%]", False))
        errors.append("dcf_valuation.wacc_pct must be between 7.0 and 15.0 — this is standard for tech SaaS acquisitions")

    # 2b. Terminal growth rate in [1%, 5%]
    tgr = dcf.get("terminal_growth_rate_pct", None)
    if isinstance(tgr, (int, float)) and 1.0 <= tgr <= 5.0:
        checks.append((f"TGR = {tgr}% in valid range [1%–5%]", True))
    else:
        checks.append((f"TGR = {tgr}% outside valid range [1%–5%]", False))
        errors.append("dcf_valuation.terminal_growth_rate_pct must be between 1.0 and 5.0")

    # 2c. Enterprise value is positive and plausible ($500M–$10B range)
    ev = dcf.get("enterprise_value_usd_m", None)
    if isinstance(ev, (int, float)) and 500 <= ev <= 10_000:
        checks.append((f"DCF Enterprise Value = ${ev}M in plausible range [$500M–$10B]", True))
    else:
        checks.append((f"DCF EV = ${ev}M outside plausible range [$500M–$10B]", False))
        errors.append("dcf_valuation.enterprise_value_usd_m should be $500M–$10B for DataFlow Analytics")

    # 2d. Comps implied multiple in reasonable range (3x–25x EV/Revenue)
    comps_mult = comps.get("applied_multiple", None)
    if isinstance(comps_mult, (int, float)) and 3.0 <= comps_mult <= 25.0:
        checks.append((f"Comps applied multiple = {comps_mult}x in range [3x–25x]", True))
    else:
        checks.append((f"Comps applied multiple = {comps_mult}x outside range [3x–25x]", False))
        errors.append("comps_analysis.applied_multiple should be 3x–25x EV/Revenue for analytics SaaS")

    # 2e. Offer price >= last round valuation ($2B)
    offer = ds.get("recommended_offer_price_usd_m", None)
    if isinstance(offer, (int, float)) and offer >= 1_500:
        checks.append((f"Offer price ${offer}M >= minimum $1.5B threshold", True))
    else:
        checks.append((f"Offer price ${offer}M below $1.5B — likely below last round valuation ($2B)", False))
        errors.append("deal_structure.recommended_offer_price_usd_m should be >= $1,500M (DataFlow's last round was $2B)")

    # 2f. Walk-away price >= offer price
    walkaway = ds.get("walk_away_price_usd_m", None)
    if isinstance(offer, (int, float)) and isinstance(walkaway, (int, float)) and walkaway >= offer:
        checks.append((f"Walk-away ${walkaway}M >= offer ${offer}M", True))
    else:
        checks.append(("Walk-away price is less than offer price or missing", False))
        errors.append("deal_structure.walk_away_price_usd_m must be >= recommended_offer_price_usd_m")

    # 2g. Synergy NPV is positive
    syn_npv = syn.get("total_synergy_npv_base_usd_m", None)
    if isinstance(syn_npv, (int, float)) and syn_npv > 0:
        checks.append((f"Synergy NPV (base) = ${syn_npv}M > 0", True))
    else:
        checks.append((f"Synergy NPV = ${syn_npv}M — must be positive", False))
        errors.append("synergy_analysis.total_synergy_npv_base_usd_m must be positive")

    # 2h. Sensitivity table is not all identical values (non-trivial analysis)
    st = dcf.get("sensitivity_table", {})
    if isinstance(st, dict) and len(st) >= 2:
        all_values = []
        for row_data in st.values():
            if isinstance(row_data, dict):
                all_values.extend(v for v in row_data.values() if isinstance(v, (int, float)))
        if len(set(all_values)) > 1:
            checks.append(("Sensitivity table has varying values (non-trivial analysis)", True))
        else:
            checks.append(("Sensitivity table has all identical values — likely not computed properly", False))
            errors.append("dcf_valuation.sensitivity_table cells should vary with WACC and TGR assumptions")
    else:
        checks.append(("Sensitivity table structure invalid", False))
        errors.append("dcf_valuation.sensitivity_table must be a nested dict with at least 2 rows")

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

    # 3a. Recommendation is clear and consistent with valuation (+5)
    rec = submission.get("recommendation", {})
    decision = rec.get("decision", "")
    rationale = rec.get("rationale", "")
    if decision in ("Buy", "Pass", "Conditional") and len(str(rationale)) > 50:
        pts += 5
        notes.append(f"[+5] Clear recommendation: '{decision}' with substantive rationale")
    else:
        notes.append(f"[+0] Recommendation unclear or rationale too brief (need >50 chars)")

    # 3b. Integration plan addresses culture risk (startup vs. enterprise) (+5)
    integ_text = json.dumps(submission.get("integration_plan", {})).lower()
    if any(kw in integ_text for kw in ["culture", "startup", "retention", "founder", "autonomy", "standalone"]):
        pts += 5
        notes.append("[+5] Integration plan addresses culture/retention risk")
    else:
        notes.append("[+0] Integration plan lacks culture/retention language")

    # 3c. Synergy analysis has 3 scenarios (+5)
    syn = submission.get("synergy_analysis", {})
    rev_syn = syn.get("revenue_synergies", {})
    scenarios_present = all(
        rev_syn.get(s) is not None for s in ["conservative_usd_m", "base_usd_m", "optimistic_usd_m"]
    )
    if scenarios_present:
        pts += 5
        notes.append("[+5] Synergy analysis has conservative/base/optimistic scenarios")
    else:
        notes.append("[+0] Synergy analysis missing one or more scenarios")

    # 3d. Walk-away price is meaningfully higher than offer price (+5)
    ds = submission.get("deal_structure", {})
    offer = ds.get("recommended_offer_price_usd_m", 0)
    walkaway = ds.get("walk_away_price_usd_m", 0)
    if isinstance(offer, (int, float)) and isinstance(walkaway, (int, float)):
        premium = (walkaway - offer) / offer if offer > 0 else 0
        if 0.05 <= premium <= 0.50:
            pts += 5
            notes.append(f"[+5] Walk-away price is {round(premium*100)}% above offer ({offer}M → {walkaway}M)")
        elif premium > 0.50:
            notes.append(f"[+0] Walk-away premium {round(premium*100)}% is too large — implies poor negotiation discipline")
        else:
            notes.append(f"[+0] Walk-away price is not meaningfully above offer (need 5–50% premium)")
    else:
        notes.append("[+0] Offer or walk-away price not numeric")

    return round(pts, 1), max_score, notes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P5 DealArchitect — Submission Evaluator"
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
