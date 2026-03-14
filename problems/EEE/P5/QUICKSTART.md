# E-Harvest — Quick Start

## Objective
Design a complete RF energy harvesting system (rectenna) on a 50 mm × 50 mm PCB that captures ambient 915 MHz and 2.4 GHz RF energy and delivers stable 1.8 V DC at 100 μW to a low-power IoT sensor, operating without a battery using only capacitor buffering.

## Inputs

This is a design problem — no pre-existing data files. Your design inputs are:

| Parameter               | Value                          |
|-------------------------|--------------------------------|
| Target frequencies      | 915 MHz and 2.4 GHz            |
| Input RF power range    | -20 dBm to -10 dBm (10–100 μW) |
| PCB area                | 50 mm × 50 mm, 2-layer         |
| Output voltage          | 1.8 V ± 5%                    |
| Output power            | 100 μW minimum                 |
| PCE target              | > 40% at -10 dBm               |
| Storage                 | Capacitor only (no battery)    |

## Expected Output

**Filename:** `submission/eharvest_design_report.json`

Top-level keys required:

- `antenna_design` — type, geometry, dimensions, gain (dBi), S11 at target frequencies, bandwidth
- `matching_network` — topology, component values (L, C), insertion loss, bandwidth
- `rectifier_circuit` — topology (doubler/Dickson/etc.), diode part number, conversion efficiency curve
- `voltage_regulator` — type, quiescent current, output voltage, load regulation
- `energy_buffer` — capacitor value, capacitor voltage rating, charge/discharge analysis
- `simulation_results` — PCE vs. input power table, output voltage vs. input power table, startup waveform
- `pcb_layout_notes` — layer stack, trace widths, ground plane strategy

## Recommended First Steps

1. Run `python starter.py` — it computes theoretical maximum PCE, antenna link budget, and rectifier operating point using standard RF circuit equations; review which stage dominates the efficiency loss.
2. Adjust the antenna gain target: a simple patch antenna on 50 mm × 50 mm FR4 achieves ~5 dBi at 2.4 GHz — the script shows how that affects harvestable power at each frequency.
3. Iterate on the rectifier stage: the Dickson multiplier trades voltage gain for efficiency; the single-series rectifier is more efficient at -10 dBm but produces lower voltage — run both topologies with the `RECTIFIER_TOPOLOGY` flag in the script.

## Scoring Breakdown

| Metric                                      | Weight |
|---------------------------------------------|--------|
| Power Conversion Efficiency (PCE) at -10 dBm (target > 40%) | 40% |
| Bandwidth (coverage of 915 MHz and 2.4 GHz, wider is better) | 25% |
| Output voltage stability (1.8 V ± 5% over input range) | 20% |
| Design documentation completeness | 15% |

## Common Pitfalls

- Using a Schottky diode with 200–500 mV forward voltage at low power — at -20 dBm input, the RF peak voltage is only ~100 mV at 50 Ω, which is below the diode threshold; choose a zero-bias detector diode (e.g., SMS7630) with forward voltage < 150 mV.
- Ignoring the impedance mismatch between antenna (50 Ω) and non-linear rectifier (complex, load-dependent): the matching network must be re-optimized for each input power level; at minimum, tune it for -10 dBm (the main design point).
- Sizing the storage capacitor too small for the intended duty cycle — if the sensor wakes up every 10 seconds and draws 100 μA for 10 ms, the minimum capacitor is C = I × t / ΔV = 100e-6 × 10e-3 / 0.09 = 11 μF (allowing 5% voltage droop).
