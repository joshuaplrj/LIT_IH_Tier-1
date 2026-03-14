# LaunchPad — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

Selling deep-tech B2B to Fortune 500 buyers is a **land-and-expand** game, not a volume motion. Your initial ICP (Ideal Customer Profile) should be ruthlessly specific: which 50 companies can you actually close in 18 months, and which specific person within each company is your champion? The key tension is between **targeting broadly** (maximising pipeline) and **targeting deeply** (maximising close rate on a limited $500K budget with a 3-person sales team). For a product with a 6–18 month sales cycle, you can only afford to pursue accounts where you have a credible path to a champion within the first 60 days. Everything else is a distraction.

## Tier 2 — Framework Guidance (-10% score penalty)

Use the **MEDDIC sales qualification framework** for each deal: Metrics (quantified business impact), Economic buyer (who signs), Decision criteria (how they evaluate), Decision process (steps to close), Identify pain (specific problem), Champion (internal advocate). Your sales playbook should map to each MEDDIC stage.

For **market sizing**, use three layers: TAM = $15B (total optimisation software market), SAM = the fraction addressable with a cloud API product in logistics/supply chain (estimate 20–30% of TAM = $3–4.5B), SOM = what you can actually close in 18 months = (# target accounts × win rate × ACV). Then do a bottom-up check: 3 sales reps × 40 active deals each × 20% close rate × $150K ACV = realistic ARR target.

For **channel budget allocation**, the correct model for enterprise B2B deep-tech is: 50–60% on outbound direct sales (sales team salaries and tools), 15–20% on thought leadership/content (analysts, whitepapers, conference speaking), 10–15% on targeted events (2–3 logistics/supply chain conferences), 5–10% on account-based digital (LinkedIn targeted to ICP personas). Digital advertising CPCs are a poor use of budget when your audience is 5,000 people globally.

For **CAC/LTV**, LTV = ACV × gross margin × (1 / churn rate). For enterprise SaaS with 90% gross margin and 5% annual churn: LTV = $150K × 0.90 / 0.05 = $2.7M. CAC = total sales + marketing spend / # new customers closed. For a 12-month sales cycle with 3 reps at $150K fully loaded: CAC = ($450K + $500K) / 12 new customers/year = ~$79K. LTV/CAC ratio = 2.7M/79K = 34x (excellent — deep-tech B2B tends to look strong on this metric when customers are sticky).

## Tier 3 — Structural Guidance (-15% score penalty)

Structure your `submission.json` as follows:

**`market_sizing`**: Report `tam_usd_b` (15.0), `sam_usd_b` (your estimate with methodology), `som_18month_usd_m` (realistic 18-month target). Include both top-down and bottom-up calculations explicitly. List your ICP definition (5 criteria: industry, company size, tech stack, pain point, budget authority).

**`gtm_strategy`**: Define positioning statement (for [ICP] who [pain point], QuantumLeap is [category] that [key benefit] unlike [competitor], we [key differentiator]). Include a competitive matrix (3–5 competitors × 4–6 criteria). Define your sales methodology (MEDDIC recommended) and document the 6-stage sales playbook.

**`channel_strategy`**: Report `budget_by_channel` (dict of channel → $K allocation), `expected_leads_by_channel`, `expected_pipeline_by_channel_usd_m`. Justify direct-vs-PLG-vs-partner choice (PLG is hard for enterprise B2B with 12-month sales cycles and $100K+ ACVs).

**`financial_projections`**: Build a monthly ARR model: `monthly_arr_usd_k` (list of 18 values). Compute `cac_usd_k`, `ltv_usd_k`, `ltv_cac_ratio`, `payback_months`. State the `series_b_arr_threshold_usd_m` (your estimate of required ARR for Series B) and whether your model reaches it.

**`action_plan_90_days`**: 12 specific actions across 3 sprints (Days 1–30, 31–60, 61–90). Each action: `sprint`, `action`, `owner`, `success_metric`. Prioritise: hire AEs, identify champion contacts at top 20 accounts, publish first thought leadership piece, launch outbound sequence.
