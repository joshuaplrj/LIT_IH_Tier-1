"""
MBA-P5: DealArchitect — M&A Valuation Analysis Scaffold
=========================================================
CloudStack Inc. ($5B) evaluating acquisition of DataFlow Analytics ($200M ARR).
Build DCF, comps analysis, synergy model, and integration plan.

Data directory (default): prerequisites/MBA/MBA-P5/

Usage:
    python starter.py [--data-dir <path>] [--output analysis.json]
                      [--wacc <float>] [--tgr <float>]

Outputs:
    analysis.json  — DCF valuation, comps, precedents, synergy model
"""

import argparse
import csv
import json
import math
import os


# ─────────────────────────────────────────────────────────────────────────────
# DEAL CONSTANTS  (problem parameters)
# ─────────────────────────────────────────────────────────────────────────────
ACQUIRER = {
    "name": "CloudStack Inc.",
    "revenue_usd_m": 5_000,
    "revenue_growth_pct": 12,
    "ebitda_margin_pct": 30,
    "market_cap_usd_m": 50_000,
    "cash_usd_m": 1_800,
    "debt_usd_m": 2_000,
    "strategic_rationale": "Needs analytics/BI to compete with Snowflake and Databricks",
}

TARGET = {
    "name": "DataFlow Analytics",
    "revenue_usd_m": 200,
    "revenue_growth_pct": 80,
    "gross_margin_pct": 75,
    "ebitda_usd_m": -50,
    "arr_usd_m": 180,
    "ndr_pct": 140,
    "customers": 500,
    "avg_acv_usd_k": 360,
    "employees": 800,
    "last_round_valuation_usd_m": 2_000,   # Series D
    "cash_usd_m": 120,      # approximate from dcf_template data
    "debt_usd_m": 60,       # approximate (venture debt)
    "net_debt_usd_m": -60,  # net cash positive
}

COMPETITION = ["Snowflake", "Google"]  # reportedly also interested


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
# SECTION 1: DCF VALUATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_dcf(dcf_rows: list, wacc: float, tgr: float) -> dict:
    """
    Compute enterprise value from the DCF template.

    Reads dcf_template.csv (pre-built projections for FY2025–FY2035).
    Sums PV of FCFs and PV of terminal value.

    Parameters
    ----------
    dcf_rows : list of dicts from dcf_template.csv
    wacc     : weighted average cost of capital (e.g., 0.12)
    tgr      : terminal growth rate (e.g., 0.03)

    Returns
    -------
    dict with enterprise_value_usd_m, equity_value_usd_m, and components
    """
    if not dcf_rows:
        return {
            "error": "DCF template not loaded",
            "note": "Run generate_mba_p5.py to create dcf_template.csv",
        }

    pv_fcf_sum = 0.0
    pv_tv = 0.0
    projection_rows = []
    terminal_row = None

    for row in dcf_rows:
        year = row.get("year", "")
        if str(year) == "Terminal Value":
            terminal_row = row
            continue

        try:
            yr = int(year)
            ufcf = float(row.get("unlevered_fcf_usd_m", 0))
            t = yr - 2024    # projection year (2025=1, 2026=2, etc.)
            # Recompute discount factor with provided WACC
            df = 1 / (1 + wacc) ** t
            pv = round(ufcf * df, 1)
            pv_fcf_sum += pv

            projection_rows.append({
                "year": yr,
                "unlevered_fcf_usd_m": round(ufcf, 1),
                "discount_factor": round(df, 6),
                "pv_fcf_usd_m": pv,
            })
        except (ValueError, TypeError):
            continue

    # Terminal value (Gordon Growth Model)
    # TV = last_ufcf × (1 + tgr) / (wacc - tgr)
    if projection_rows:
        last_ufcf = projection_rows[-1]["unlevered_fcf_usd_m"]
        n = len(projection_rows)
        if wacc > tgr:
            tv = round(last_ufcf * (1 + tgr) / (wacc - tgr), 1)
            df_tv = round(1 / (1 + wacc) ** n, 6)
            pv_tv = round(tv * df_tv, 1)
        else:
            tv = None
            pv_tv = None
    else:
        tv = None
        pv_tv = None

    enterprise_value = round(pv_fcf_sum + (pv_tv or 0), 1)
    # Equity value = EV - net debt (DataFlow has net cash, so we ADD the net cash)
    equity_value = round(enterprise_value - TARGET["net_debt_usd_m"], 1)

    return {
        "wacc_pct": round(wacc * 100, 1),
        "terminal_growth_rate_pct": round(tgr * 100, 1),
        "pv_fcf_sum_usd_m": round(pv_fcf_sum, 1),
        "terminal_value_usd_m": tv,
        "pv_terminal_value_usd_m": pv_tv,
        "enterprise_value_usd_m": enterprise_value,
        "net_debt_usd_m": TARGET["net_debt_usd_m"],
        "equity_value_usd_m": equity_value,
        "n_projection_years": len(projection_rows),
        "terminal_value_pct_of_ev": round(pv_tv / enterprise_value * 100, 1) if (pv_tv and enterprise_value > 0) else None,
        "projection_detail": projection_rows,
    }


def compute_dcf_sensitivity(dcf_rows: list) -> dict:
    """
    3x3 sensitivity table: WACC (10%, 12%, 14%) × TGR (2%, 3%, 4%).
    Returns a nested dict: {wacc_pct: {tgr_pct: equity_value_usd_m}}
    """
    wacc_vals = [0.10, 0.12, 0.14]
    tgr_vals  = [0.02, 0.03, 0.04]
    table = {}

    for wacc in wacc_vals:
        row_key = f"wacc_{int(wacc*100)}pct"
        table[row_key] = {}
        for tgr in tgr_vals:
            result = compute_dcf(dcf_rows, wacc, tgr)
            col_key = f"tgr_{int(tgr*100)}pct"
            table[row_key][col_key] = result.get("equity_value_usd_m")

    return {
        "description": "Equity Value ($M) sensitivity to WACC and Terminal Growth Rate",
        "axes": {
            "rows": "WACC (%)",
            "columns": "Terminal Growth Rate (%)",
        },
        "table": table,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: COMPARABLE COMPANY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def comps_analysis(comps_rows: list) -> dict:
    """
    Apply comparable company multiples to DataFlow.

    TODO: Select the most relevant comps (filter by growth rate, business model).
    Apply appropriate discounts for private company / smaller scale.
    """
    if not comps_rows:
        return {"error": "Comparable companies data not loaded"}

    ev_rev_multiples = []
    selected_comps = []

    for row in comps_rows:
        try:
            ev_rev = row.get("ev_revenue_multiple", "N/M")
            rev_grw = row.get("revenue_growth_pct", "0")
            if ev_rev in ("N/M", "", "N/A"):
                continue
            ev_rev_f = float(ev_rev)
            rev_grw_f = float(rev_grw)

            # Filter: high-growth analytics comps (growth > 10%)
            if rev_grw_f > 10:
                ev_rev_multiples.append(ev_rev_f)
                selected_comps.append({
                    "company": row.get("company_name"),
                    "ev_revenue_multiple": ev_rev_f,
                    "revenue_growth_pct": rev_grw_f,
                    "gross_margin_pct": row.get("gross_margin_pct"),
                    "ndr_pct": row.get("ndr_pct"),
                })
        except (ValueError, TypeError):
            continue

    if not ev_rev_multiples:
        return {"error": "No valid EV/Revenue multiples found in comps data"}

    n = len(ev_rev_multiples)
    median_mult = sorted(ev_rev_multiples)[n // 2]
    mean_mult = sum(ev_rev_multiples) / n

    # Apply 20% private company discount (illiquidity)
    private_discount = 0.20
    applied_mult = round(median_mult * (1 - private_discount), 1)

    # Apply to DataFlow's forward ARR ($180M)
    implied_ev = round(applied_mult * TARGET["arr_usd_m"], 1)
    implied_equity = round(implied_ev - TARGET["net_debt_usd_m"], 1)

    return {
        "selected_comps_count": len(selected_comps),
        "selected_comps": selected_comps,
        "median_ev_revenue_multiple": round(median_mult, 1),
        "mean_ev_revenue_multiple": round(mean_mult, 1),
        "private_discount_applied_pct": private_discount * 100,
        "applied_multiple": applied_mult,
        "applied_to": f"DataFlow ARR ${TARGET['arr_usd_m']}M",
        "implied_ev_usd_m": implied_ev,
        "implied_equity_value_usd_m": implied_equity,
        "note": "TODO: Adjust comp selection and private discount. Also apply EV/NTM ARR if available. "
                "DataFlow's 140% NDR and 80% growth warrant a premium to median.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: PRECEDENT TRANSACTION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def precedent_analysis(txn_rows: list) -> dict:
    """
    Apply precedent transaction multiples to DataFlow.
    Transactions include a control premium vs. trading comps.
    """
    if not txn_rows:
        return {"error": "Precedent transactions data not loaded"}

    multiples = []
    transactions = []

    for row in txn_rows:
        try:
            mult = float(row.get("ev_revenue_multiple", 0))
            if mult > 0:
                multiples.append(mult)
                transactions.append({
                    "deal": f"{row.get('acquirer')} / {row.get('target')}",
                    "date": row.get("deal_date"),
                    "ev_revenue_multiple": mult,
                    "deal_value_usd_m": row.get("deal_value_usd_m"),
                    "strategic_rationale": row.get("strategic_rationale"),
                })
        except (ValueError, TypeError):
            continue

    if not multiples:
        return {"error": "No valid multiples in precedent transactions"}

    median_mult = sorted(multiples)[len(multiples) // 2]
    applied_mult = round(median_mult, 1)

    # Apply to DataFlow revenue
    implied_ev = round(applied_mult * TARGET["revenue_usd_m"], 1)
    implied_equity = round(implied_ev - TARGET["net_debt_usd_m"], 1)

    # Valuation range: low (min multiple) to high (max multiple)
    low_ev = round(min(multiples) * TARGET["revenue_usd_m"], 1)
    high_ev = round(max(multiples) * TARGET["revenue_usd_m"], 1)

    return {
        "transactions_used": len(transactions),
        "transactions": transactions,
        "multiple_range": f"{round(min(multiples), 1)}x – {round(max(multiples), 1)}x",
        "median_ev_revenue_multiple": round(median_mult, 1),
        "applied_multiple": applied_mult,
        "implied_ev_usd_m": implied_ev,
        "implied_equity_value_usd_m": implied_equity,
        "ev_range_usd_m": {"low": low_ev, "high": high_ev},
        "note": "TODO: Consider that recent comps are from 2019–2021 bull market. "
                "Apply a macro adjustment if current multiples are lower. "
                "Control premium vs. public comps typically 20–40%.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: SYNERGY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def synergy_model(
    cloudstack_customers: int = 5_000,    # estimated enterprise customers
    cross_sell_rate: float = 0.05,        # % of CloudStack customers buying DataFlow
    dataflow_acv_usd_k: float = 360.0,
    cost_synergy_pct_of_target_opex: float = 0.15,  # 15% of DataFlow OpEx
    dataflow_opex_usd_m: float = 250.0,   # DataFlow OpEx (revenue - EBITDA)
    wacc: float = 0.12,
    synergy_years: int = 5,
) -> dict:
    """
    Model revenue and cost synergies from the CloudStack/DataFlow deal.

    Revenue synergies: Cross-sell DataFlow to CloudStack's installed base.
    Cost synergies: Eliminate redundant S&M, R&D overlap, and leverage CloudStack infra.

    TODO: Quantify each synergy bucket separately.
    """
    # Revenue synergies (Year 3 run-rate after ramp)
    new_customers_year3 = cloudstack_customers * cross_sell_rate
    annual_rev_synergy = new_customers_year3 * dataflow_acv_usd_k / 1_000  # $M
    rev_synergy_ramp = [annual_rev_synergy * r for r in [0.2, 0.5, 1.0, 1.0, 1.0]]

    # Cost synergies (Year 2 run-rate after integration)
    annual_cost_synergy = dataflow_opex_usd_m * cost_synergy_pct_of_target_opex
    cost_synergy_ramp = [annual_cost_synergy * r for r in [0.3, 0.8, 1.0, 1.0, 1.0]]

    # NPV of synergies (discounted at WACC, 5 years)
    def synergy_npv(annual_synergies):
        return sum(s / (1 + wacc) ** (t + 1) for t, s in enumerate(annual_synergies))

    gross_margin = TARGET["gross_margin_pct"] / 100
    rev_syn_npv = round(synergy_npv([s * gross_margin for s in rev_synergy_ramp]), 1)
    cost_syn_npv = round(synergy_npv(cost_synergy_ramp), 1)
    total_syn_npv = round(rev_syn_npv + cost_syn_npv, 1)

    # Three scenarios (conservative/base/optimistic)
    scenarios = {}
    for scenario, factor in [("conservative", 0.50), ("base", 0.75), ("optimistic", 1.00)]:
        scenarios[scenario] = {
            "revenue_synergy_yr3_run_rate_usd_m": round(annual_rev_synergy * factor, 1),
            "cost_synergy_yr2_run_rate_usd_m": round(annual_cost_synergy * factor, 1),
            "total_synergy_npv_usd_m": round(total_syn_npv * factor, 1),
            "synergy_share_to_seller_pct": 60,   # TODO: adjust per negotiation
            "value_to_cloudstack_usd_m": round(total_syn_npv * factor * 0.40, 1),
        }

    return {
        "revenue_synergy_assumptions": {
            "cloudstack_enterprise_customers": cloudstack_customers,
            "cross_sell_conversion_rate_pct": cross_sell_rate * 100,
            "dataflow_acv_usd_k": dataflow_acv_usd_k,
            "year3_run_rate_new_customers": round(new_customers_year3),
            "year3_annual_revenue_synergy_usd_m": round(annual_rev_synergy, 1),
        },
        "cost_synergy_assumptions": {
            "target_opex_usd_m": dataflow_opex_usd_m,
            "synergy_pct_of_opex": cost_synergy_pct_of_target_opex * 100,
            "annual_cost_synergy_usd_m": round(annual_cost_synergy, 1),
            "buckets": ["Redundant S&M", "Overlapping G&A", "Cloud infrastructure consolidation"],
        },
        "scenarios": scenarios,
        "note": "TODO: Validate cross_sell_rate with CloudStack's existing data/analytics customer penetration. "
                "Cost synergies typically realised over 18–24 months, not immediately. "
                "Include one-time restructuring costs (redundancy, system migration).",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: OFFER PRICE RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def recommend_offer_price(
    dcf_equity_value: float,
    comps_equity_value: float,
    precedent_equity_value: float,
    synergy_npv_base: float,
    synergy_share_to_seller: float = 0.60,
    last_round_valuation: float = 2_000.0,
) -> dict:
    """
    Triangulate valuation and recommend offer price range.

    Walk-away price = max(comps, precedents, last round valuation)
    Initial offer = min(walk-away, DCF + synergies shared with seller)

    TODO: Incorporate competitive dynamics (Snowflake and Google also interested).
    """
    # Intrinsic value = DCF standalone
    intrinsic = dcf_equity_value

    # Value with synergies shared (60% to seller)
    with_synergies = round(dcf_equity_value + synergy_npv_base * synergy_share_to_seller, 1)

    # Market anchor: max of comps and precedents
    market_anchor = max(comps_equity_value, precedent_equity_value, last_round_valuation)

    # Recommended offer: between intrinsic+synergies and market anchor
    initial_offer = round((with_synergies + market_anchor) / 2, 0)
    walk_away = round(market_anchor * 1.15, 0)  # 15% above market anchor

    return {
        "standalone_dcf_equity_value_usd_m": intrinsic,
        "dcf_plus_synergies_usd_m": with_synergies,
        "comps_implied_equity_usd_m": comps_equity_value,
        "precedents_implied_equity_usd_m": precedent_equity_value,
        "last_round_valuation_usd_m": last_round_valuation,
        "market_anchor_usd_m": market_anchor,
        "recommended_initial_offer_usd_m": initial_offer,
        "walk_away_price_usd_m": walk_away,
        "valuation_range": {
            "low": round(min(intrinsic, comps_equity_value) * 0.9, 0),
            "midpoint": round((intrinsic + market_anchor) / 2, 0),
            "high": walk_away,
        },
        "note": "TODO: Adjust for competitive bid (Snowflake/Google interest may push price up 10–20%). "
                "Consider earnout structure to reduce upfront payment risk.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P5 DealArchitect — M&A Valuation Scaffold"
    )
    parser.add_argument(
        "--data-dir",
        default=r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P5",
        help="Directory containing M&A data files",
    )
    parser.add_argument("--output", default="analysis.json",
                        help="Output path for analysis JSON (default: analysis.json)")
    parser.add_argument("--wacc", type=float, default=0.12,
                        help="WACC assumption (default: 0.12 = 12%%)")
    parser.add_argument("--tgr", type=float, default=0.03,
                        help="Terminal growth rate (default: 0.03 = 3%%)")

    args = parser.parse_args()

    print(f"[MBA-P5] DealArchitect — CloudStack / DataFlow M&A Analysis")
    print(f"  Data directory: {args.data_dir}")
    print(f"  WACC: {args.wacc*100:.1f}%  |  TGR: {args.tgr*100:.1f}%")

    # Load data
    print("\n[1/6] Loading data files...")
    dcf_rows = load_csv(os.path.join(args.data_dir, "dcf_template.csv"))
    comps_rows = load_csv(os.path.join(args.data_dir, "comparable_companies.csv"))
    txn_rows = load_csv(os.path.join(args.data_dir, "precedent_transactions.csv"))
    cloudstack_rows = load_csv(os.path.join(args.data_dir, "cloudstack_financials.csv"))
    dataflow_rows = load_csv(os.path.join(args.data_dir, "dataflow_financials.csv"))
    print(f"  DCF rows: {len(dcf_rows)}  Comps: {len(comps_rows)}  Transactions: {len(txn_rows)}")

    # DCF valuation
    print("[2/6] Computing DCF valuation...")
    dcf = compute_dcf(dcf_rows, wacc=args.wacc, tgr=args.tgr)
    print(f"  Enterprise Value: ${dcf.get('enterprise_value_usd_m', 'N/A')}M  "
          f"|  Equity Value: ${dcf.get('equity_value_usd_m', 'N/A')}M  "
          f"|  TV %: {dcf.get('terminal_value_pct_of_ev', 'N/A')}%")

    # Sensitivity table
    print("[3/6] Building DCF sensitivity table...")
    sensitivity = compute_dcf_sensitivity(dcf_rows)

    # Comps analysis
    print("[4/6] Comparable company analysis...")
    comps = comps_analysis(comps_rows)
    print(f"  Median EV/Rev: {comps.get('median_ev_revenue_multiple', 'N/A')}x  "
          f"|  Implied equity: ${comps.get('implied_equity_value_usd_m', 'N/A')}M")

    # Precedent transactions
    print("[5/6] Precedent transaction analysis...")
    precedents = precedent_analysis(txn_rows)
    print(f"  Median multiple: {precedents.get('median_ev_revenue_multiple', 'N/A')}x  "
          f"|  Implied equity: ${precedents.get('implied_equity_value_usd_m', 'N/A')}M")

    # Synergy model
    synergies = synergy_model(wacc=args.wacc)
    base_synergy_npv = synergies["scenarios"]["base"]["total_synergy_npv_usd_m"]
    print(f"  Synergy NPV (base): ${base_synergy_npv}M")

    # Offer price recommendation
    print("[6/6] Offer price recommendation...")
    offer = recommend_offer_price(
        dcf_equity_value=dcf.get("equity_value_usd_m", 1_500),
        comps_equity_value=comps.get("implied_equity_value_usd_m", 2_000),
        precedent_equity_value=precedents.get("implied_equity_value_usd_m", 2_500),
        synergy_npv_base=base_synergy_npv,
    )
    print(f"  Recommended offer: ${offer['recommended_initial_offer_usd_m']}M  "
          f"|  Walk-away: ${offer['walk_away_price_usd_m']}M")

    # Assemble output
    analysis = {
        "problem": "MBA-P5: DealArchitect",
        "deal": f"{ACQUIRER['name']} / {TARGET['name']}",
        "parameters": {"wacc_pct": args.wacc * 100, "tgr_pct": args.tgr * 100},
        "acquirer": ACQUIRER,
        "target": TARGET,
        "dcf_valuation": dcf,
        "dcf_sensitivity_table": sensitivity,
        "comps_analysis": comps,
        "precedent_analysis": precedents,
        "synergy_analysis": synergies,
        "offer_price_recommendation": offer,
        "summary": {
            "dcf_equity_value_usd_m": dcf.get("equity_value_usd_m"),
            "comps_equity_value_usd_m": comps.get("implied_equity_value_usd_m"),
            "precedents_equity_value_usd_m": precedents.get("implied_equity_value_usd_m"),
            "base_synergy_npv_usd_m": base_synergy_npv,
            "recommended_offer_usd_m": offer["recommended_initial_offer_usd_m"],
            "walk_away_price_usd_m": offer["walk_away_price_usd_m"],
            "next_steps": [
                "TODO: Refine WACC using CAPM (risk-free rate + beta × equity risk premium)",
                "TODO: Adjust comp selection to only high-growth analytics SaaS",
                "TODO: Model synergies by bucket (S&M, R&D, infra) with timing",
                "TODO: Design earnout structure tied to DataFlow ARR milestones",
                "TODO: Build 100-day integration plan with org design decisions",
                "TODO: Write board recommendation memo (2 pages)",
            ],
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
