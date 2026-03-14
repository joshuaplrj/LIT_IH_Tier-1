# HyperCool — Quick Start

## Objective
Design a two-phase (evaporative) cooling system for a high-density data center rack that dissipates 50 kW total (10 servers × 5 kW), handles chip-level heat flux up to 100 W/cm², and maintains junction temperature below 85°C under worst-case ambient of 40°C.

## Inputs
- **Total rack heat load**: 50 kW (10 servers × 5 kW each)
- **Chip heat flux**: up to 100 W/cm² (GPU/CPU die)
- **Die area**: 1 cm² (assumed; 10 mm × 10 mm)
- **Inlet coolant temperature**: 25°C (nominal); 40°C (worst case ambient)
- **Junction temperature limit**: < 85°C
- **Rack form factor**: 42U standard (600 mm × 1000 mm × 2000 mm)
- **Coolant options**: Water (boiling 100°C), Novec 7100 dielectric (boiling 61°C), R134a (boiling -26°C)

## Expected Output
A file named `report.json` with the following top-level keys:
```json
{
  "coolant_selected": "water | novec_7100 | R134a | other",
  "cooling_technology": "microchannel_cold_plate | immersion | heat_pipe",
  "chip_heat_flux_W_cm2": <float>,
  "die_area_cm2": <float>,
  "q_total_kW": <float>,
  "evaporator_channel_width_um": <float>,
  "evaporator_channel_height_um": <float>,
  "evaporator_htc_W_m2K": <float>,
  "evaporator_pressure_drop_kPa": <float>,
  "condenser_area_m2": <float>,
  "condenser_type": "air | liquid",
  "thermal_resistance_total_K_W": <float>,
  "junction_temp_C": <float>,
  "saturation_temp_C": <float>,
  "critical_heat_flux_W_cm2": <float>,
  "chf_safety_factor": <float>,
  "pump_power_W": <float>,
  "system_cop": <float>
}
```

## Recommended First Steps
1. Select **Novec 7100** as coolant (boiling point 61°C at 1 atm): its low saturation temperature leaves a large margin to Tj < 85°C while remaining non-toxic and non-conductive.
2. Calculate total thermal resistance budget: `R_total = (Tj_max - T_sat) / Q_chip`. With Tj = 85°C, T_sat = 61°C (at 1 bar), Q_chip = 500 W (100 W/cm² × 5 cm² die): `R_total = (85 - 61) / 500 = 0.048 K/W`. This is your entire budget — apportion it across junction-to-case, TIM, cold plate spreading, and convective resistance.
3. Size the microchannel cold plate: target heat transfer coefficient HTC >= 20,000 W/(m²·K) via boiling in microchannels (width 200–500 μm). Check that `Q / (HTC × A_base) = delta_T < your allocated R_conv × Q`.

## Scoring Breakdown
| Metric             | Weight |
|--------------------|--------|
| Thermal Resistance | 35%    |
| Pressure Drop      | 25%    |
| Reliability        | 25%    |
| Scalability        | 15%    |

## Common Pitfalls
- Using single-phase (sensible heat) to calculate HTC and forgetting that flow boiling can achieve 5–10× higher HTC — if your numbers show HTC of only 2,000–3,000 W/(m²·K), you have likely not engaged the two-phase regime.
- Neglecting the **critical heat flux (CHF)**: if the chip heat flux exceeds CHF, the liquid film dries out and the chip temperature spikes catastrophically; maintain a CHF safety factor >= 1.5.
- Computing pump power from pressure drop alone without checking whether natural circulation (thermosiphon) is sufficient — for Novec 7100 in a short vertical loop, natural circulation alone can drive flow, eliminating the pump entirely and improving reliability.
