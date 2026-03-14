"""
generate_eee_p1.py
Generates microgrid_data.csv, equipment_specs.json, and README.md
for EEE-P1 "GridBrain" hackathon problem.
"""

import numpy as np
import csv
import json
import os
from datetime import datetime, timezone, timedelta

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.join(
    r"C:\Users\John Jacob\Desktop\Tier-1\prerequisites\EEE\EEE-P1"
)
os.makedirs(BASE_DIR, exist_ok=True)

CSV_PATH   = os.path.join(BASE_DIR, "microgrid_data.csv")
JSON_PATH  = os.path.join(BASE_DIR, "equipment_specs.json")
README_PATH = os.path.join(BASE_DIR, "README.md")

# ── RNG ────────────────────────────────────────────────────────────────────────
np.random.seed(42)

# ── Constants ─────────────────────────────────────────────────────────────────
HOURS       = 8760           # 365 * 24
START_UTC   = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

BATTERY_CAPACITY_KWH = 2000.0
SOC_MIN = 10.0   # %
SOC_MAX = 90.0   # %

# ── Time axis ─────────────────────────────────────────────────────────────────
timestamps = [
    (START_UTC + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for h in range(HOURS)
]

# Day-of-year (0-indexed) for each hour
doy = np.array([(START_UTC + timedelta(hours=h)).timetuple().tm_yday - 1
                for h in range(HOURS)], dtype=float)          # 0 … 364

# Hour of day for each row
hour_of_day = np.array([(h % 24) for h in range(HOURS)], dtype=float)

# Weekday (0=Mon … 6=Sun) for each row
weekday = np.array([
    (START_UTC + timedelta(hours=h)).weekday() for h in range(HOURS)
], dtype=int)

# ── Solar irradiance ──────────────────────────────────────────────────────────
# Seasonal sunrise / sunset (linear interp between winter and summer)
# Winter: sunrise 6, sunset 18  |  Summer: sunrise 5, sunset 19
season_factor = 0.5 * (1 - np.cos(2 * np.pi * doy / 365))   # 0→winter, 1→summer
sunrise  = 6.0 - 1.0 * season_factor          # 6 in winter → 5 in summer
sunset   = 18.0 + 1.0 * season_factor          # 18 in winter → 19 in summer
daylight = sunset - sunrise

# Peak irradiance: 700 (winter) → 1100 (summer) W/m²
peak_irr = 700 + 400 * season_factor

# Bell-curve irradiance formula
solar_noon_frac = (hour_of_day - sunrise) / daylight
irr_raw = np.maximum(0, np.sin(np.pi * solar_noon_frac)) * peak_irr

# Zero out before sunrise / after sunset
mask_day = (hour_of_day >= sunrise) & (hour_of_day < sunset)
irr_raw = np.where(mask_day, irr_raw, 0.0)

# Cloud-cover attenuation: ~30 % of hours get reduced
cloud_factor = np.ones(HOURS)
cloudy_hours = np.random.random(HOURS) < 0.30
cloud_factor[cloudy_hours] = np.random.uniform(0.2, 1.0, cloudy_hours.sum())
solar_irradiance = irr_raw * cloud_factor

# ── Wind speed ────────────────────────────────────────────────────────────────
# Base Weibull(k=2, λ=6); seasonal: +1.5 in winter, –1.5 in summer
k_shape, lam_scale = 2.0, 6.0
weibull_base = lam_scale * np.random.weibull(k_shape, HOURS)

# Seasonal: winter higher
seasonal_wind = 1.5 * np.cos(2 * np.pi * doy / 365)   # +1.5 in Jan, –1.5 in Jul

# Daily pattern: slightly higher mid-day (+0.5 at noon)
daily_wind = 0.5 * np.sin(np.pi * (hour_of_day - 6) / 12) * (hour_of_day >= 6) * (hour_of_day <= 18)

wind_speed = np.clip(weibull_base + seasonal_wind + daily_wind, 0.0, 25.0)

# ── Temperature ───────────────────────────────────────────────────────────────
# Seasonal daily mean: 15 (winter) → 35 (summer) °C
temp_mean_daily = 15 + 20 * season_factor

# Daily sinusoidal ±5 °C (min at 4am, max at 3pm)
temp_daily_variation = 5 * np.sin(2 * np.pi * (hour_of_day - 4) / 24)

# Gaussian noise
temp_noise = np.random.normal(0, 1.0, HOURS)

temperature = temp_mean_daily + temp_daily_variation + temp_noise

# ── Load demand ───────────────────────────────────────────────────────────────
# Base load
is_weekday = (weekday < 5)
base_kw = np.where(is_weekday, 300.0, 220.0)

# Morning peak 7–9 am: Gaussian centred at 8 am
morning_peak = 150.0 * np.exp(-0.5 * ((hour_of_day - 8) / 1.0) ** 2)

# Evening peak 6–9 pm: Gaussian centred at 7 pm (19)
# Weekday peak higher
eve_height = np.where(is_weekday, 200.0, 160.0)
evening_peak = eve_height * np.exp(-0.5 * ((hour_of_day - 19) / 1.5) ** 2)

# Industrial load: only on weekdays during working hours
industrial = np.where(
    is_weekday & (hour_of_day >= 8) & (hour_of_day < 18),
    80.0, 0.0
)

# Seasonal variation ±10 %
seasonal_load = 1.0 + 0.10 * np.cos(2 * np.pi * (doy - 15) / 365)

# Noise
load_noise = np.random.normal(0, 20.0, HOURS)

load_demand = (base_kw + morning_peak + evening_peak + industrial + load_noise) * seasonal_load
load_demand = np.clip(load_demand, 150.0, 800.0)

# ── Solar output ──────────────────────────────────────────────────────────────
solar_output = solar_irradiance * 500 * 0.20 * 0.001   # W/m² × panels × eff × kW
solar_output = np.clip(solar_output, 0.0, 500.0)

# ── Wind output ───────────────────────────────────────────────────────────────
def turbine_power_kw(ws):
    """Power curve for a single 250 kW turbine."""
    p = np.zeros_like(ws)
    # Between cut-in (3) and rated (12)
    in_range = (ws >= 3.0) & (ws < 12.0)
    p[in_range] = 250.0 * ((ws[in_range] - 3.0) / (12.0 - 3.0)) ** 3
    # Between rated and cut-out
    rated_range = (ws >= 12.0) & (ws <= 25.0)
    p[rated_range] = 250.0
    return np.minimum(p, 250.0)

wind_output = 2 * turbine_power_kw(wind_speed)   # 2 turbines

# ── Derived columns ───────────────────────────────────────────────────────────
renewable_total = solar_output + wind_output
net_load = load_demand - renewable_total

# ── Battery SOC (greedy baseline) ────────────────────────────────────────────
battery_soc = np.empty(HOURS)
soc = 50.0                      # start at 50 %
energy_per_pct = BATTERY_CAPACITY_KWH / 100.0   # 20 kWh per %

for h in range(HOURS):
    surplus = -net_load[h]       # positive → surplus renewable energy
    delta_pct = surplus / energy_per_pct   # % change per hour
    soc = np.clip(soc + delta_pct, SOC_MIN, SOC_MAX)
    battery_soc[h] = soc

# ── Write CSV ─────────────────────────────────────────────────────────────────
COLUMNS = [
    "timestamp",
    "solar_irradiance_W_per_m2",
    "wind_speed_m_s",
    "temperature_C",
    "load_demand_kW",
    "solar_output_kW",
    "wind_output_kW",
    "renewable_total_kW",
    "net_load_kW",
    "battery_soc_baseline_pct",
]

print(f"Writing {CSV_PATH} ...")
with open(CSV_PATH, "w", newline="") as fh:
    writer = csv.writer(fh)
    writer.writerow(COLUMNS)
    for h in range(HOURS):
        writer.writerow([
            timestamps[h],
            round(float(solar_irradiance[h]), 4),
            round(float(wind_speed[h]), 4),
            round(float(temperature[h]), 4),
            round(float(load_demand[h]), 4),
            round(float(solar_output[h]), 4),
            round(float(wind_output[h]), 4),
            round(float(renewable_total[h]), 4),
            round(float(net_load[h]), 4),
            round(float(battery_soc[h]), 4),
        ])
print(f"  Done — {HOURS} rows written.")

# ── Write equipment_specs.json ────────────────────────────────────────────────
specs = {
    "solar_pv": {
        "capacity_kw": 500,
        "panel_efficiency_pct": 20,
        "inverter_efficiency_pct": 97,
        "degradation_per_year_pct": 0.5
    },
    "wind_turbine": {
        "count": 2,
        "rated_power_kw_each": 250,
        "cut_in_speed_m_s": 3,
        "rated_speed_m_s": 12,
        "cut_out_speed_m_s": 25
    },
    "battery": {
        "capacity_kwh": 2000,
        "soc_min_pct": 10,
        "soc_max_pct": 90,
        "charge_efficiency_pct": 95,
        "discharge_efficiency_pct": 95,
        "degradation_per_cycle_pct": 0.01,
        "replacement_cost_usd": 400000
    },
    "diesel_generator": {
        "capacity_kw": 300,
        "fuel_cost_usd_per_liter": 1.50,
        "fuel_consumption_l_per_kwh": 0.25,
        "startup_cost_usd": 5
    },
    "load": {
        "peak_kw": 800,
        "average_kw": 400,
        "min_kw": 150
    }
}

print(f"Writing {JSON_PATH} ...")
with open(JSON_PATH, "w") as fh:
    json.dump(specs, fh, indent=2)
print("  Done.")

# ── Write README.md ───────────────────────────────────────────────────────────
readme_text = """# EEE-P1: GridBrain — Microgrid Optimisation Challenge

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
"""

print(f"Writing {README_PATH} ...")
with open(README_PATH, "w", encoding="utf-8") as fh:
    fh.write(readme_text)
print("  Done.")

print("\nEEE-P1 generation complete.")
