# AeroBot — Quick Start

## Objective
Design a VTOL fixed-wing UAV capable of aerial surveying with 2 kg payload, 2-hour cruise endurance at 20 m/s, and 100 km round-trip range. The airframe must take off and land vertically from unprepared surfaces while meeting a 15 kg MTOW limit.

## Inputs
- **Payload mass**: 2 kg (camera, LiDAR, GPS)
- **Cruise speed**: 20 m/s
- **Endurance target**: >= 2 hours cruise
- **Range target**: 100 km round trip
- **Max wind**: 10 m/s
- **MTOW limit**: 15 kg
- **VTOL requirement**: No runway; vertical takeoff and landing
- **Design constraints**: foldable airframe preferred; ISA sea-level atmosphere assumed

## Expected Output
A file named `report.json` with the following top-level keys:
```json
{
  "configuration": "quad-plane | tilt-rotor | tail-sitter | hybrid",
  "mtow_kg": <float>,
  "wing_area_m2": <float>,
  "aspect_ratio": <float>,
  "airfoil": "<string>",
  "cruise_cl": <float>,
  "cruise_cd": <float>,
  "ld_ratio": <float>,
  "power_cruise_W": <float>,
  "battery_capacity_Wh": <float>,
  "endurance_hr": <float>,
  "range_km": <float>,
  "vtol_rotor_diameter_m": <float>,
  "vtol_disk_loading_kg_m2": <float>,
  "hover_power_W": <float>,
  "static_margin_percent": <float>,
  "wing_spar_safety_factor": <float>,
  "bom": [{"item": "<str>", "mass_kg": <float>, "cost_usd": <float>}]
}
```

## Recommended First Steps
1. Fix MTOW budget: allocate mass fractions to structure (35%), propulsion (25%), battery (30%), and payload (10%) and verify sum <= 15 kg.
2. Size the wing: use cruise lift equation `W = 0.5 * rho * V^2 * S * CL` with CL ~0.8 for your chosen airfoil to get wing area, then derive aspect ratio for L/D > 12.
3. Calculate cruise power (`P = D * V`), then battery capacity (`E = P * t / eta_motor`), and check battery mass fits within the allocated budget before moving to VTOL rotor sizing.

## Scoring Breakdown
| Metric                  | Weight |
|-------------------------|--------|
| Aerodynamics            | 25%    |
| Structural Integrity    | 25%    |
| Propulsion Efficiency   | 25%    |
| Design Documentation    | 25%    |

## Common Pitfalls
- Forgetting to account for VTOL hover power in battery sizing — hover can consume 3-5x cruise power; a 2-minute transition budget alone can drain a lightweight battery.
- Selecting too small a wing (low wing loading is good for efficiency) but then finding the VTOL rotors are undersized for the resulting disk loading; aim for disk loading < 15 kg/m².
- Ignoring transition: the UAV must fly stably at airspeeds between 0 and stall (~10 m/s) — check that the VTOL rotors can provide sufficient pitch authority during the transition phase.
