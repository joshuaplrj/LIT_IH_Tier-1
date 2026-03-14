# MIMO-Sat — Quick Start

## Objective
Design a complete LEO satellite communication link at 550 km orbit altitude using Ku-band (12/14 GHz) to deliver 100 Mbps downlink and 10 Mbps uplink at BER 10^-6. Deliver a full link budget, modulation/coding selection, beamforming design, and Doppler analysis as a JSON report.

## Inputs
- No external input files required; all parameters are defined in your design.
- Optional: `scenario.json` — override link parameters `{"elevation_deg": float, "rain_rate_mmhr": float, "modulation": str, "code_rate": float}`

## Expected Output
- **Filename**: `submission.json`
- **Format**:
```json
{
  "link_budget": {
    "downlink": {
      "path_loss_db": <float>,
      "eirp_dbw": <float>,
      "g_over_t_db_per_k": <float>,
      "rain_attenuation_db": <float>,
      "received_snr_db": <float>,
      "eb_n0_db": <float>
    },
    "uplink": { ... same fields ... }
  },
  "modcod": {
    "modulation": "<QPSK|8PSK|16APSK|32APSK>",
    "fec_code": "<LDPC|Turbo|Polar>",
    "code_rate": <float>,
    "spectral_efficiency_bps_per_hz": <float>,
    "required_eb_n0_db": <float>
  },
  "beamforming": {
    "array_elements": 256,
    "beam_gain_db": <float>,
    "scan_loss_db_at_60deg": <float>,
    "half_power_beamwidth_deg": <float>
  },
  "doppler": {
    "max_doppler_shift_hz": <float>,
    "compensation_method": "<str>",
    "residual_frequency_error_hz": <float>
  },
  "availability": {
    "link_margin_db": <float>,
    "availability_pct": <float>
  }
}
```

## Recommended First Steps
1. Run `starter.py` to produce a placeholder `submission.json` and verify the environment.
2. Implement `compute_path_loss()`: free-space path loss is `FSPL = 20*log10(4*pi*R*f/c)` where R is slant range from orbit altitude and elevation angle.
3. Implement `link_budget_downlink()`: sum up all gains and losses (EIRP, FSPL, atmospheric, rain, G/T) to get Eb/N0, then verify against the required Eb/N0 for your chosen modcod.

## Scoring Breakdown
| Metric                   | Weight |
|--------------------------|--------|
| Link budget accuracy     | 30%    |
| MIMO / array capacity    | 30%    |
| Beamforming design       | 25%    |
| Documentation / analysis | 15%    |

## Common Pitfalls
- Using vertical-path rain attenuation instead of slant-path — multiply by `1/sin(elevation)` for the slant range correction.
- Forgetting scan loss in the phased array gain formula — gain decreases as `cos(theta)` for a flat array scanned to elevation angle theta.
- Ignoring the satellite velocity component along the LOS when computing Doppler — the full Doppler is `f_d = (2*v*cos(gamma)/lambda)` where gamma is the angle between velocity vector and LOS.
- Misusing noise temperature — G/T must use system noise temperature (antenna + LNA + feed losses), not just LNA noise figure.
- Treating 256-element array gain as 10*log10(256) without accounting for element efficiency, mutual coupling, or scan loss.
