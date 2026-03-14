# MBA-P2: PricingGenius — Ride-Hailing Dynamic Pricing Dataset

## Problem Statement
You are the Head of Pricing at GoRide, a ride-hailing company operating in 50 cities.
Design a dynamic pricing algorithm that maximises revenue while maintaining acceptable
cancellation rates and driver/passenger satisfaction.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| rides.csv | 1,000,000 | Historical ride records Jan–Jun 2024 |
| competitor_prices.csv | ~300,000 | Competitor price samples (RideX, QuickCab) |
| events.csv | 500 | City event calendar |
| weather.csv | 217,200 | Hourly weather per city |

## rides.csv Columns
- ride_id: Unique ride identifier
- timestamp: Ride request datetime (YYYY-MM-DD HH:MM:SS)
- city: city_1 … city_50
- origin_zone / dest_zone: zone_A … zone_J
- distance_km: Trip distance
- duration_min: Trip duration in minutes
- base_price_usd: Formula-based price (2.50 + 1.20*dist + 0.30*dur)
- surge_multiplier: 1.0–3.0 (higher during peaks/events)
- final_price_usd: base_price * surge_multiplier
- driver_rating / passenger_rating: 1–5 scale
- cancelled: 1 = cancelled, 0 = completed

## Key Challenges
1. Predict demand spikes (events, weather, time-of-day)
2. Balance surge pricing vs. cancellation risk
3. Competitor price benchmarking
4. Zone-level demand forecasting

## Suggested Approach
- Feature engineering: hour, dow, weather features, event proximity
- Model: XGBoost/LightGBM for demand prediction; RL for pricing policy
- Evaluation: Revenue lift vs. baseline, cancellation rate delta
