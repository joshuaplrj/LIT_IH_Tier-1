# MarketPivot — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

Strategic transformation problems require you to separate **where to compete** from **how to compete**. MediCore's core challenge is that its competitive advantages (installed base, regulatory compliance, data) are eroding at different rates across its three business lines. Before modeling financials, identify which parts of the business are worth defending, which are worth harvesting (generating cash but not investing in growth), and which represent new platforms worth building. The Build/Buy/Partner/Pivot framework only works if you first diagnose the strategic position clearly.

## Tier 2 — Framework Guidance (-10% score penalty)

Apply **Porter's Five Forces** to each of MediCore's three business lines (EHR, billing, telehealth) separately — the competitive dynamics differ significantly. Then use a **Build-Buy-Partner scoring matrix** with at least four criteria: speed-to-capability, cost, control/IP, execution risk. For the financial model, use a **three-scenario P&L** (base, optimistic, downside) anchored on the current 15% churn rate as the bear-case assumption. For the strategic recommendation itself, frame it using the **McKinsey Three Horizons** model: Horizon 1 (defend/optimize the EHR core), Horizon 2 (accelerate billing AI and telehealth platform), Horizon 3 (new AI-native platform business). This structure lets you allocate the $500M cash reserve and $160M R&D spend coherently.

## Tier 3 — Structural Guidance (-15% score penalty)

Structure your `submission.json` as follows for maximum score:

**`strategic_analysis`**: Include a Porter's 5 Forces table for the EHR market, a 2x2 competitive positioning matrix (price vs. AI capability), and a weighted strategic options scorecard (4 options x 5 criteria x 0–10 scores).

**`recommended_strategy`**: State a single primary recommendation (e.g., "Partner-first with selective Build"). Justify using the scorecard. Acknowledge the top trade-off explicitly.

**`gtm_transformation`**: Model the license-to-SaaS transition as a revenue bridge — show how much license revenue converts, at what ASP change, over what timeline. Include a customer retention playbook (90-day, 180-day, 12-month actions).

**`financial_plan`**: Build the 3-year P&L starting from Year 0 (current state): Revenue, COGS, Gross Profit, EBITDA. Show three columns per year (base/bull/bear). Include a capital allocation table (R&D split by horizon, M&A budget, debt refinancing plan). Calculate break-even for the new AI product line.

**`risk_analysis`**: Use a risk matrix (probability × impact) with at least 6 risks. For the two highest-priority risks, write a full mitigation plan plus a contingency trigger.
