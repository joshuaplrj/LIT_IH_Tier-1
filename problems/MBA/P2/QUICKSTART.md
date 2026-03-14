# PricingGenius — Quick Start

## Objective
You are the VP of Pricing at GoRide, a ride-hailing platform processing 5M rides/day across 50 cities. Design a dynamic pricing strategy that maximises revenue while maintaining competitive market share (prices must not exceed competitors by more than 15%).

## Inputs
All data files are in `prerequisites/MBA/MBA-P2/` — run `generate_mba_p2.py` first if files are absent.

- **rides.csv** (1,000,000 rows): `ride_id`, `timestamp`, `city`, `origin_zone`, `dest_zone`, `distance_km`, `duration_min`, `base_price_usd`, `surge_multiplier`, `final_price_usd`, `driver_rating`, `passenger_rating`, `cancelled`
- **competitor_prices.csv** (~300,000 rows): `timestamp`, `city`, `origin_zone`, `dest_zone`, `competitor_name`, `price_usd`, `scraped_at` — two competitors: RideX and QuickCab
- **events.csv** (500 rows): `event_id`, `city`, `event_name`, `event_type`, `start_datetime`, `end_datetime`, `expected_attendance`
- **weather.csv** (217,200 rows): `timestamp`, `city`, `temperature_c`, `precipitation_mm_hr`, `visibility_km`, `wind_speed_kmph`, `weather_condition`

## Expected Output
A structured JSON file (`submission.json`) with:
```
submission.json
├── demand_model        (features, accuracy metrics, elasticity estimates by segment)
├── pricing_strategy    (surge formula, multiplier caps, segment discounts, driver incentives)
├── simulation_results  (revenue uplift %, cancellation rate delta, utilisation change)
├── ab_testing_plan     (metrics, significance thresholds, rollout design)
└── ethical_considerations  (fairness policy, regulatory compliance, CLV protection)
```

## Recommended First Steps
1. Run `python starter.py --data-dir <path_to_MBA-P2>` to load the data, compute summary statistics, and generate baseline price elasticity estimates in `analysis.json`
2. Identify peak demand windows: group `rides.csv` by hour-of-day and day-of-week to find where surge_multiplier is already high — these are your validation segments
3. Compute the cancellation rate by surge multiplier bucket (1.0–1.5, 1.5–2.0, 2.0+) to understand the demand cliff — this is your core elasticity signal

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Revenue Uplift (quantified % improvement over baseline pricing) | 35% |
| Demand Model Accuracy (documented feature importance + error metrics) | 30% |
| Strategy Documentation (surge formula, segmentation logic, driver incentives) | 20% |
| Ethical Considerations (fairness, CLV protection, regulatory compliance) | 15% |

## Common Pitfalls
- Optimising only for revenue without modelling the cancellation elasticity — overpricing kills supply utilisation and reduces total revenue
- Ignoring the 15% competitor price cap constraint — any surge above competitor + 15% should be flagged in your model
- Treating all 50 cities identically — city-level surge caps (some cities cap at 2x) and local demand patterns are material
- Skipping driver incentive modelling — supply-side is half the equation; higher prices are worthless if drivers aren't available
- Not addressing CLV segmentation — loyal high-frequency customers have high LTV and should receive price protection
