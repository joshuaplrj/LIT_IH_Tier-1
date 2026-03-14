# GridBrain — Quick Start

## Objective
Design an AI-optimized energy management system for an off-grid island microgrid that minimizes 20-year total cost (fuel + battery replacement + maintenance) while ensuring no more than 10 hours of annual load shedding. Implement as an optimization problem (MILP, DP, or RL) and compare against a rule-based baseline.

## Inputs

- `prerequisites/EEE/EEE-P1/microgrid_data.csv` — 8,760 rows of hourly data for 2023:
  - `timestamp` (ISO 8601 UTC), `solar_irradiance_W_per_m2`, `wind_speed_m_s`, `temperature_C`
  - `load_demand_kW`, `solar_output_kW`, `wind_output_kW`, `renewable_total_kW`
  - `net_load_kW` (positive = deficit), `battery_soc_baseline_pct` (greedy policy reference)
- `prerequisites/EEE/EEE-P1/equipment_specs.json` — asset specifications:
  - Solar PV: 500 kW capacity, 20% panel efficiency, 97% inverter efficiency
  - Wind: 2 × 250 kW, cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s
  - Battery: 2,000 kWh, SOC 10–90%, 95% round-trip efficiency, $400,000 replacement cost
  - Diesel: 300 kW max, $1.50/L fuel, 0.25 L/kWh, $5 startup cost

## Expected Output

**Filename:** `submission/schedule.json`

```json
{
  "metadata": {
    "solver": "string",
    "horizon_hours": 8760,
    "total_cost_usd": 0.0,
    "total_emissions_kg_co2": 0.0,
    "load_shedding_hours": 0,
    "battery_cycles": 0.0
  },
  "hourly_schedule": [
    {
      "hour": 0,
      "battery_charge_kw": 0.0,
      "battery_discharge_kw": 0.0,
      "diesel_output_kw": 0.0,
      "load_shed_kw": 0.0,
      "battery_soc_pct": 50.0
    }
  ],
  "sensitivity_analysis": {
    "fuel_price_2x": {"total_cost_usd": 0.0},
    "solar_capacity_1_5x": {"total_cost_usd": 0.0}
  }
}
```

## Recommended First Steps

1. Load `microgrid_data.csv` and `equipment_specs.json`; plot the net load profile and identify surplus/deficit patterns across seasons.
2. Implement the rule-based baseline (renewables first → battery second → diesel last) to establish a cost and shedding benchmark.
3. Formulate and solve a rolling 24-hour MILP using the `net_load_kW` column as the forecast; extend to the full year by sliding the window.

## Scoring Breakdown

| Metric                  | Weight |
|-------------------------|--------|
| Cost reduction vs. baseline | 35%  |
| Emission reduction      | 25%    |
| Constraint satisfaction (SOC bounds, load shedding ≤ 10 h/yr, diesel ≤ 300 kW) | 25% |
| Solution quality (sensitivity analysis completeness, formulation clarity) | 15% |

## Common Pitfalls

- Forgetting battery round-trip efficiency (95% charge × 95% discharge = 90.25% effective) leads to SOC drift.
- Setting up MILP without binary startup variables causes the solver to spuriously "trickle" the diesel generator at partial load, underestimating startup costs.
- Running the full 8,760-hour MILP at once is usually intractable; use a rolling 24–48 hour window with a warm-start SOC carry-over.
- Ignoring the 20-year battery degradation model means the optimizer does not correctly trade off deep cycles against fuel cost today.
