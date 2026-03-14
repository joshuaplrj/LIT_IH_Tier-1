# VibeKill — Quick Start

## Objective
Design an active vibration control system for a CNC milling machine that suppresses regenerative chatter in the 250–400 Hz range during titanium alloy (Ti-6Al-4V) machining. The system must achieve > 20 dB attenuation at chatter frequencies without reducing static stiffness by more than 10%.

## Inputs
- **Chatter frequency range**: 250–400 Hz (dominant mode: tool overhang dependent)
- **Target surface roughness**: Ra < 0.8 μm (current without control: Ra > 3.2 μm)
- **Workpiece material**: Ti-6Al-4V (difficult to machine: low thermal conductivity, high strength at temperature)
- **Actuation options**: Piezoelectric on spindle housing, active magnetic bearings, electromagnetic shakers, or adaptive spindle speed control
- **Control bandwidth requirement**: DC to 500 Hz (must not affect static stiffness at 0 Hz)
- **Attenuation target**: > 20 dB reduction in vibration amplitude at chatter frequencies
- **Static stiffness preservation**: > 90% of original stiffness

## Expected Output
A file named `report.json` with the following top-level keys:
```json
{
  "actuator_type": "<string>",
  "sensor_type": "<string>",
  "control_algorithm": "FxLMS | H_infinity | PID | other",
  "chatter_frequency_Hz": <float>,
  "attenuation_dB": <float>,
  "control_bandwidth_Hz": <float>,
  "static_stiffness_preservation_pct": <float>,
  "response_time_ms": <float>,
  "stability_margin_dB": <float>,
  "phase_margin_deg": <float>,
  "actuator_force_N": <float>,
  "actuator_stroke_um": <float>,
  "controller_sampling_rate_Hz": <float>,
  "open_loop_fn_Hz": [<float>, ...],
  "closed_loop_fn_Hz": [<float>, ...]
}
```

## Recommended First Steps
1. Build a 1-DOF dynamic model of the spindle-tool system: `m*x_ddot + c*x_dot + k*x = F_cut + F_actuator`. Identify k from a typical spindle stiffness of 50 N/μm and estimate m from modal mass (typically 0.5–2 kg for a CNC spindle).
2. Compute the open-loop natural frequency `fn = sqrt(k/m) / (2*pi)` and verify it falls in or near the 250–400 Hz chatter band, then derive the required damping ratio to achieve 20 dB attenuation.
3. Size the piezoelectric actuator: the required force `F_act = 2 * zeta_target * sqrt(k*m) * v_max` where v_max is peak velocity amplitude during chatter.

## Scoring Breakdown
| Metric                | Weight |
|-----------------------|--------|
| Attenuation Achieved  | 40%    |
| Control Stability     | 25%    |
| Response Time         | 20%    |
| Design Quality        | 15%    |

## Common Pitfalls
- Designing a controller with high gain at chatter frequencies but neglecting spillover: energy pushed out of the 250–400 Hz band can excite higher structural modes at 600–1000 Hz if the controller has insufficient roll-off.
- Confusing open-loop and closed-loop stability — a positive real part of any closed-loop pole means instability; always check phase margin >= 30° and gain margin >= 6 dB.
- Using a static stiffness formulation but missing the dynamic stiffness: the actuator adds active stiffness at low frequency only if the controller has an integrating term; a pure derivative (velocity feedback) adds damping but not stiffness.
