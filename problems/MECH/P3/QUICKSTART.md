# GearPro — Quick Start

## Objective
Design a 3-stage epicyclic (planetary) gearbox for a 5 MW wind turbine, converting 8–15 RPM rotor input to 1,500 RPM generator output (overall ratio ~1:100). The gearbox must meet AGMA 6006 standards, achieve > 97% efficiency, and survive 175,200 hours (20 years) of operation.

## Inputs
- **Input speed**: 8–15 RPM (variable; design at 15 RPM rated)
- **Input torque**: 3.2 MN·m at rated wind speed
- **Output speed**: 1,500 RPM (50 Hz, 4-pole generator)
- **Overall gear ratio**: ~100:1 (exact value from your design)
- **Design life**: 20 years = 175,200 hours
- **Efficiency target**: > 97% overall (all stages combined)
- **Noise limit**: < 85 dBA at 1 m
- **Design standard**: AGMA 6006 (wind turbine gearboxes)

## Expected Output
A file named `report.json` with the following top-level keys:
```json
{
  "overall_gear_ratio": <float>,
  "ratio_error_pct": <float>,
  "stage_ratios": [<float>, <float>, <float>],
  "stages": [
    {
      "stage": 1,
      "sun_teeth": <int>, "planet_teeth": <int>, "ring_teeth": <int>,
      "module_mm": <float>, "face_width_mm": <float>,
      "num_planets": <int>, "helix_angle_deg": <float>,
      "agma_bending_sf": <float>, "agma_contact_sf": <float>
    }, ...
  ],
  "overall_efficiency_pct": <float>,
  "bearing_l10_life_hr": <float>,
  "output_speed_rpm": <float>,
  "input_torque_MNm": <float>,
  "agma_standard": "AGMA 6006"
}
```

## Recommended First Steps
1. Distribute the 1:100 ratio across 3 planetary stages: a good starting split is 1:5, 1:5, 1:4 (product = 100). Each single-stage planetary ratio is `i = 1 + Z_ring / Z_sun`.
2. For each stage, select `Z_sun`, then compute `Z_planet = (Z_ring - Z_sun) / 2` and verify the **assembly condition**: `(Z_sun + Z_ring) / N_planets` must be an integer.
3. Run AGMA bending stress check: `sigma_b = W_t * Ko * Kv * Ks * Km / (b * m * J)` and confirm safety factor >= 1.2 for all meshes.

## Scoring Breakdown
| Metric               | Weight |
|----------------------|--------|
| Gear Ratio Accuracy  | 25%    |
| AGMA Compliance      | 30%    |
| Bearing Selection    | 20%    |
| Efficiency           | 25%    |

## Common Pitfalls
- Violating the **assembly condition** — if `(Z_sun + Z_ring)` is not exactly divisible by the number of planets, the planets cannot be equally spaced and the gearbox cannot be assembled.
- Choosing too small a module to save space, resulting in AGMA contact stress that exceeds the allowable `S_ac` for carburised steel — Stage 1 sees the highest torque and needs the largest module (typically 16–25 mm).
- Neglecting the **load sharing factor** among planets (AGMA `K_H` for planetary gears accounts for unequal load sharing due to manufacturing tolerances; use `K_H >= 1.1` for 3-planet stages).
