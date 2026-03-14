# PowerShield — Quick Start

## Objective
Design a solid-state circuit breaker (SSCB) for a 400 V DC microgrid rated at 200 A continuous, capable of interrupting a 10 kA fault in under 100 μs from detection to current zero. The design must be bidirectional, limit transient overvoltage to < 600 V, and survive 10,000 switching cycles.

## Inputs

This is a hardware design problem — no pre-existing data files are required. Your inputs are the specifications below:

| Parameter              | Requirement                  |
|------------------------|------------------------------|
| System voltage         | 400 V DC                     |
| Rated current          | 200 A continuous             |
| Breaking capacity      | 10 kA at 400 V DC            |
| Breaking time          | < 100 μs (detection to interrupt) |
| Bidirectional          | Both current directions       |
| Voltage clamping       | Transient overvoltage < 600 V |
| Switching endurance    | 10,000 cycles                 |

## Expected Output

**Filename:** `submission/sscb_design_report.json`

Top-level keys required:

- `semiconductor_selection` — device type (SiC MOSFET / IGBT / hybrid), part number, justification
- `topology` — circuit topology description, number of devices in series/parallel
- `snubber_clamping` — component type (MOV / RC / active clamp), values, clamping voltage
- `gate_driver` — turn-off time target, gate resistance, negative gate voltage for fast turn-off
- `fault_detection` — detection method, threshold, detection time (μs)
- `thermal_design` — heat sink thermal resistance, steady-state and fault junction temperature
- `simulation_results` — waveform arrays: current vs. time, voltage vs. time during fault interruption
- `bom` — list of components with estimated unit cost
- `timing_breakdown` — detection_us, gate_delay_us, rise_fall_us, total_us

## Recommended First Steps

1. Run `python starter.py` — it simulates the fault interruption transient using a simple RL circuit model and prints whether the 100 μs timing budget is met.
2. Review the semiconductor selection section: the script defaults to SiC MOSFETs — adjust the device parameters (Rds_on, Coss, gate charge) to match a real part from the Wolfspeed or STMicroelectronics catalog.
3. Check the clamping voltage output — if the MOV clamping voltage exceeds 600 V, reduce the MOV clamping ratio or add an active clamp circuit.

## Scoring Breakdown

| Metric                      | Weight |
|-----------------------------|--------|
| Interrupt time (target < 100 μs, full marks < 10 μs) | 35% |
| Protection accuracy (correct fault detection, no nuisance trips) | 30% |
| Efficiency (conduction + switching losses at rated load) | 20% |
| Design quality (BOM completeness, thermal analysis, documentation) | 15% |

## Common Pitfalls

- Calculating device turn-off time from datasheet fall time only — the actual current fall time depends on the circuit inductance L and the gate driver speed: di/dt = V_gs_off / L. A stray inductance of 100 nH can add 5–20 μs to the interrupt time.
- Sizing the MOV for the fault energy incorrectly — the MOV must absorb E = 0.5 × L_fault × I_fault² joules; underspecifying the MOV leads to thermal runaway.
- Ignoring bidirectional requirement — a single MOSFET blocks only one direction via its body diode; you need two back-to-back MOSFETs (common-source or common-drain) for true bidirectional breaking.
