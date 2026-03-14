# MotorForge — Quick Start

## Objective
Design and simulate a 10 kW BLDC motor for an electric scooter: complete electromagnetic design, loss estimation, thermal analysis, and FOC controller simulation. Verify all performance requirements are met and document every design decision with supporting calculations.

## Inputs

This is a design problem — there are no pre-existing data files to load. Your inputs are the **design requirements** below:

| Parameter              | Requirement              |
|------------------------|--------------------------|
| Rated power            | 10 kW at 4,000 RPM       |
| Peak torque            | 40 Nm (0–2,000 RPM)      |
| Efficiency at rated    | > 92%                    |
| DC bus voltage         | 72 V                     |
| Cooling                | Air-cooled only          |
| Outer diameter         | ≤ 200 mm                 |
| Axial length           | ≤ 150 mm                 |
| Weight                 | ≤ 12 kg                  |

## Expected Output

**Filename:** `submission/motor_design_report.json`

The report must contain the following top-level keys (see `starter.py` for the full schema):

- `motor_parameters` — pole/slot count, dimensions, winding data, magnet grade
- `magnetic_analysis` — flux density, back-EMF constant, torque constant, inductances
- `loss_breakdown` — copper, iron, magnet, mechanical losses at rated conditions (W)
- `thermal_analysis` — winding temperature rise, ambient assumption, cooling coefficient
- `performance_verification` — efficiency %, torque at rated and peak, weight, size
- `foc_controller` — PI gain values, bandwidth, simulation notes
- `simulation_results` — torque-speed curve (array), efficiency map (array of dicts)

## Recommended First Steps

1. Run `python starter.py` — it prints a design worksheet with all core formulas pre-coded; inspect the calculated values and adjust the design parameters at the top of the script.
2. Use the electromagnetic sizing section to choose a pole/slot combination (e.g., 8 poles / 12 slots or 10 poles / 12 slots), then iterate the stator bore diameter until the torque constant meets the 40 Nm target.
3. Check the thermal model output — if the winding temperature rise exceeds ~120 K above ambient, reduce the current density or revise the slot fill factor.

## Scoring Breakdown

| Metric                  | Weight |
|-------------------------|--------|
| Efficiency at rated point (target >92%) | 30% |
| Torque density (Nm/kg, higher is better) | 25% |
| Thermal compliance (winding temp ≤ 155°C for Class F insulation) | 25% |
| Design documentation completeness and calculation rigor | 20% |

## Common Pitfalls

- Choosing too many pole pairs increases iron losses quadratically with frequency — for 4,000 RPM, 4 pole pairs (8 poles) gives 267 Hz fundamental, which is manageable; 10 pole pairs gives 667 Hz and iron losses dominate.
- Underestimating copper fill factor (realistic slot fill = 0.40–0.45 for round wire, not 0.60) leads to underestimating winding resistance and thus copper losses.
- Forgetting to add magnet eddy-current losses — at high electrical frequency with rare-earth magnets these can be 5–10% of total losses; use the formula in the starter.
