"""
MBA-P4: LaunchPad — Go-to-Market Strategy Analysis Scaffold
============================================================
QuantumLeap: quantum-inspired optimisation SaaS startup.
Build a GTM strategy to reach Series B ARR threshold in 18 months.

No external data files required — all inputs are embedded below.

Usage:
    python starter.py [--output analysis.json]
                      [--acv-k <avg_contract_value_$K>]
                      [--win-rate <fraction>]
                      [--sales-cycle-months <months>]
                      [--series-b-target-m <$M ARR>]

Outputs:
    analysis.json  — TAM/SAM/SOM, CAC/LTV, funnel model, ARR projection
"""

import argparse
import json
import math


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY / MARKET CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
COMPANY = {
    "name": "QuantumLeap",
    "product": "Quantum-inspired optimisation engine (VRP, facility location, supply chain)",
    "pricing_model": "Usage-based ($0.01 per optimisation call)",
    "current_arr_usd_k": 50.0,
    "current_customers": 5,
    "employees": {"engineering": 10, "sales": 3, "marketing": 2, "leadership": 5},
    "series_a_usd_m": 15.0,
    "runway_months": 18,
    "marketing_budget_usd_k": 500.0,
}

MARKET = {
    "tam_usd_b": 15.0,        # Total Addressable Market (optimisation software)
    "target_buyer": "VP Supply Chain / VP Operations at Fortune 500",
    "avg_sales_cycle_months_min": 6,
    "avg_sales_cycle_months_max": 18,
    "competitors": [
        {"name": "Gurobi", "type": "classical_solver", "pricing": "license", "open_source": False},
        {"name": "CPLEX (IBM)", "type": "classical_solver", "pricing": "license", "open_source": False},
        {"name": "Google OR-Tools", "type": "classical_solver", "pricing": "free", "open_source": True},
        {"name": "D-Wave", "type": "quantum_hardware", "pricing": "cloud", "open_source": False},
        {"name": "Rigetti", "type": "quantum_hardware", "pricing": "cloud", "open_source": False},
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: TAM / SAM / SOM CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def calculate_market_sizing(
    acv_usd_k: float,
    win_rate: float,
    sales_cycle_months: float,
    sales_reps: int = 3,
    deals_per_rep: int = 40,
    sam_fraction_of_tam: float = 0.25,   # TODO: justify this estimate
) -> dict:
    """
    TAM / SAM / SOM market sizing.

    Top-down approach:
        TAM = $15B (given)
        SAM = TAM × sam_fraction (cloud API, logistics/supply chain segment)
        SOM = SAM × realistic_market_capture_pct (18-month achievable)

    Bottom-up approach:
        SOM_18mo = sales_reps × deals_per_rep × win_rate × acv_usd_k
                   × (18 / sales_cycle_months)  # time-weighted pipeline cycles

    TODO: Document your methodology for sam_fraction and win_rate assumptions.
    """
    tam_usd_b = MARKET["tam_usd_b"]

    # Top-down
    sam_usd_b = round(tam_usd_b * sam_fraction_of_tam, 2)
    # Plausible 18-month SOM: capture 0.1–2% of SAM
    som_topdown_usd_m = round(sam_usd_b * 1_000 * 0.001, 1)  # 0.1% of SAM

    # Bottom-up
    # Deals closeable per rep in 18 months = 18 / sales_cycle × deals_per_rep × win_rate
    pipeline_cycles = 18 / max(sales_cycle_months, 1)
    closed_deals_total = sales_reps * deals_per_rep * win_rate * pipeline_cycles
    som_bottomup_usd_m = round(closed_deals_total * acv_usd_k / 1_000, 2)

    # Reconcile: take lower of two (conservative)
    som_recommended_usd_m = min(som_topdown_usd_m, som_bottomup_usd_m)

    return {
        "tam_usd_b": tam_usd_b,
        "sam_usd_b": sam_usd_b,
        "sam_fraction_assumption": sam_fraction_of_tam,
        "sam_rationale": "TODO: Replace with specific segment data (e.g., Gartner/IDC report on logistics optimization)",
        "som_topdown_usd_m": som_topdown_usd_m,
        "som_bottomup_usd_m": som_bottomup_usd_m,
        "som_recommended_18month_usd_m": som_recommended_usd_m,
        "bottom_up_inputs": {
            "sales_reps": sales_reps,
            "active_deals_per_rep": deals_per_rep,
            "win_rate": win_rate,
            "avg_acv_usd_k": acv_usd_k,
            "sales_cycle_months": sales_cycle_months,
            "pipeline_cycles_in_18mo": round(pipeline_cycles, 2),
        },
        "total_closed_deals_18mo": round(closed_deals_total, 1),
        "icp_definition": {
            "industry": ["Logistics", "Retail", "Manufacturing", "CPG", "E-commerce"],
            "company_size": "Fortune 500 or mid-market with $1B+ revenue",
            "tech_readiness": "Has API integration capability, cloud-first",
            "pain_point": "Vehicle routing / supply chain optimisation cost > $5M/year",
            "budget_authority": "VP Operations or VP Supply Chain with $500K+ budget",
            "note": "TODO: Validate ICP criteria with your 5 existing customers — what do they have in common?",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: CAC / LTV MODEL
# ─────────────────────────────────────────────────────────────────────────────

def calculate_cac_ltv(
    acv_usd_k: float,
    gross_margin_pct: float = 90.0,     # API SaaS — very high gross margin
    annual_churn_rate: float = 0.10,    # 10% annual churn (TODO: adjust)
    sales_headcount: int = 3,
    sales_rep_fully_loaded_usd_k: float = 200.0,  # base + bonus + benefits
    marketing_budget_usd_k: float = 500.0,
    new_customers_18mo: float = 10.0,   # TODO: derive from your SOM model
) -> dict:
    """
    Calculate CAC, LTV, and LTV/CAC ratio.

    TODO: Update churn_rate and new_customers_18mo from your funnel model.
    """
    gross_margin = gross_margin_pct / 100
    annual_sales_cost_usd_k = sales_headcount * sales_rep_fully_loaded_usd_k
    total_sales_marketing_18mo_usd_k = annual_sales_cost_usd_k * 1.5 + marketing_budget_usd_k

    if new_customers_18mo > 0:
        cac_usd_k = round(total_sales_marketing_18mo_usd_k / new_customers_18mo, 1)
    else:
        cac_usd_k = None

    # LTV = ACV × gross_margin / churn_rate  (assumes constant ACV, no expansion)
    ltv_usd_k = round(acv_usd_k * gross_margin / annual_churn_rate, 1) if annual_churn_rate > 0 else None

    ltv_cac = round(ltv_usd_k / cac_usd_k, 1) if (ltv_usd_k and cac_usd_k and cac_usd_k > 0) else None

    # Payback period = CAC / (ACV × gross_margin / 12 months)
    monthly_gm_per_customer = acv_usd_k * gross_margin / 12
    payback_months = round(cac_usd_k / monthly_gm_per_customer, 1) if (
        cac_usd_k and monthly_gm_per_customer > 0) else None

    return {
        "acv_usd_k": acv_usd_k,
        "gross_margin_pct": gross_margin_pct,
        "annual_churn_rate_pct": annual_churn_rate * 100,
        "cac_usd_k": cac_usd_k,
        "ltv_usd_k": ltv_usd_k,
        "ltv_cac_ratio": ltv_cac,
        "payback_period_months": payback_months,
        "total_sales_marketing_18mo_usd_k": round(total_sales_marketing_18mo_usd_k, 1),
        "new_customers_target_18mo": new_customers_18mo,
        "benchmark_ltv_cac_target": "3x (minimum), 10x+ (excellent for enterprise B2B)",
        "note": "TODO: Adjust churn rate based on your customer retention analysis",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: SALES FUNNEL MODEL
# ─────────────────────────────────────────────────────────────────────────────

def build_sales_funnel(
    target_accounts: int = 100,          # ABM target account list size
    awareness_rate: float = 0.40,        # % of target accounts reached
    interest_rate: float = 0.20,         # % of aware accounts → engaged
    poc_rate: float = 0.30,              # % of interested accounts → POC
    close_rate: float = 0.35,            # % of POC → closed won
    acv_usd_k: float = 150.0,
    sales_cycle_months: float = 12.0,
) -> dict:
    """
    Build a sales funnel model from target account list to ARR.

    Stages: Awareness → Interest/MQL → SQL → POC → Closed Won

    TODO: Calibrate conversion rates against your current 5-customer data.
    """
    aware_accounts = round(target_accounts * awareness_rate)
    mql = round(aware_accounts * interest_rate)
    sql = round(mql * 0.60)    # SQL = qualified leads (60% of MQLs pass qualification)
    poc = round(sql * poc_rate)
    closed = round(poc * close_rate)
    new_arr = round(closed * acv_usd_k, 1)

    # Monthly deal closure rate (assumes pipeline builds over 18 months)
    deals_per_month = closed / 18 if closed > 0 else 0

    return {
        "target_accounts": target_accounts,
        "funnel_stages": {
            "awareness": {"accounts": aware_accounts, "rate_from_prev_pct": round(awareness_rate * 100, 0)},
            "mql": {"accounts": mql, "rate_from_prev_pct": round(interest_rate * 100, 0)},
            "sql": {"accounts": sql, "rate_from_prev_pct": 60},
            "poc": {"accounts": poc, "rate_from_prev_pct": round(poc_rate * 100, 0)},
            "closed_won": {"accounts": closed, "rate_from_prev_pct": round(close_rate * 100, 0)},
        },
        "new_arr_from_funnel_usd_k": new_arr,
        "deals_per_month": round(deals_per_month, 2),
        "total_arr_with_existing_usd_k": round(COMPANY["current_arr_usd_k"] + new_arr, 1),
        "note": "TODO: Add time-weighted model to spread closures across 18 months vs. end-loaded",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: ARR PROJECTION (18 MONTHS)
# ─────────────────────────────────────────────────────────────────────────────

def project_arr_18_months(
    current_arr_usd_k: float,
    deals_per_month: float,
    acv_usd_k: float,
    monthly_churn_rate: float = 0.008,   # ~10% annual / 12
    sales_cycle_months: float = 12.0,
    ramp_delay_months: float = 3.0,      # months before first deal closes
) -> list:
    """
    Project ARR for each of 18 months.

    Assumes:
    - No deals close in first ramp_delay_months months (pipeline build)
    - After ramp, deals_per_month close each month
    - Existing ARR churns at monthly_churn_rate

    TODO: Build a more sophisticated model with:
          - Cohort-based expansion (usage-based pricing grows with customer adoption)
          - Seasonality (Q4 budget cycles tend to close more enterprise deals)
    """
    arr = current_arr_usd_k
    monthly_arr = []

    for month in range(1, 19):
        # Churn from existing base
        churn = arr * monthly_churn_rate

        # New ARR from deal closures (after ramp period)
        if month > ramp_delay_months:
            new_deals_this_month = deals_per_month
        else:
            new_deals_this_month = 0

        new_arr = new_deals_this_month * acv_usd_k
        arr = max(arr - churn + new_arr, 0)

        monthly_arr.append({
            "month": month,
            "arr_usd_k": round(arr, 1),
            "new_arr_this_month_usd_k": round(new_arr, 1),
            "churn_this_month_usd_k": round(churn, 1),
        })

    return monthly_arr


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: CHANNEL BUDGET ALLOCATION
# ─────────────────────────────────────────────────────────────────────────────

def allocate_channel_budget(total_budget_usd_k: float = 500.0) -> dict:
    """
    Allocate the $500K marketing budget across channels.

    TODO: Replace these placeholder allocations with your strategy rationale.
    Each channel should have an expected lead count and pipeline contribution.
    """
    # Placeholder allocation — adjust based on your GTM strategy
    channels = {
        "outbound_direct_sales_tools": {
            "budget_usd_k": None,     # TODO: set (recommended: $50-80K for tools/data)
            "expected_leads": None,   # TODO: estimate
            "rationale": "TODO: LinkedIn Sales Navigator, intent data, outreach tools",
        },
        "conferences_and_events": {
            "budget_usd_k": None,     # TODO: set (recommended: $100-150K for 2-3 key conferences)
            "expected_leads": None,
            "rationale": "TODO: Modex, Gartner SC&O Summit, Council of Supply Chain Management",
        },
        "content_and_thought_leadership": {
            "budget_usd_k": None,     # TODO: set (recommended: $75-100K)
            "expected_leads": None,
            "rationale": "TODO: Case studies, ROI calculators, analyst briefs (Gartner, Forrester)",
        },
        "account_based_marketing_digital": {
            "budget_usd_k": None,     # TODO: set (recommended: $50-75K)
            "expected_leads": None,
            "rationale": "TODO: LinkedIn targeted ads to ICP personas at target account list",
        },
        "partner_channel_development": {
            "budget_usd_k": None,     # TODO: set (recommended: $50K)
            "expected_leads": None,
            "rationale": "TODO: SI partners (Accenture, Deloitte supply chain practice), AWS/Azure marketplace",
        },
        "reserve_and_testing": {
            "budget_usd_k": None,     # TODO: 10% reserve
            "expected_leads": None,
            "rationale": "Experimental channels and budget contingency",
        },
    }

    return {
        "total_budget_usd_k": total_budget_usd_k,
        "channels": channels,
        "note": "TODO: Fill in all budget_usd_k values (must sum to total_budget_usd_k) "
                "and estimate expected_leads for each channel",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P4 LaunchPad — GTM Strategy Analysis Scaffold"
    )
    parser.add_argument("--output", default="analysis.json",
                        help="Output path for analysis JSON (default: analysis.json)")
    parser.add_argument("--acv-k", type=float, default=150.0,
                        help="Average contract value in $K (default: 150)")
    parser.add_argument("--win-rate", type=float, default=0.25,
                        help="Sales win rate 0–1 (default: 0.25)")
    parser.add_argument("--sales-cycle-months", type=float, default=12.0,
                        help="Average sales cycle months (default: 12)")
    parser.add_argument("--series-b-target-m", type=float, default=8.0,
                        help="ARR target for Series B raise in $M (default: 8)")
    parser.add_argument("--target-accounts", type=int, default=100,
                        help="ABM target account list size (default: 100)")

    args = parser.parse_args()

    print(f"[MBA-P4] LaunchPad GTM Analysis — QuantumLeap")
    print(f"  ACV: ${args.acv_k}K  |  Win rate: {args.win_rate*100:.0f}%  "
          f"|  Sales cycle: {args.sales_cycle_months} months")
    print(f"  Series B target: ${args.series_b_target_m}M ARR")

    # 1. Market sizing
    print("\n[1/5] Market sizing (TAM/SAM/SOM)...")
    market = calculate_market_sizing(
        acv_usd_k=args.acv_k,
        win_rate=args.win_rate,
        sales_cycle_months=args.sales_cycle_months,
        sales_reps=COMPANY["employees"]["sales"],
    )
    print(f"  TAM: ${market['tam_usd_b']}B  |  SAM: ${market['sam_usd_b']}B  "
          f"|  SOM (18mo): ${market['som_recommended_18month_usd_m']}M")

    # 2. CAC / LTV
    print("[2/5] CAC / LTV analysis...")
    new_customers = market["total_closed_deals_18mo"]
    cac_ltv = calculate_cac_ltv(
        acv_usd_k=args.acv_k,
        new_customers_18mo=max(new_customers, 1),
        marketing_budget_usd_k=COMPANY["marketing_budget_usd_k"],
    )
    print(f"  CAC: ${cac_ltv['cac_usd_k']}K  |  LTV: ${cac_ltv['ltv_usd_k']}K  "
          f"|  LTV/CAC: {cac_ltv['ltv_cac_ratio']}x  "
          f"|  Payback: {cac_ltv['payback_period_months']} months")

    # 3. Sales funnel
    print("[3/5] Building sales funnel model...")
    funnel = build_sales_funnel(
        target_accounts=args.target_accounts,
        acv_usd_k=args.acv_k,
        close_rate=args.win_rate,
        sales_cycle_months=args.sales_cycle_months,
    )
    print(f"  Target accounts: {funnel['target_accounts']}  "
          f"Closed won: {funnel['funnel_stages']['closed_won']['accounts']}  "
          f"New ARR: ${funnel['new_arr_from_funnel_usd_k']}K")

    # 4. ARR projection
    print("[4/5] Projecting 18-month ARR...")
    arr_proj = project_arr_18_months(
        current_arr_usd_k=COMPANY["current_arr_usd_k"],
        deals_per_month=funnel["deals_per_month"],
        acv_usd_k=args.acv_k,
        sales_cycle_months=args.sales_cycle_months,
    )
    final_arr_usd_m = arr_proj[-1]["arr_usd_k"] / 1_000
    series_b_achieved = final_arr_usd_m >= args.series_b_target_m
    print(f"  Month 18 ARR: ${final_arr_usd_m:.2f}M  |  "
          f"Series B target (${args.series_b_target_m}M): {'ACHIEVED' if series_b_achieved else 'NOT ACHIEVED'}")

    # 5. Channel budget
    print("[5/5] Channel budget allocation (placeholder)...")
    channels = allocate_channel_budget(COMPANY["marketing_budget_usd_k"])

    # Assemble
    analysis = {
        "problem": "MBA-P4: LaunchPad",
        "company": COMPANY["name"],
        "parameters": {
            "acv_usd_k": args.acv_k,
            "win_rate": args.win_rate,
            "sales_cycle_months": args.sales_cycle_months,
            "series_b_target_arr_usd_m": args.series_b_target_m,
        },
        "market_sizing": market,
        "cac_ltv_analysis": cac_ltv,
        "sales_funnel": funnel,
        "arr_projection_18_months": arr_proj,
        "channel_budget": channels,
        "summary": {
            "som_18month_usd_m": market["som_recommended_18month_usd_m"],
            "total_closed_deals_18mo": market["total_closed_deals_18mo"],
            "month_18_arr_usd_m": round(final_arr_usd_m, 2),
            "series_b_target_usd_m": args.series_b_target_m,
            "series_b_on_track": series_b_achieved,
            "ltv_cac_ratio": cac_ltv["ltv_cac_ratio"],
            "next_steps": [
                "TODO: Fill in channel budget allocations in allocate_channel_budget()",
                "TODO: Build positioning statement and competitive matrix",
                "TODO: Define MEDDIC-based sales playbook stages",
                "TODO: Create 90-day action plan with specific owners and metrics",
                "TODO: Validate ICP criteria against existing 5 customers",
            ],
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
