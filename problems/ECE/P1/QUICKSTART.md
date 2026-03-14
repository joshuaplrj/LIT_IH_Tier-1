# RadarForge — Quick Start

## Objective
Design a complete FMCW radar system operating at 24 GHz capable of detecting small drones (RCS ≈ 0.01 m²) at ranges up to 500 m. Deliver a full system design document, signal processing simulation, and performance analysis as a JSON report.

## Inputs
- No external input files required; all parameters are defined in your design.
- Optional: `scenario.json` — drone trajectory parameters `{"range_m": float, "velocity_mps": float, "azimuth_deg": float, "rcs_m2": float}`

## Expected Output
- **Filename**: `submission.json`
- **Format**:
```json
{
  "system_design": {
    "center_freq_hz": 24e9,
    "bandwidth_hz": <float>,
    "chirp_duration_s": <float>,
    "num_chirps": <int>,
    "tx_power_dbm": <float>,
    "tx_rx_elements": {"tx": <int>, "rx": <int>},
    "mimo_virtual_elements": <int>
  },
  "performance": {
    "range_resolution_m": <float>,
    "velocity_resolution_mps": <float>,
    "max_range_m": <float>,
    "max_velocity_mps": <float>,
    "angular_resolution_deg": <float>,
    "snr_at_500m_db": <float>,
    "detection_probability_pct": <float>,
    "cfar_threshold_db": <float>
  },
  "signal_processing": {
    "range_fft_size": <int>,
    "doppler_fft_size": <int>,
    "cfar_type": "<CA-CFAR|OS-CFAR>",
    "angle_method": "<MUSIC|ESPRIT|Beamforming>"
  }
}
```

## Recommended First Steps
1. Open `starter.py` and run it to confirm the environment works — it will produce a placeholder `submission.json`.
2. Fill in `design_radar_system()`: compute bandwidth from range resolution formula `B = c / (2 * delta_R)`, chirp duration from velocity resolution, transmit power from the radar range equation.
3. Implement `range_doppler_processing()`: generate a simulated IF signal, apply windowing, run the 2D FFT, and read off peak location to extract range and velocity.

## Scoring Breakdown
| Metric                | Weight |
|-----------------------|--------|
| Range accuracy        | 30%    |
| Velocity accuracy     | 25%    |
| Angular resolution    | 25%    |
| SNR (link budget)     | 20%    |

## Common Pitfalls
- Forgetting to account for MIMO virtual aperture — with N_tx × N_rx elements the effective aperture is N_tx × N_rx, not N_rx alone.
- Using the wrong formula for max unambiguous range vs. range resolution — they depend on different parameters (PRI vs. bandwidth).
- Ignoring the ISM-band EIRP limit (typically +36 dBm in 24 GHz ISM) when computing transmit power; exceeding this invalidates the design.
- Setting chirp duration too short, which causes Doppler-range coupling artifacts in the 2D FFT.
- Choosing a CFAR guard cell count smaller than the range resolution cell spread, causing false detections.
