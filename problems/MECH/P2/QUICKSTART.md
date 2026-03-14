# ThermoCell — Quick Start

## Objective
Design a thermal energy storage (TES) system for a concentrated solar power plant that stores 1,000 MWh at 565°C and delivers 100 MW thermal discharge power for 10 hours. The system must achieve > 95% round-trip efficiency and cost less than $20/kWh over a 30-year design life.

## Inputs
- **Storage capacity**: 1,000 MWh thermal
- **Discharge power**: 100 MW thermal (10-hour discharge)
- **Charge power**: 50 MW thermal
- **Operating temperatures**: 290°C (cold) — 565°C (hot)
- **Round-trip efficiency target**: > 95%
- **Design life**: 30 years (10,950 thermal cycles)
- **Cost target**: < $20/kWh stored
- **Technology options**: Solar Salt molten salt (60% NaNO3 + 40% KNO3), PCM, or thermochemical

## Expected Output
A file named `report.json` with the following top-level keys:
```json
{
  "technology_selected": "molten_salt | PCM | thermochemical",
  "storage_medium": "<string>",
  "hot_tank_volume_m3": <float>,
  "cold_tank_volume_m3": <float>,
  "tank_material": "<string>",
  "insulation_thickness_m": <float>,
  "thermal_loss_rate_kW": <float>,
  "round_trip_efficiency_pct": <float>,
  "hx_area_m2": <float>,
  "hx_effectiveness": <float>,
  "energy_density_kWh_m3": <float>,
  "cycle_lifetime_cycles": <int>,
  "thermal_stress_MPa": <float>,
  "cost_per_kWh_usd": <float>,
  "total_salt_mass_kg": <float>,
  "charge_time_hr": <float>,
  "discharge_time_hr": <float>
}
```

## Recommended First Steps
1. Select **Solar Salt** (molten salt) as the storage medium and compute the required salt mass: `m = Q / (cp * delta_T)` where Q = 3,600,000 MJ, cp = 1.52 kJ/(kg·K), delta_T = 275 K.
2. Size the hot and cold tanks (cylindrical, H/D = 1): `V_salt = m / rho` where rho ≈ 1,800 kg/m³; add 10% ullage and choose tank dimensions.
3. Calculate thermal losses through the tank insulation using `Q_loss = k * A * delta_T / thickness` and verify round-trip efficiency meets the > 95% target.

## Scoring Breakdown
| Metric                         | Weight |
|--------------------------------|--------|
| Energy Density                 | 30%    |
| Charge/Discharge Efficiency    | 30%    |
| Structural / Thermal Analysis  | 25%    |
| Cost Estimate                  | 15%    |

## Common Pitfalls
- Using cp = 2.09 kJ/(kg·K) (water value) instead of the correct Solar Salt value of ~1.52 kJ/(kg·K) — this underestimates the required salt mass by 27%.
- Forgetting that the cold tank must also be insulated and maintained above 290°C (Solar Salt solidifies at ~238°C); cold tank heat tracing is a significant parasitic loss.
- Underestimating thermal expansion: the 275°C temperature swing causes ~0.5% volumetric expansion of the salt; tanks must accommodate this with expansion joints and not be filled 100%.
