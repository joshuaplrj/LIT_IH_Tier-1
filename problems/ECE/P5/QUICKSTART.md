# WaveCraft — Quick Start

## Objective
Design a Software-Defined Radio (SDR) receiver architecture capable of simultaneously receiving and demodulating signals from at least 2 of the 5 target wireless standards (FM, DAB+, LTE, WiFi 6E, GPS L1) spanning 88 MHz to 7.125 GHz. Deliver a complete architecture document, DSP chain implementation, and performance metrics as a JSON report.

## Inputs
- No external input files required; all parameters are defined in your design.
- Optional: `scenario.json` — choose which standards to implement `{"standards": ["FM", "LTE"], "snr_db": float}`

## Expected Output
- **Filename**: `submission.json`
- **Format**:
```json
{
  "architecture": {
    "topology": "<direct_conversion|superheterodyne|direct_sampling>",
    "adc_sampling_rate_msps": <float>,
    "adc_enob": <float>,
    "rf_bandwidth_mhz": <float>,
    "image_rejection_db": <float>,
    "iq_imbalance_correction": <bool>
  },
  "analog_frontend": {
    "lna_noise_figure_db": <float>,
    "lna_gain_db": <float>,
    "frequency_range_mhz": {"min": <float>, "max": <float>},
    "lo_frequency_mhz": <float>,
    "phase_noise_dbc_per_hz_at_1khz": <float>
  },
  "digital_frontend": {
    "ddc_implemented": <bool>,
    "channelization_type": "<polyphase|fft|single_channel>",
    "sample_rate_conversion": <bool>
  },
  "standards_implemented": [
    {
      "name": "<FM|DAB+|LTE|GPS|WiFi>",
      "center_freq_mhz": <float>,
      "bandwidth_mhz": <float>,
      "demodulation": "<str>",
      "sensitivity_dbm": <float>,
      "selectivity_db": <float>,
      "ber_at_sensitivity": <float>
    }
  ],
  "performance": {
    "n_standards_implemented": <int>,
    "dynamic_range_db": <float>,
    "noise_figure_system_db": <float>
  }
}
```

## Recommended First Steps
1. Run `starter.py` to produce a placeholder `submission.json` and verify the environment.
2. Choose your architecture first — `direct_conversion` simplifies the RF chain but suffers from DC offset and LO leakage; `superheterodyne` needs careful IF frequency planning to avoid image problems.
3. Implement at least 2 demodulators: FM demodulation is a good starting point (frequency discriminator, ~5 lines of DSP), and LTE/GPS each demonstrate digital-heavy baseband processing.

## Scoring Breakdown
| Metric                      | Weight |
|-----------------------------|--------|
| Standard coverage (count)   | 35%    |
| Receiver sensitivity        | 30%    |
| Selectivity / rejection     | 20%    |
| Architecture quality        | 15%    |

## Common Pitfalls
- Trying to design one wideband ADC covering 88 MHz to 7.125 GHz — the ADC would need > 14 Gsps with > 10 ENOB, which does not exist in commercially viable form. You need band-selective front-end switching.
- Forgetting image rejection in a direct-conversion receiver — LO leakage causes DC offset; I/Q mismatch causes image at -2*f_offset.
- Setting ADC sampling rate too low for wideband standards — WiFi 6E at 160 MHz bandwidth needs ADC fs > 320 Msps.
- Implementing FM demodulation without de-emphasis (75 µs time constant) — correct FM audio requires a 6 dB/octave post-de-emphasis filter.
- Ignoring GPS acquisition complexity — GPS requires spreading code correlation over 1023 chips × multiple Doppler hypotheses (~1000 bins) before tracking loops can engage.
