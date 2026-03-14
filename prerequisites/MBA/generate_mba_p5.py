"""
MBA-P5: DealArchitect — M&A Financial Data Generator
Generates cloudstack_financials.csv, dataflow_financials.csv,
comparable_companies.csv, precedent_transactions.csv,
dcf_template.csv, README.md
"""

import csv
import os
import math

OUT_DIR = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P5"
os.makedirs(OUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  cloudstack_financials.csv  (FY2017 – FY2024)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_cloudstack():
    """
    Enterprise software company.
    FY2024: Revenue=5000, Growth=12%, EBITDA margin=30%, Net Income=900,
            Debt=2000, Cash=1800
    Work backwards with consistent ~12% growth ± noise.
    """

    # Anchor FY2024 values
    GROWTH_BASE   = 0.12
    GROSS_MARGIN  = 0.68
    EBITDA_MARGIN = 0.30
    EBIT_MARGIN   = 0.22
    NI_MARGIN     = 0.18
    RD_PCT        = 0.15     # R&D as % of revenue
    CAPEX_PCT     = 0.04
    FCF_PCT       = 0.16     # FCF as % of revenue
    SHARES        = 320.0    # millions
    PE_RATIO      = 28.0

    # Build from FY2017 forward
    rev_2024 = 5000.0
    years    = list(range(2017, 2025))
    n        = len(years)   # 8

    # Back-calculate revenue for each year
    # FY2024 = 5000; each prior year = current / 1.12 * (1 ± small noise)
    noise_seeds = [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01, 0.0]
    revenues = [0.0] * n
    revenues[n-1] = rev_2024
    for i in range(n-2, -1, -1):
        g = GROWTH_BASE + noise_seeds[i]
        revenues[i] = revenues[i+1] / (1.0 + g)

    # Debt schedule: decreasing from higher level in 2017
    debts  = [3800, 3600, 3300, 3000, 2800, 2600, 2200, 2000]
    cashes = [400,  500,  650,  800,  1000, 1200, 1500, 1800]

    path = os.path.join(OUT_DIR, "cloudstack_financials.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fiscal_year", "revenue_usd_m", "revenue_growth_pct",
                    "gross_profit_usd_m", "gross_margin_pct",
                    "ebitda_usd_m", "ebitda_margin_pct",
                    "ebit_usd_m", "net_income_usd_m", "eps",
                    "revenue_arr_usd_m",
                    "r&d_spend_usd_m", "capex_usd_m", "fcf_usd_m",
                    "total_debt_usd_m", "cash_usd_m",
                    "shares_outstanding_m", "stock_price_eoy"])

        for i, yr in enumerate(years):
            rev  = round(revenues[i], 1)
            if i == 0:
                grw = "N/A"
            else:
                grw = round((revenues[i] / revenues[i-1] - 1) * 100, 1)

            gp   = round(rev * GROSS_MARGIN, 1)
            gm   = round(GROSS_MARGIN * 100, 1)
            ebitda = round(rev * EBITDA_MARGIN, 1)
            ebitda_m = round(EBITDA_MARGIN * 100, 1)
            ebit = round(rev * EBIT_MARGIN, 1)
            ni   = round(rev * NI_MARGIN, 1)
            eps  = round(ni / SHARES, 2)
            arr  = round(rev * 0.85, 1)      # ARR ~ 85 % of revenue (subscription)
            rd   = round(rev * RD_PCT, 1)
            capex = round(rev * CAPEX_PCT, 1)
            fcf  = round(rev * FCF_PCT, 1)
            debt = float(debts[i])
            cash = float(cashes[i])
            price = round(eps * PE_RATIO * (1 + 0.05 * (i - (n-1))), 2)

            w.writerow([yr, rev, grw, gp, gm, ebitda, ebitda_m,
                        ebit, ni, eps, arr, rd, capex, fcf,
                        debt, cash, SHARES, price])

    print(f"  cloudstack_financials.csv → {len(years)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  dataflow_financials.csv  (FY2020 – FY2024)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_dataflow():
    """
    Fast-growing analytics startup.
    FY2024: Revenue=200 (+80%), ARR=180, GM=75%, EBITDA=-50M, Customers=500, NDR=140%
    FY2023: Revenue=111 (+95%), ARR=100
    Work backwards to FY2020.
    """

    # Hard-coded anchor points aligned to spec
    data = [
        # yr, rev, arr, gm_pct, ebitda, customers, ndr, acv_k
        (2024, 200.0,  180.0, 75.0,  -50.0,  500, 140, 400),
        (2023, 111.0,  100.0, 72.0,  -65.0,  280, 135, 395),
        (2022,  57.0,   50.0, 70.0,  -55.0,  145, 128, 393),
        (2021,  20.0,   17.0, 65.0,  -35.0,   62, 120, 322),
        (2020,   5.0,    4.0, 55.0,  -15.0,   15, 108, 267),
    ]

    SHARES = 45.0      # millions (private → share count estimated)

    path = os.path.join(OUT_DIR, "dataflow_financials.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["fiscal_year", "revenue_usd_m", "revenue_growth_pct",
                  "gross_profit_usd_m", "gross_margin_pct",
                  "ebitda_usd_m", "ebitda_margin_pct",
                  "ebit_usd_m", "net_income_usd_m", "eps",
                  "revenue_arr_usd_m",
                  "r&d_spend_usd_m", "capex_usd_m", "fcf_usd_m",
                  "total_debt_usd_m", "cash_usd_m",
                  "shares_outstanding_m", "stock_price_eoy",
                  "arr_usd_m", "ndr_pct", "customers",
                  "average_acv_usd_k", "cac_usd_k", "ltv_usd_k",
                  "rule_of_40_score"]
        w.writerow(header)

        prev_rev = None
        for yr, rev, arr, gm_pct, ebitda, customers, ndr, acv_k in data:
            grw = "N/A" if prev_rev is None else round((rev / prev_rev - 1) * 100, 1)
            prev_rev = rev

            gp      = round(rev * gm_pct / 100, 1)
            ebitda_m = round(ebitda / rev * 100, 1)
            ebit    = round(ebitda - rev * 0.10, 1)   # D&A ~10% of rev
            ni      = round(ebit - rev * 0.03, 1)     # interest + taxes est
            eps     = round(ni / SHARES, 2)
            rd      = round(rev * 0.40, 1)             # heavy R&D investment
            capex   = round(rev * 0.05, 1)
            fcf     = round(ebitda - capex, 1)
            debt    = round(rev * 0.30, 1)             # venture debt
            cash    = round(rev * 0.50 + 20, 1)        # cash from fundraises
            price   = "N/A"                            # private company

            cac     = round(acv_k * 0.80, 1)
            ltv     = round(acv_k * (ndr / 100) * 5, 1)

            # Rule of 40: revenue growth % + EBITDA margin %
            if grw == "N/A":
                r40 = round(ebitda_m, 1)
            else:
                r40 = round(float(grw) + ebitda_m, 1)

            w.writerow([yr, rev, grw, gp, gm_pct, ebitda, ebitda_m,
                        ebit, ni, eps, arr,
                        rd, capex, fcf, debt, cash, SHARES, price,
                        arr, ndr, customers, acv_k, cac, ltv, r40])

    print(f"  dataflow_financials.csv → {len(data)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  comparable_companies.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_comps():
    comps = [
        # name, ticker, desc, rev, rev_grw, gm, ebitda_m, ev, ev_rev, ev_ebitda, ndr, mktcap
        ("Snowflake",    "SNOW",  "Cloud data platform and analytics",
         2800, 38, 67, -15, 50000, 17.9, "N/M",   130, 43000),
        ("Databricks",   "N/A (Private)", "Unified data analytics and AI platform",
         1500, 50, 72, -10, 28000, 18.7, "N/M",   140, 28000),
        ("Palantir",     "PLTR",  "AI-powered data analytics for enterprise and government",
         2300, 17, 80,  10, 45000, 19.6, 196,     115, 40000),
        ("Tableau",      "Acquired by Salesforce", "Business intelligence and data visualisation",
         1320, 10, 75,  15, 15700, 11.9, 105,     120,  None),
        ("Qlik",         "N/A (Private)", "Data integration and analytics platform",
          900, 12, 70,  18, 3000,   3.3,  18,     110,  3000),
        ("ThoughtSpot",  "N/A (Private)", "AI-powered search and analytics",
          160, 40, 68, -35, 4500,  28.1, "N/M",   135,  4500),
        ("Looker",       "Acquired by Google", "Business intelligence and data exploration platform",
          390, 45, 71, -20, 2600,   6.7, "N/M",   125,  None),
        ("Domo",         "DOMO",  "Cloud business intelligence platform",
          335,  8, 65,  -8, 700,    2.1,  "N/M",  110,   620),
        ("MicroStrategy","MSTR",  "Enterprise analytics and business intelligence",
          490,  5, 77,  12, 3500,   7.1,  59,     105,  3200),
        ("Sisense",      "N/A (Private)", "Embedded analytics and business intelligence",
          200, 20, 70, -12, 1200,   6.0, "N/M",   118,  1200),
    ]

    path = os.path.join(OUT_DIR, "comparable_companies.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_name", "ticker", "description",
                    "revenue_usd_m", "revenue_growth_pct",
                    "gross_margin_pct", "ebitda_margin_pct",
                    "ev_usd_m", "ev_revenue_multiple",
                    "ev_ebitda_multiple", "ndr_pct", "market_cap_usd_m"])
        for c in comps:
            w.writerow(list(c))

    print(f"  comparable_companies.csv → {len(comps)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  precedent_transactions.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_precedent():
    txns = [
        ("2019-06-10", "Salesforce",    "Tableau Software",
         15700, 1070, 14.7, 960, "Expand BI and data visualisation capabilities", "Strategic acquisition"),
        ("2019-06-06", "Google (Alphabet)", "Looker",
         2600,  390,  6.7,  290, "Strengthen Google Cloud data analytics offerings", "Strategic acquisition"),
        ("2019-01-22", "SAP",           "Qualtrics International",
         8000,  400, 20.0,  290, "Add experience management data to SAP's ERP suite", "Strategic acquisition"),
        ("2019-06-03", "Thoma Bravo",   "Qlik Technologies",
         3000,  800,  3.75, 600, "Private equity platform consolidation play in BI", "Private equity buyout"),
        ("2021-03-08", "Salesforce",    "Slack Technologies",
         27700, 902, 30.7,  820, "Collaboration platform to deepen CRM ecosystem", "Strategic acquisition"),
    ]

    path = os.path.join(OUT_DIR, "precedent_transactions.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["deal_date", "acquirer", "target", "deal_value_usd_m",
                    "target_revenue_usd_m", "ev_revenue_multiple",
                    "target_arr_usd_m", "strategic_rationale", "deal_type"])
        for t in txns:
            w.writerow(list(t))

    print(f"  precedent_transactions.csv → {len(txns)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  dcf_template.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_dcf_template():
    """
    DCF template for DataFlow Analytics acquisition valuation.
    Columns: year, revenue_usd_m, revenue_growth_pct, ebitda_margin_pct,
             ebitda_usd_m, d_and_a_usd_m, ebit_usd_m, tax_rate_pct,
             nopat_usd_m, capex_usd_m, change_in_nwc_usd_m,
             unlevered_fcf_usd_m, discount_factor, pv_fcf_usd_m, notes
    Rows FY2025-FY2035 (projection period) + terminal value row
    """

    wacc = 0.12          # 12% WACC assumption
    tgr  = 0.03          # terminal growth rate 3%
    tax  = 0.21          # 21% corporate tax

    # DataFlow FY2024 anchors: Rev=200, growth decelerating from 80% → 15%
    growth_schedule = [0.60, 0.50, 0.40, 0.35, 0.30, 0.25, 0.22, 0.20, 0.18, 0.15, 0.15]
    ebitda_march    = [-0.15, -0.05, 0.05, 0.12, 0.18, 0.22, 0.25, 0.27, 0.28, 0.29, 0.30]
    years = list(range(2025, 2036))

    path = os.path.join(OUT_DIR, "dcf_template.csv")
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "revenue_usd_m", "revenue_growth_pct",
                    "ebitda_margin_pct", "ebitda_usd_m",
                    "d_and_a_usd_m", "ebit_usd_m",
                    "tax_rate_pct", "nopat_usd_m",
                    "capex_usd_m", "change_in_nwc_usd_m",
                    "unlevered_fcf_usd_m",
                    "discount_factor", "pv_fcf_usd_m",
                    "notes"])

        rev = 200.0
        for i, yr in enumerate(years):
            rev = round(rev * (1 + growth_schedule[i]), 1)
            ebitda_m = ebitda_march[i]
            ebitda   = round(rev * ebitda_m, 1)
            dna      = round(rev * 0.06, 1)          # D&A ~ 6% of rev
            ebit     = round(ebitda - dna, 1)
            nopat    = round(ebit * (1 - tax), 1)
            capex    = round(rev * 0.05, 1)
            nwc_chg  = round(rev * 0.02, 1)
            ufcf     = round(nopat + dna - capex - nwc_chg, 1)
            t        = i + 1
            df       = round(1 / (1 + wacc) ** t, 6)
            pv       = round(ufcf * df, 1)

            note = (f"Year {t}: Revenue growth {round(growth_schedule[i]*100,0):.0f}%, "
                    f"EBITDA margin {round(ebitda_m*100,0):.0f}%, "
                    f"WACC={round(wacc*100,0):.0f}%")
            w.writerow([yr, rev, round(growth_schedule[i]*100,1),
                        round(ebitda_m*100,1), ebitda,
                        dna, ebit, round(tax*100,0),
                        nopat, capex, nwc_chg, ufcf,
                        df, pv, note])
            rows_written += 1

        # Terminal value row
        last_rev   = rev
        tv_ufcf    = round(last_rev * 0.30 * (1 - tax), 1)
        tv         = round(tv_ufcf * (1 + tgr) / (wacc - tgr), 1)
        df_tv      = round(1 / (1 + wacc) ** len(years), 6)
        pv_tv      = round(tv * df_tv, 1)
        w.writerow(["Terminal Value", "", "",
                    "", "", "", "", "", "",
                    "", "", tv_ufcf * (1 + tgr),
                    df_tv, pv_tv,
                    f"Gordon Growth Model: TV = UFCF*(1+g)/(WACC-g), g={tgr*100:.0f}%, WACC={wacc*100:.0f}%"])
        rows_written += 1

    print(f"  dcf_template.csv → {rows_written} rows (incl. terminal value)")


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  README.md
# ═══════════════════════════════════════════════════════════════════════════════
def write_readme():
    text = """# MBA-P5: DealArchitect — M&A Financial Modelling Dataset

## Problem Statement
CloudStack (enterprise software, $5B revenue) is considering acquiring DataFlow Analytics
(fast-growing startup, $200M ARR). As the lead M&A analyst, build a full valuation model
and recommend a fair acquisition price range.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| cloudstack_financials.csv | 8 | CloudStack historical financials FY2017–FY2024 |
| dataflow_financials.csv | 5 | DataFlow Analytics financials FY2020–FY2024 |
| comparable_companies.csv | 10 | Public/private comps with trading multiples |
| precedent_transactions.csv | 5 | Recent data analytics M&A deals |
| dcf_template.csv | 12 | Pre-built DCF model with projections |

## Valuation Framework
Use three methodologies and triangulate:

### 1. Comparable Company Analysis (Comps)
- Apply EV/Revenue and EV/EBITDA multiples from comparable_companies.csv
- Adjust for DataFlow's higher growth rate (premium warranted)

### 2. Precedent Transaction Analysis (Precedents)
- Use EV/Revenue multiples from precedent_transactions.csv
- Note: M&A premiums typically 20-40% above trading comps

### 3. Discounted Cash Flow (DCF)
- Use dcf_template.csv as starting point
- Key assumptions: WACC=12%, Terminal Growth=3%, projection 10 years
- Sensitivity analysis: WACC ±2%, Terminal Growth ±1%

## Key Questions
1. What is the implied valuation range for DataFlow?
2. What synergies would CloudStack need to justify a premium?
3. Is DataFlow's 140% NDR sustainable? How does it affect LTV?
4. What integration risks exist (culture, technology, customer overlap)?
5. How does the deal affect CloudStack's leverage (Debt/EBITDA)?

## Suggested Deliverables
- Football field chart showing valuation range across methodologies
- Synergy model: revenue synergies + cost synergies over 3 years
- Pro-forma combined P&L for FY2025-FY2027
- Deal recommendation memo (buy / pass / conditional)
"""
    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print("  README.md written")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating MBA-P5 files...")
    print("  [1/6] cloudstack_financials.csv")
    generate_cloudstack()
    print("  [2/6] dataflow_financials.csv")
    generate_dataflow()
    print("  [3/6] comparable_companies.csv")
    generate_comps()
    print("  [4/6] precedent_transactions.csv")
    generate_precedent()
    print("  [5/6] dcf_template.csv")
    generate_dcf_template()
    print("  [6/6] README.md")
    write_readme()
    print("MBA-P5 complete.")
