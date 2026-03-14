# PhotonLink — Quick Start

## Objective
Design a Free-Space Optical (FSO) communication link at 1550 nm between two buildings 5 km apart, achieving 10 Gbps throughput at BER 10^-9 with 99.9% availability despite fog, rain, turbulence, and pointing errors. Deliver a complete system design and simulation as a JSON report.

## Inputs
- No external input files required; all channel parameters are defined in your design.
- Optional: `scenario.json` — override atmospheric conditions `{"visibility_m": float, "rain_rate_mmhr": float, "Cn2": float, "wind_speed_mps": float}`

## Expected Output
- **Filename**: `submission.json`
- **Format**:
```json
{
  "link_budget": {
    "tx_power_dbm": <float>,
    "beam_divergence_mrad": <float>,
    "rx_aperture_diameter_m": <float>,
    "geometric_loss_db": <float>,
    "fog_attenuation_db": <float>,
    "rain_attenuation_db": <float>,
    "scintillation_sigma_i2": <float>,
    "pointing_loss_db": <float>,
    "total_loss_db": <float>,
    "received_power_dbm": <float>,
    "receiver_sensitivity_dbm": <float>,
    "link_margin_db": <float>
  },
  "channel_model": {
    "visibility_m": <float>,
    "rain_rate_mmhr": <float>,
    "Cn2_m_neg2_thirds": <float>,
    "rytov_variance": <float>,
    "turbulence_regime": "<weak|moderate|strong>",
    "fried_parameter_r0_m": <float>
  },
  "diversity": {
    "n_tx_apertures": <int>,
    "n_rx_apertures": <int>,
    "diversity_gain_db": <float>
  },
  "adaptive_optics": {
    "n_actuators": <int>,
    "wavefront_sensor": "<str>",
    "correction_bandwidth_hz": <float>,
    "residual_wavefront_error_nm": <float>
  },
  "performance": {
    "ber_clear_sky": <float>,
    "ber_with_fog_attenuation": <float>,
    "availability_pct": <float>,
    "modulation": "<OOK|PPM|DPSK|BPSK>"
  }
}
```

## Recommended First Steps
1. Run `starter.py` to confirm the environment produces a placeholder `submission.json`.
2. Implement `fog_attenuation_kim_model()`: the Kim model gives specific attenuation from visibility — `alpha = 3.91/V * (lambda/550nm)^(-q)` where q depends on visibility range.
3. Implement `compute_link_budget()`: sum all losses (geometric, fog, rain, scintillation, pointing) and compare received power against receiver sensitivity to find the link margin.

## Scoring Breakdown
| Metric                        | Weight |
|-------------------------------|--------|
| BER performance               | 35%    |
| Atmospheric model accuracy    | 30%    |
| Adaptive compensation design  | 25%    |
| Link budget completeness      | 10%    |

## Common Pitfalls
- Treating fog attenuation as negligible — at 50 m visibility, Kim model gives >200 dB/km at 1550 nm, making 5 km simply unworkable without hybrid backup.
- Confusing Rytov variance (weak turbulence approximation) with the gamma-gamma distribution parameters (which apply to all turbulence regimes).
- Using plane-wave Rytov variance instead of spherical-wave Rytov variance — for a 5 km FSO link, the spherical-wave form is more accurate.
- Ignoring pointing loss — 1 mrad RMS building sway on a narrow optical beam causes significant power loss; this must be included in the link budget.
- Forgetting that 99.9% availability means you need a hybrid RF/FSO backup, not just a larger optical margin (fog is too severe).
