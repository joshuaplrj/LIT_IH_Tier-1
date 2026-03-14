# PricingGenius — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

Dynamic pricing on a two-sided platform is fundamentally a **supply-demand matching problem under constraints**. Your pricing engine has two independent levers: the price paid by passengers (demand side) and the incentive paid to drivers (supply side). Revenue maximisation is not the same as profit maximisation — driver incentives are a cost. Start by quantifying **price elasticity of demand** (what happens to ride volume when price increases?) and **supply elasticity** (what happens to driver availability when incentives increase?). These two elasticities define the trade-off frontier your pricing engine must navigate.

## Tier 2 — Framework Guidance (-10% score penalty)

Use a **log-log regression model** to estimate price elasticity of demand: `log(demand) = α + β × log(price) + γ × features`. The coefficient β is your price elasticity estimate — for ride-hailing, a realistic range is -0.3 to -1.5 (more elastic during off-peak when substitutes are available). Segment your data by: (1) peak vs. off-peak, (2) weather condition, (3) event proximity, (4) city tier. Each segment will have a different elasticity.

For the **surge multiplier optimisation**, the unconstrained revenue-maximising price is: `P* = MC / (1 + 1/ε)` where ε is the price elasticity. Apply two hard constraints: surge cap (city regulation, usually 2x) and competitor parity cap (price ≤ competitor × 1.15).

For the **A/B test design**, use a **switchback experiment** (alternate treatment and control in time blocks within the same geography) rather than geographic split testing, to avoid spillover effects (drivers/passengers moving between zones).

## Tier 3 — Structural Guidance (-15% score penalty)

Structure your `submission.json` as follows:

**`demand_model`**: Report elasticity estimates per segment as a table: `{segment, elasticity, n_observations, r_squared}`. Feature importance list (top 10 features). Baseline cancellation rate per surge bucket. Model type used (e.g., log-log OLS, XGBoost, LightGBM).

**`pricing_strategy`**: Define the surge multiplier formula explicitly:
`surge = min(max(1.0, demand_supply_ratio × base_factor), city_surge_cap, competitor_price × 1.15 / base_price)`
Document the segmented discount policy: what % discount for top-decile CLV customers? When are driver incentives triggered (supply < X% of demand forecast)?

**`simulation_results`**: Run your pricing strategy on a holdout slice of `rides.csv` (e.g., last 2 weeks of data). Report: total revenue under new strategy vs. baseline, percentage change, cancellation rate delta, average utilisation change. Use these as your "revenue uplift" metric.

**`ab_testing_plan`**: Specify minimum detectable effect size (e.g., 3% revenue lift), required sample size (rides per arm), test duration (days), randomisation unit (15-minute time block), guardrail metrics (cancellation rate, driver hours), and statistical test (t-test or Mann-Whitney U).

**`ethical_considerations`**: Address three specific issues: (1) surge pricing during emergencies (policy statement), (2) demographic fairness (how you avoid charging more in lower-income areas), (3) CLV protection threshold (e.g., top 20% customers capped at 1.3× surge).
