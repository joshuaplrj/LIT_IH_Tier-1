# EEE-P1: GridBrain — Microgrid Optimisation Challenge

## Problem Statement
Design and implement an intelligent energy management system (EMS) for a community microgrid that minimises operational costs and maximises renewable energy utilisation while ensuring reliable power supply.

## Dataset Description

### microgrid_data.csv
One full year of hourly operational data (8,760 rows), covering 2023-01-01 to 2023-12-31 UTC.

| Column | Unit | Description |
|--------|------|-------------|
| timestamp | ISO 8601 UTC | Hourly timestamp |
| solar_irradiance_W_per_m2 | W/m² | Incident solar irradiance with cloud-cover effects |
| wind_speed_m_s | m/s | Hub-height wind speed (Weibull-distributed, seasonal) |
| temperature_C | °C | Ambient temperature (seasonal + diurnal variation) |
| load_demand_kW | kW | Community electrical demand |
| solar_output_kW | kW | PV array output (derived from irradiance) |
| wind_output_kW | kW | Wind turbine output (power-curve model) |
| renewable_total_kW | kW | solar_output_kW + wind_output_kW |
| net_load_kW | kW | load_demand_kW − renewable_total_kW (positive = deficit) |
| battery_soc_baseline_pct | % | Greedy-policy battery state-of-charge baseline |

### equipment_specs.json
Technical specifications for all microgrid assets (PV, wind turbines, battery, diesel generator).

## Objectives
1. **Forecast** solar and wind output 24 hours ahead.
2. **Optimise** the battery charge/discharge schedule to minimise diesel consumption.
3. **Detect** periods of energy curtailment or unmet demand.
4. **Reduce** lifecycle battery degradation by avoiding deep cycles.

## Evaluation Metrics
- Root Mean Squared Error of energy forecasts (kW)
- Total diesel fuel consumed over a 30-day test window (litres)
- Number of hours with unmet demand
- Battery equivalent full cycles (lower is better)

## Constraints
- Battery SOC must remain within [10 %, 90 %] at all times.
- Diesel generator may only provide up to 300 kW.
- Net load must be ≥ 0 kW (no export to main grid assumed).

## Getting Started
```python
import pandas as pd, json

df   = pd.read_csv("microgrid_data.csv", parse_dates=["timestamp"])
spec = json.load(open("equipment_specs.json"))
print(df.head())
print(spec["battery"])
```
