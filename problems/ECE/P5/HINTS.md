# WaveCraft — Hints

> Each tier costs score points. Only request when genuinely stuck. Read all lower tiers before moving to the next.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This problem has two distinct phases: **RF/architecture design** and **digital baseband processing**. A common mistake is spending too much time on the RF architecture and too little on the baseband DSP.

The key architectural insight: you cannot cover 88 MHz to 7.125 GHz with a single direct-conversion path efficiently. The right approach is a **segmented/band-switching architecture** with:
- A low-band path (88–240 MHz) for FM and DAB+.
- A mid-band path (700 MHz–3.8 GHz) for GPS and LTE.
- A high-band path (5.9–7.2 GHz) for WiFi 6E.
- Each band uses a frequency-agile synthesiser (PLL) to downconvert to a common IF or directly to baseband.

For the 3-hour hackathon, focus on implementing **two strong demodulators** with full signal processing chains (including synchronisation, equalisation) rather than five shallow implementations. Scorers weight demonstrated implementation quality over quantity.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Architecture comparison:**
- **Direct conversion (zero-IF)**: LO at carrier, outputs I and Q at baseband. Pros: simple, no image. Cons: DC offset (LO self-mixing), I/Q imbalance, 1/f noise.
- **Low-IF conversion**: LO slightly offset from carrier, IF = 1–2× channel bandwidth. Pros: avoids DC offset. Cons: image rejection challenge.
- **Direct sampling**: wideband ADC directly samples RF. Requires ADC with very high sample rate and ENOB. Only feasible up to ~3 GHz with current technology.

Recommended: **Direct conversion with digital I/Q correction** for each band segment.

**FM demodulation** (simplest to implement):
- Received baseband: `r(t) = cos(2*pi*fc*t + 2*pi*kf*∫m(τ)dτ)`
- After I/Q downconversion: `I + jQ = A * exp(j*phi(t))`
- Frequency discriminator: `m_hat(t) = (1/(2*pi*kf)) * d/dt[arg(I + jQ)]`
- In discrete time: `phi_diff[n] = angle(conj(x[n-1]) * x[n])`
- Then: apply low-pass audio filter, de-emphasis (IIR: H(z) = (1-z^(-1)) / (1-a*z^(-1)), a = exp(-1/(tau*fs))), stereo pilot decode (38 kHz sub-carrier).

**LTE OFDM demodulation:**
- OFDM with 15 kHz subcarrier spacing, cyclic prefix = 4.7 µs (normal CP).
- Steps: (1) timing sync (PSS/SSS correlation), (2) frequency sync (from PSS), (3) CP removal, (4) N-point FFT, (5) channel estimation from CRS pilots, (6) ZF equalization, (7) QAM demapping.
- PSS sequences: 3 root Zadoff-Chu sequences (roots u=25, 29, 34).

**GPS L1 C/A acquisition:**
- Signal structure: 1.023 Mcps spreading code (1023-chip PRN sequence), 50 bps navigation message, BPSK modulation.
- Acquisition: 2D search over code phase (1023 bins) × Doppler (±10 kHz / 500 Hz step = 40 bins). Use FFT-based parallel code search.
- After acquisition: DLL (delay-locked loop) for code tracking, PLL (phase-locked loop) for carrier tracking.
- Navigation solution: requires at least 4 satellites; collect ephemeris, solve pseudorange equations.

**Sensitivity and selectivity:**
- Sensitivity: `MDS = kTB + NF + SNR_min` (minimum detectable signal). For FM: NF=5 dB, B=200 kHz, SNR=10 dB → MDS = -174 + 10*log10(200e3) + 5 + 10 ≈ -96 dBm.
- Selectivity: measured as adjacent-channel rejection. For LTE, rejection ≥ 30 dB is required; achieved by the channel-select digital filter after DDC.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation:**

1. **Architecture definition** (`design_architecture()`):
   - Choose direct conversion for simplicity.
   - ADC requirements: for LTE (20 MHz bandwidth), ADC fs >= 40 Msps, ENOB >= 11 bits. For WiFi (160 MHz), fs >= 320 Msps.
   - Image rejection: use quadrature (I/Q) mixing → image rejection = `20*log10(1/epsilon_iq)` where epsilon_iq is I/Q imbalance. Target: 40–60 dB.
   - LNA: wideband LNA with NF < 3 dB, gain ~20 dB. Example: use switched LNA stages for each band with a common output buffer.

2. **FM demodulator** (`demodulate_fm()`):
   ```python
   # 1. Downconvert to baseband (already done by SDR)
   # 2. FM discriminator
   phi_diff = np.angle(np.conj(iq_signal[:-1]) * iq_signal[1:])
   audio = phi_diff / (2 * np.pi * max_deviation / sample_rate)
   # 3. De-emphasis filter (75 µs)
   tau = 75e-6
   alpha = np.exp(-1 / (tau * fs))
   audio_de_emp = lfilter([1 - alpha], [1, -alpha], audio)
   # 4. Downsample to 48 kHz audio
   ```

3. **GPS acquisition** (`gps_acquisition()`):
   - Generate all 32 GPS PRN codes using the CA code generator (generator polynomial: g1 = x^10+x^3+1, g2 = x^10+x^9+x^8+x^6+x^3+x^2+1; output = g1_output XOR g2_output delayed by satellite-specific taps).
   - Correlate received signal with each PRN code across all code phases using FFT: `correlation = IFFT(FFT(signal) * conj(FFT(code)))`.
   - Search for Doppler by repeating at each frequency hypothesis.
   - Detection: peak-to-noise ratio > 3 dB indicates acquisition.

4. **LTE synchronisation** (`lte_pss_sync()`):
   - Generate PSS sequences (Zadoff-Chu root 25/29/34, length 62).
   - Cross-correlate received signal with PSS to find frame timing and NID2.
   - Frequency offset from PSS correlation angle.

5. **Digital front-end** (`digital_frontend()`):
   - DDC: numerically controlled oscillator (NCO) generates `exp(j*2*pi*f_lo*n/fs)`, multiply with ADC samples to shift band to baseband.
   - CIC filter for decimation (first coarse stage), then half-band FIR filters.
   - Channelizer: polyphase filter bank — for M channels, use `M`-point DFT of `M` polyphase branches.

6. **Populate submission.json** with architecture parameters and per-standard performance metrics (sensitivity, selectivity, BER at sensitivity point).
