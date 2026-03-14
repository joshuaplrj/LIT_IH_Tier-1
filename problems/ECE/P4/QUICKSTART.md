# ChipCraft — Quick Start

## Objective
Design a mixed-signal ASIC analog front-end for a wearable ECG + PPG biosensor: ECG channel with 16-bit SAR ADC (1 kSPS per channel, total power < 500 µW across all 8 channels). Deliver a complete circuit design, simulation results, and performance metrics as a JSON report.

## Inputs
- No external input files required; all circuit parameters are defined in your design.
- Optional: `scenario.json` — override process/supply parameters `{"vdd_v": float, "process_node_nm": int, "temperature_c": float}`

## Expected Output
- **Filename**: `submission.json`
- **Format**:
```json
{
  "ecg_channel": {
    "ina_gain_db": <float>,
    "input_impedance_ohm": <float>,
    "cmrr_db": <float>,
    "input_referred_noise_uvrms": <float>,
    "bandwidth_hz": <float>,
    "power_uw": <float>
  },
  "ppg_channel": {
    "tia_transimpedance_kohm": <float>,
    "led_drive_current_ma": <float>,
    "snr_db": <float>,
    "ambient_rejection_db": <float>,
    "power_uw": <float>
  },
  "sar_adc": {
    "resolution_bits": 16,
    "sampling_rate_ksps": 1.0,
    "enob_bits": <float>,
    "inl_lsb": <float>,
    "dnl_lsb": <float>,
    "sndr_db": <float>,
    "power_uw_per_channel": <float>
  },
  "biasing": {
    "bandgap_voltage_v": <float>,
    "reference_accuracy_ppm_per_c": <float>,
    "bias_current_na": <float>
  },
  "power_budget": {
    "ecg_total_uw": <float>,
    "ppg_total_uw": <float>,
    "adc_8ch_total_uw": <float>,
    "biasing_uw": <float>,
    "total_afe_uw": <float>
  }
}
```

## Recommended First Steps
1. Run `starter.py` to produce a placeholder `submission.json` and verify the environment.
2. Implement `design_sar_adc()`: start by sizing the capacitor DAC — total capacitance = `C_unit * 2^N` where N = 16 and C_unit targets the kT/C noise floor below 0.5 LSB.
3. Implement `design_ecg_frontend()`: an instrumentation amplifier (INA) requires `CMRR > 100 dB`. The classic 3-op-amp INA topology achieves CMRR limited by resistor matching. Estimate the required resistor matching tolerance.

## Scoring Breakdown
| Metric               | Weight |
|----------------------|--------|
| ADC linearity        | 30%    |
| Power consumption    | 30%    |
| Noise floor          | 25%    |
| Layout quality       | 15%    |

## Common Pitfalls
- Sizing the SAR ADC capacitor DAC without checking kT/C noise — for 16-bit resolution, `C_unit > kT / (Vref^2 / 12)` sets the minimum capacitance per unit cell.
- Achieving 100 dB CMRR with a simple diff-amp — the 3-op-amp INA topology needs all four resistors matched to within 0.001% for 100 dB CMRR; standard resistors (0.1%) only give 66 dB.
- Ignoring flicker (1/f) noise in the ECG band — at 0.05–150 Hz, flicker noise dominates MOS transistors; chopper stabilisation or correlated double sampling are required to meet < 5 µVrms.
- Budgeting ADC power without the CDAC reference charging current — most of the SAR ADC power comes from charging the 64 fF–1 pF capacitors to Vref each cycle.
- Forgetting digital logic power in the SAR ADC — the SAR controller and register flip-flops contribute ~20–30% of total ADC power.
