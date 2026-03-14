"""
MBA-P1: MarketPivot — Strategic Repositioning Analysis Scaffold
================================================================
MediCore Health: $2B healthcare IT company facing AI/EV disruption.
Develop a 3-year transformation plan.

Usage:
    python starter.py [--output analysis.json]

Outputs:
    analysis.json  — computed metrics and strategy scoring scaffold
"""

import argparse
import json
import math
import sys


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY CONSTANTS  (do not change — these are the problem parameters)
# ─────────────────────────────────────────────────────────────────────────────
COMPANY = {
    "name": "MediCore Health",
    "revenue_current": 2_000,          # $M
    "revenue_growth_rate": -0.05,       # -5% YoY
    "ebitda_margin": 0.18,
    "cash_reserves": 500,              # $M
    "debt": 800,                       # $M (maturing in 3 years)
    "rd_spend": 160,                   # $M/year (8% of revenue)
    "churn_rate_current": 0.15,        # 15% annual customer churn
    "churn_rate_prior": 0.05,          # was 5% 18 months ago
    "nps_current": 12,
    "nps_prior": 45,
    "segments": {
        "ehr_software": {"revenue_share": 0.60, "margin": 0.25},
        "medical_billing": {"revenue_share": 0.25, "margin": 0.20},
        "telehealth": {"revenue_share": 0.15, "margin": 0.10},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: STRATEGIC OPTIONS SCORING
# ─────────────────────────────────────────────────────────────────────────────
# Fill in your scores (0-10) for each option × criterion.
# Criteria weights must sum to 1.0.

SCORING_CRITERIA = {
    "speed_to_capability":  0.25,   # How quickly can this option close the AI capability gap?
    "cost_efficiency":      0.20,   # Total investment required vs. expected return
    "ip_and_control":       0.20,   # Degree of proprietary technology and competitive moat
    "execution_risk":       0.20,   # Organisational ability to execute (lower risk = higher score)
    "strategic_fit":        0.15,   # Alignment with long-term healthcare AI vision
}

# TODO: Replace all None values with your scores (0–10).
STRATEGIC_OPTIONS = {
    "Build": {
        "description": "Develop proprietary AI capabilities in-house",
        "capex_estimate_usd_m": 400,   # estimated 3-year investment
        "scores": {
            "speed_to_capability": None,   # TODO: score 0-10
            "cost_efficiency":     None,   # TODO: score 0-10
            "ip_and_control":      None,   # TODO: score 0-10
            "execution_risk":      None,   # TODO: score 0-10
            "strategic_fit":       None,   # TODO: score 0-10
        },
        "pros": ["Full IP ownership", "Deep product integration"],
        "cons": ["18-24 month lag to market", "Talent acquisition risk", "High burn rate"],
    },
    "Buy": {
        "description": "Acquire AI healthcare startups",
        "capex_estimate_usd_m": 350,   # estimated acquisition spend
        "scores": {
            "speed_to_capability": None,   # TODO: score 0-10
            "cost_efficiency":     None,   # TODO: score 0-10
            "ip_and_control":      None,   # TODO: score 0-10
            "execution_risk":      None,   # TODO: score 0-10
            "strategic_fit":       None,   # TODO: score 0-10
        },
        "pros": ["Speed", "Proven technology", "Acqui-hire talent"],
        "cons": ["Integration risk", "Premium pricing in hot market", "Culture clash"],
    },
    "Partner": {
        "description": "Form strategic alliances with tech giants",
        "capex_estimate_usd_m": 50,    # partnership development cost
        "scores": {
            "speed_to_capability": None,   # TODO: score 0-10
            "cost_efficiency":     None,   # TODO: score 0-10
            "ip_and_control":      None,   # TODO: score 0-10
            "execution_risk":      None,   # TODO: score 0-10
            "strategic_fit":       None,   # TODO: score 0-10
        },
        "pros": ["Low capex", "Access to frontier AI", "Fast go-to-market"],
        "cons": ["Dependency risk", "Limited IP ownership", "Partner may compete directly"],
    },
    "Pivot": {
        "description": "Transform into healthcare AI platform company",
        "capex_estimate_usd_m": 500,   # full transformation spend
        "scores": {
            "speed_to_capability": None,   # TODO: score 0-10
            "cost_efficiency":     None,   # TODO: score 0-10
            "ip_and_control":      None,   # TODO: score 0-10
            "execution_risk":      None,   # TODO: score 0-10
            "strategic_fit":       None,   # TODO: score 0-10
        },
        "pros": ["Largest long-term upside", "New revenue streams", "Platform network effects"],
        "cons": ["Highest execution risk", "Revenue gap during transition", "Cultural transformation required"],
    },
}


def score_strategic_options(options: dict, criteria_weights: dict) -> dict:
    """
    Compute weighted scores for each strategic option.
    Returns a dict: {option_name: {"weighted_score": float, "rank": int}}
    """
    results = {}
    for option_name, option_data in options.items():
        scores = option_data["scores"]
        # Skip options with None scores (not yet filled in)
        if any(v is None for v in scores.values()):
            results[option_name] = {
                "weighted_score": None,
                "raw_scores": scores,
                "note": "TODO: Fill in scores to enable ranking",
            }
            continue

        weighted = sum(scores[c] * w for c, w in criteria_weights.items())
        results[option_name] = {
            "weighted_score": round(weighted, 2),
            "raw_scores": scores,
        }

    # Rank completed options
    completed = {k: v for k, v in results.items() if v["weighted_score"] is not None}
    ranked = sorted(completed, key=lambda k: completed[k]["weighted_score"], reverse=True)
    for rank, name in enumerate(ranked, start=1):
        results[name]["rank"] = rank

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: REVENUE PROJECTION MODEL
# ─────────────────────────────────────────────────────────────────────────────

def project_revenue(
    base_revenue: float,
    churn_rate: float,
    new_customer_growth_rate: float,    # TODO: set based on your strategy
    ai_uplift_rate: float,              # TODO: expected uplift from AI product launch
    years: int = 3,
) -> list:
    """
    Simple revenue projection incorporating churn and new customer growth.

    Parameters
    ----------
    base_revenue             : current annual revenue ($M)
    churn_rate               : annual customer churn rate (0–1)
    new_customer_growth_rate : net new customer revenue growth rate per year (0–1)
    ai_uplift_rate           : additional revenue from AI product launch per year (0–1)
    years                    : projection horizon

    Returns
    -------
    List of dicts, one per year.
    """
    projections = []
    revenue = base_revenue

    for yr in range(1, years + 1):
        revenue_lost_to_churn = revenue * churn_rate
        revenue_from_new_customers = revenue * new_customer_growth_rate
        ai_revenue = revenue * ai_uplift_rate * yr           # grows with time
        revenue = revenue - revenue_lost_to_churn + revenue_from_new_customers + ai_revenue
        revenue = max(revenue, 0)

        projections.append({
            "year": yr,
            "revenue_usd_m": round(revenue, 1),
            "revenue_lost_to_churn_usd_m": round(revenue_lost_to_churn, 1),
            "new_customer_revenue_usd_m": round(revenue_from_new_customers, 1),
            "ai_product_revenue_usd_m": round(ai_revenue, 1),
        })

    return projections


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: EBITDA & CASH FLOW MODEL
# ─────────────────────────────────────────────────────────────────────────────

def build_pl_model(revenue_projections: list, scenario: str = "base") -> list:
    """
    Build a 3-year P&L from revenue projections.

    TODO: Adjust margin assumptions per your strategy.
    """
    # Margin assumptions by scenario — adjust to match your strategy
    MARGIN_ASSUMPTIONS = {
        "base": {
            "gross_margin":       [0.52, 0.54, 0.56],   # improving with SaaS mix
            "rd_pct_of_revenue":  [0.10, 0.11, 0.12],   # increasing AI investment
            "sg_and_a_pct":       [0.28, 0.27, 0.26],   # efficiency gains
        },
        "bull": {
            "gross_margin":       [0.54, 0.58, 0.62],
            "rd_pct_of_revenue":  [0.10, 0.11, 0.12],
            "sg_and_a_pct":       [0.26, 0.24, 0.22],
        },
        "bear": {
            "gross_margin":       [0.50, 0.50, 0.51],
            "rd_pct_of_revenue":  [0.10, 0.11, 0.12],
            "sg_and_a_pct":       [0.30, 0.30, 0.29],
        },
    }

    assumptions = MARGIN_ASSUMPTIONS.get(scenario, MARGIN_ASSUMPTIONS["base"])
    pl = []

    for i, yr_data in enumerate(revenue_projections):
        rev = yr_data["revenue_usd_m"]
        gm  = assumptions["gross_margin"][i]
        rd  = assumptions["rd_pct_of_revenue"][i]
        sga = assumptions["sg_and_a_pct"][i]

        gross_profit = round(rev * gm, 1)
        rd_spend     = round(rev * rd, 1)
        sga_spend    = round(rev * sga, 1)
        ebitda       = round(gross_profit - rd_spend - sga_spend, 1)
        ebitda_margin = round(ebitda / rev * 100, 1) if rev > 0 else 0

        pl.append({
            "year":               yr_data["year"],
            "scenario":           scenario,
            "revenue_usd_m":      rev,
            "gross_profit_usd_m": gross_profit,
            "gross_margin_pct":   round(gm * 100, 1),
            "rd_spend_usd_m":     rd_spend,
            "sga_spend_usd_m":    sga_spend,
            "ebitda_usd_m":       ebitda,
            "ebitda_margin_pct":  ebitda_margin,
        })

    return pl


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: BREAK-EVEN ANALYSIS FOR AI PRODUCT
# ─────────────────────────────────────────────────────────────────────────────

def break_even_analysis(
    fixed_investment_usd_m: float,    # one-time AI product development cost
    annual_fixed_cost_usd_m: float,   # ongoing annual cost (infra, team)
    gross_margin_pct: float,          # gross margin of the AI product
    avg_annual_contract_value_usd_k: float,  # ACV per customer in $K
) -> dict:
    """
    Calculate break-even customers and revenue for the AI product line.

    TODO: Fill in realistic values based on your strategy.
    """
    # TODO: Validate and adjust these inputs based on your research
    gross_margin = gross_margin_pct / 100
    acv_per_customer = avg_annual_contract_value_usd_k / 1000   # convert to $M

    if gross_margin <= 0 or acv_per_customer <= 0:
        return {"error": "Invalid inputs — gross margin and ACV must be positive"}

    # Contribution margin per customer per year ($M)
    contribution_per_customer = acv_per_customer * gross_margin

    # Break-even on annual fixed costs
    annual_break_even_customers = math.ceil(
        annual_fixed_cost_usd_m / contribution_per_customer
    )

    # Break-even on total investment (amortised over 3 years)
    total_fixed = fixed_investment_usd_m + annual_fixed_cost_usd_m * 3
    total_break_even_customers = math.ceil(
        total_fixed / (contribution_per_customer * 3)
    )

    break_even_revenue_usd_m = round(total_break_even_customers * acv_per_customer, 1)

    return {
        "fixed_investment_usd_m":          fixed_investment_usd_m,
        "annual_fixed_cost_usd_m":         annual_fixed_cost_usd_m,
        "gross_margin_pct":                gross_margin_pct,
        "acv_per_customer_usd_k":          avg_annual_contract_value_usd_k,
        "annual_break_even_customers":     annual_break_even_customers,
        "total_break_even_customers_3yr":  total_break_even_customers,
        "break_even_revenue_usd_m":        break_even_revenue_usd_m,
        "note": "TODO: Validate ACV and margin assumptions against market research",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: DEBT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def debt_management_plan(
    debt_usd_m: float = 800,
    cash_reserves_usd_m: float = 500,
    annual_fcf_usd_m: float = None,    # TODO: derive from your P&L model
) -> dict:
    """
    Evaluate options for the $800M debt maturing in 3 years.
    Options: Refinance, Repay from cash + FCF, Equity raise, Asset sale.
    """
    # TODO: Calculate annual FCF from your P&L and use it here
    if annual_fcf_usd_m is None:
        # Placeholder: assume 8% FCF margin on $1.9B Year 1 revenue
        annual_fcf_usd_m = 1_900 * 0.08

    cash_available_in_3yr = cash_reserves_usd_m + annual_fcf_usd_m * 3
    shortfall = max(0, debt_usd_m - cash_available_in_3yr)

    return {
        "debt_usd_m":                  debt_usd_m,
        "cash_reserves_usd_m":         cash_reserves_usd_m,
        "estimated_annual_fcf_usd_m":  round(annual_fcf_usd_m, 1),
        "cash_available_in_3yr_usd_m": round(cash_available_in_3yr, 1),
        "shortfall_usd_m":             round(shortfall, 1),
        "options": {
            "refinance":   "Roll over at current rates (~6–7% for investment grade). Feasible if EBITDA improves.",
            "repay":       "Use cash + FCF. Feasible only if shortfall = 0.",
            "equity_raise": "Dilutive but preserves cash for transformation investment.",
            "asset_sale":  "Sell medical billing division (~$500–700M at 1.5x revenue). Reduces complexity.",
        },
        "recommendation": "TODO: State your preferred debt strategy and quantify the cost",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P1 MarketPivot — Strategic Analysis Scaffold"
    )
    parser.add_argument(
        "--output", default="analysis.json",
        help="Output path for analysis JSON (default: analysis.json)"
    )
    # Optional: override key parameters
    parser.add_argument("--churn-rate", type=float, default=0.15,
                        help="Annual customer churn rate (default: 0.15)")
    parser.add_argument("--new-customer-growth", type=float, default=0.05,
                        help="Net new customer revenue growth rate (default: 0.05)")
    parser.add_argument("--ai-uplift", type=float, default=0.02,
                        help="AI product revenue uplift per year (default: 0.02)")
    parser.add_argument("--scenario", choices=["base", "bull", "bear"], default="base",
                        help="Financial scenario (default: base)")

    args = parser.parse_args()

    print(f"[MBA-P1] MarketPivot Analysis — MediCore Health")
    print(f"  Scenario: {args.scenario}")
    print(f"  Churn rate: {args.churn_rate * 100:.1f}%")
    print(f"  New customer growth: {args.new_customer_growth * 100:.1f}%")
    print(f"  AI uplift: {args.ai_uplift * 100:.1f}% per year")

    # 1. Score strategic options
    option_scores = score_strategic_options(STRATEGIC_OPTIONS, SCORING_CRITERIA)
    print(f"\n[1/5] Strategic options scored — {sum(1 for v in option_scores.values() if v.get('weighted_score') is not None)} / {len(option_scores)} complete")

    # 2. Revenue projections
    revenue_proj = project_revenue(
        base_revenue=COMPANY["revenue_current"],
        churn_rate=args.churn_rate,
        new_customer_growth_rate=args.new_customer_growth,
        ai_uplift_rate=args.ai_uplift,
        years=3,
    )
    print(f"[2/5] Revenue projections: Y1={revenue_proj[0]['revenue_usd_m']}M  "
          f"Y2={revenue_proj[1]['revenue_usd_m']}M  "
          f"Y3={revenue_proj[2]['revenue_usd_m']}M")

    # 3. P&L model
    pl = build_pl_model(revenue_proj, scenario=args.scenario)
    print(f"[3/5] P&L model built — EBITDA Y3: {pl[2]['ebitda_usd_m']}M "
          f"({pl[2]['ebitda_margin_pct']}% margin)")

    # 4. Break-even analysis (placeholder values — TODO: fill in)
    breakeven = break_even_analysis(
        fixed_investment_usd_m=200,         # TODO: update with your strategy cost
        annual_fixed_cost_usd_m=40,         # TODO: update with your AI team/infra cost
        gross_margin_pct=65.0,              # TODO: AI product gross margin
        avg_annual_contract_value_usd_k=180,  # TODO: AI product ACV
    )
    print(f"[4/5] Break-even: {breakeven.get('annual_break_even_customers', 'N/A')} customers "
          f"for annual cost coverage")

    # 5. Debt management
    y1_ebitda = pl[0]["ebitda_usd_m"]
    est_fcf = y1_ebitda * 0.70  # rough FCF conversion
    debt_plan = debt_management_plan(annual_fcf_usd_m=est_fcf)
    print(f"[5/5] Debt: $800M due in 3yr — shortfall estimate: "
          f"${debt_plan['shortfall_usd_m']}M")

    # Assemble output
    analysis = {
        "problem": "MBA-P1: MarketPivot",
        "company": COMPANY["name"],
        "scenario": args.scenario,
        "parameters": {
            "churn_rate": args.churn_rate,
            "new_customer_growth_rate": args.new_customer_growth,
            "ai_uplift_rate": args.ai_uplift,
        },
        "strategic_options_scores": option_scores,
        "revenue_projections": revenue_proj,
        "pl_model": pl,
        "break_even_analysis": breakeven,
        "debt_management": debt_plan,
        "summary": {
            "year_3_revenue_usd_m":      revenue_proj[2]["revenue_usd_m"],
            "year_3_ebitda_usd_m":       pl[2]["ebitda_usd_m"],
            "year_3_ebitda_margin_pct":  pl[2]["ebitda_margin_pct"],
            "recommended_option":        "TODO: Insert your recommended strategy here",
            "investment_required_usd_m": "TODO: Insert total capex for your plan",
            "key_risks":                 ["TODO: Risk 1", "TODO: Risk 2", "TODO: Risk 3"],
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nOutput written to: {args.output}")
    print("NEXT STEPS:")
    print("  1. Fill in TODO scores in STRATEGIC_OPTIONS (lines 55-98)")
    print("  2. Tune revenue model parameters (--churn-rate, --new-customer-growth, --ai-uplift)")
    print("  3. Adjust P&L margin assumptions in build_pl_model() to match your strategy")
    print("  4. Update break_even_analysis() inputs with your AI product pricing")
    print("  5. Build your full submission.json using analysis.json as the quantitative backbone")


if __name__ == "__main__":
    main()
