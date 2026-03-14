# RadarForge — Hints

> Each tier costs score points. Only request when genuinely stuck. Read all lower tiers before moving to the next.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

The problem is fundamentally a **radar systems engineering** challenge, not just a signal processing one. You need two parallel workstreams:

1. **Link budget / system design**: Determine whether the radar can physically detect a 0.01 m² target at 500 m given legal ISM-band power limits. Work through the radar range equation — it tells you the received SNR as a function of range, transmit power, antenna gain, and target RCS.

2. **Waveform design**: The FMCW chirp parameters (bandwidth, chirp duration, number of chirps) jointly determine range resolution, velocity resolution, and the maximum unambiguous range and velocity. These four quantities are coupled — improving one often degrades another.

Focus on meeting all six system requirements simultaneously rather than optimising any single one.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Waveform parameter design** follows from three equations:
- Range resolution: `delta_R = c / (2B)` → choose bandwidth B.
- Velocity resolution: `delta_v = lambda / (2 * N_chirps * T_chirp)` → choose N_chirps × T_chirp.
- Max unambiguous range: `R_max = c * T_chirp / 2` (must be ≥ 500 m).
- Max unambiguous velocity: `v_max = lambda / (4 * T_chirp)` (must cover drone speeds).

**SNR and link budget**: Use the radar range equation in the form:
`SNR = (P_t * G_t * G_r * lambda^2 * sigma) / ((4*pi)^3 * R^4 * k * T * B_n * F * L)`
where sigma = 0.01 m², R = 500 m. A MIMO virtual array of N_tx × N_rx elements improves angular resolution to `theta = lambda / (N_virt * d)` and provides array gain.

**CFAR detection**: CA-CFAR is appropriate for uniform clutter. Use ~16–32 reference cells and 2–4 guard cells per side. The threshold multiplier sets the Pfa; derive it analytically for Pfa = 10⁻⁶.

**Angle estimation**: MUSIC applied to the MIMO virtual array covariance matrix gives sub-degree resolution when SNR is adequate. ESPRIT is computationally cheaper for real-time use.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation sequence:**

1. **Parameter calculation** (fill `design_radar_system()`):
   - Set `B = c / (2 * 1.0)` for 1 m range resolution → B ≈ 150 MHz.
   - Set `T_chirp` such that `R_max = c * T_chirp / 2 ≥ 500 m` → T_chirp ≥ 3.33 µs; use ~20–40 µs to give headroom.
   - Set `N_chirps` so velocity resolution ≤ 0.5 m/s: `N_chirps ≥ lambda / (2 * 0.5 * T_chirp)`.
   - Verify frame duration = `N_chirps * T_chirp ≤ 100 ms`.

2. **IF signal generation** (fill `generate_if_signal()`):
   - For a target at range R and velocity v, the IF beat frequency is `f_beat = 2 * B * R / (c * T_chirp)` and the Doppler shift is `f_d = 2 * v / lambda`.
   - Generate complex exponentials for each chirp: `s[n, m] = exp(j*2*pi*(f_beat*t_fast + f_d*m*T_chirp))` plus AWGN.

3. **2D FFT processing** (fill `range_doppler_processing()`):
   - Apply a window (Hanning or Blackman-Harris) along both axes before FFT.
   - `range_doppler_map = fftshift(fft2(windowed_signal * window2d))`.
   - Convert bin indices to physical range and velocity using the calibration factors.

4. **CFAR detection**:
   - Implement sliding-window CA-CFAR: for each cell under test, average the power in the reference window (excluding guard cells), multiply by threshold factor alpha.
   - `alpha = N_ref * (Pfa^(-1/N_ref) - 1)` for CA-CFAR.

5. **Angle estimation**:
   - Stack snapshots from the MIMO virtual array at the detected range-Doppler bin.
   - Compute the spatial covariance matrix R = (1/K) * X * X^H.
   - Apply MUSIC: form the noise subspace from the K−1 smallest eigenvalues, sweep a steering vector across azimuth angles, find spectral peaks.

6. **Output**: Populate the `submission.json` fields with computed values; include measured range/velocity/angle errors from simulation.
