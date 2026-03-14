# DealArchitect — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

M&A valuation is never a single number — it is a **range** defined by three methodologies that each tell a different story. The DCF tells you what DataFlow is worth as a standalone business. The comps tell you what the market pays for similar businesses today. The precedents tell you what acquirers have paid for control premiums in similar deals. The art of M&A is explaining **why your recommended price sits where it does within this range**, and how much of the synergy value you are sharing with the seller. A deal is attractive when: (offer price - standalone DCF value) < (NPV of synergies you will capture). If you're paying more than the sum of standalone value + synergies, you're destroying shareholder value.

## Tier 2 — Framework Guidance (-10% score penalty)

**DCF mechanics**: Load `dcf_template.csv`. Sum the `pv_fcf_usd_m` column (Years 2025–2035). The terminal value row gives you PV of terminal value. Enterprise Value = sum of PV FCFs + PV terminal value. Equity Value = Enterprise Value - Net Debt (debt - cash). For DataFlow: use FY2024 numbers (debt ≈ $60M, cash ≈ $120M, net debt ≈ -$60M, i.e., net cash positive). Run sensitivity: vary WACC from 10–14% and terminal growth rate from 2–4%.

**Comps analysis**: From `comparable_companies.csv`, filter to high-growth analytics comps (revenue growth >20%). Apply their median EV/Revenue multiple to DataFlow's forward ARR ($180M). The high-growth comps (Databricks, ThoughtSpot, Looker) trade at 15–20x EV/Revenue. Apply a discount for DataFlow's smaller scale and private illiquidity (typically 20–30% discount to public comps).

**Precedent transactions**: From `precedent_transactions.csv`, the Salesforce/Tableau deal (14.7x EV/Revenue) and Google/Looker (6.7x) bracket the range. Apply to DataFlow's $200M revenue: implied EV range $1.3B–$3.0B. M&A deals typically command a 20–30% control premium over trading comps.

**Synergy model**: Revenue synergies = cross-sell DataFlow to CloudStack's 5,000 enterprise customers (model conversion rate × DataFlow ACV). Cost synergies = eliminate redundant S&M (both companies target same buyers), leverage CloudStack infrastructure (reduce DataFlow cloud costs by 30–40%). Use three cases: conservative (50% of synergies realised), base (75%), optimistic (100%). Share 50–70% of synergy value with DataFlow shareholders (precedent: Sirower's study shows 60% sharing in competitive auctions).

## Tier 3 — Structural Guidance (-15% score penalty)

Structure your `submission.json` as follows:

**`dcf_valuation`**: Report `wacc_pct` (your assumption), `terminal_growth_rate_pct`, `pv_fcf_sum_usd_m` (sum of PV FCFs from template), `pv_terminal_value_usd_m`, `enterprise_value_usd_m`, `equity_value_usd_m` (= EV + net cash), and a `sensitivity_table` (3×3 matrix: rows=WACC, cols=TGR, cells=equity_value_usd_m).

**`comps_analysis`**: `selected_comps` list (5–8 comps with rationale for selection/exclusion), `median_ev_revenue_multiple`, `applied_multiple` (with discount applied), `implied_ev_usd_m`, `discount_rationale`.

**`precedent_analysis`**: `selected_transactions` list (3–5), `ev_revenue_range`, `control_premium_applied_pct`, `implied_valuation_usd_m`.

**`synergy_analysis`**: `revenue_synergies_usd_m` (conservative/base/optimistic), `cost_synergies_usd_m` (conservative/base/optimistic), `total_synergy_npv_usd_m`, `synergy_share_to_seller_pct`, `incremental_value_to_cloudstack_usd_m`.

**`deal_structure`**: `recommended_offer_price_usd_m`, `walk_away_price_usd_m`, `cash_vs_stock_mix` (e.g., "70% cash / 30% CloudStack stock"), `earnout_structure` (milestone-based earnout to align founder), `key_employee_retention_pool_usd_m`.

**`recommendation`**: `decision` ("Buy" / "Pass" / "Conditional"), `rationale`, `key_conditions` (if conditional), `risk_factors` (at least 3).
