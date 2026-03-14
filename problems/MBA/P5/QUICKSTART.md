# DealArchitect — Quick Start

## Objective
You are the Head of Corporate Development at CloudStack Inc. ($5B enterprise software). Evaluate the potential acquisition of DataFlow Analytics ($200M revenue, 80% growth, -$50M EBITDA) using DCF, comparable company analysis, and precedent transactions, then recommend an offer price and integration plan.

## Inputs
All data files are in `prerequisites/MBA/MBA-P5/` — run `generate_mba_p5.py` first if files are absent.

- **cloudstack_financials.csv** (8 rows): CloudStack historical P&L FY2017–FY2024 — revenue, EBITDA, FCF, debt, cash, EPS
- **dataflow_financials.csv** (5 rows): DataFlow P&L FY2020–FY2024 — revenue, ARR, gross margin, EBITDA (negative), NDR (140%), customer count, ACV, CAC, LTV, Rule of 40
- **comparable_companies.csv** (10 rows): Public/private comps with EV/Revenue and EV/EBITDA multiples — Snowflake, Databricks, Palantir, Tableau, Qlik, ThoughtSpot, Looker, Domo, MicroStrategy, Sisense
- **precedent_transactions.csv** (5 rows): Recent analytics M&A deals — Salesforce/Tableau, Google/Looker, SAP/Qualtrics, Thoma Bravo/Qlik, Salesforce/Slack — with EV/Revenue multiples
- **dcf_template.csv** (12 rows): Pre-built DCF model (FY2025–FY2035) with revenue projections, EBITDA margins, WACC=12%, TGR=3%, unlevered FCF, discount factors

## Expected Output
A structured JSON file (`submission.json`) with:
```
submission.json
├── dcf_valuation           (WACC, terminal value, NPV, sensitivity table)
├── comps_analysis          (selected multiples, implied valuation range)
├── precedent_analysis      (transaction multiples, implied valuation)
├── synergy_analysis        (revenue synergies, cost synergies, 3 cases)
├── deal_structure          (offer price, cash/stock mix, earnout, retention)
├── integration_plan        (Day 1 readiness, 100-day plan, key risks)
└── recommendation          (buy/pass/conditional, walk-away price, rationale)
```

## Recommended First Steps
1. Run `python starter.py --data-dir <path_to_MBA-P5>` to load the DCF template, compute NPV, and generate implied valuation ranges from comps and precedents in `analysis.json`
2. Start with the DCF — load `dcf_template.csv`, sum the PV of FCFs, add terminal value, subtract net debt to get equity value. Run a 3x3 sensitivity table (WACC ±2% × terminal growth rate ±1%) to see the valuation range
3. Compare your DCF value to the comps (EV/Revenue multiples) and precedents — triangulate a valuation range and identify whether comps or DCF is the binding floor/ceiling

## Scoring Breakdown
| Metric | Weight |
|---|---|
| DCF Valuation (WACC in 7–15% range, terminal value method, sensitivity table) | 30% |
| Synergy Analysis (revenue + cost synergies quantified, 3 scenarios) | 25% |
| Integration Plan (100-day plan, org design, culture, customer communication) | 25% |
| Risk Assessment (deal risks, integration risks, walk-away conditions) | 20% |

## Common Pitfalls
- Using a WACC outside the 7–15% range without justification — 12% is the template default for a high-growth SaaS startup; lower WACC = higher valuation
- Ignoring DataFlow's negative EBITDA in Years 1–2 of the DCF — the terminal value drives 60–80% of total value, but early years are cash-negative
- Adding synergies to the DCF baseline without discounting them separately — synergies have different risk profiles than standalone FCF
- Recommending a deal price without stating the walk-away price — judges expect a clear maximum bid, not just a point estimate
- Underestimating integration risk: DataFlow has 500 engineers and startup culture; retention packages and culture integration are not afterthoughts
