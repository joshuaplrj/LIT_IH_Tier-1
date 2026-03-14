# ChipCraft — Hints

> Each tier costs score points. Only request when genuinely stuck. Read all lower tiers before moving to the next.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This problem is about **ultra-low-power analog/mixed-signal IC design** for a bio-signal sensing ASIC. There are four major blocks, each with its own design challenge:

1. **ECG instrumentation amplifier (INA)**: The challenge is simultaneously achieving very high input impedance (> 10 GΩ), very low noise (< 5 µVrms), and very high CMRR (> 100 dB) at a power budget under ~100 µW for the whole ECG channel. These three requirements are in tension — reducing power increases noise; achieving 100 dB CMRR requires precision resistor matching.

2. **PPG transimpedance amplifier (TIA)**: The input is a photodiode current (100 pA to 10 µA — 5 decades of range). The challenge is noise (must beat the shot noise of the photodiode current), ambient light rejection, and the LED drive pulse synchronisation.

3. **16-bit SAR ADC**: At 1 kSPS, there is a lot of time available per conversion (1 ms for 16 cycles) — you don't need a high-speed design. The challenge is power (< 50 µW per channel) and achieving 14+ ENOB, which is limited by kT/C noise and comparator noise.

4. **Bandgap reference and biasing**: The stability of the ADC reference directly affects linearity. A well-designed bandgap should give < 20 ppm/°C temperature coefficient.

Work through each block sequentially, compute power for each, and check the total budget.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**SAR ADC design:**
- The capacitor DAC (CDAC) is the central element. With N = 16 bits and Vref = 1 V, 1 LSB = Vref / 2^N ≈ 15.3 µV.
- Minimum capacitance for kT/C noise ≤ 0.5 LSB: `C_unit ≥ kT * 2^(2N) / Vref^2`. For N=16, T=300K, Vref=1V: `C_unit ≥ 1.38e-23 * 300 * 2^32 / 1 ≈ 17.7 fF`. In practice, use 20–50 fF for margin.
- Total CDAC capacitance: `C_total = C_unit * (2^N - 1) ≈ C_unit * 65535`.
- Power from CDAC charging: `P_CDAC ≈ C_total * Vref^2 * fs * N` (energy per cycle × sample rate × bits). With C_unit = 30 fF, P_CDAC ≈ 30e-15 * 65535 * 1 * 1e3 * 16 ≈ 31 nW — very manageable.
- ENOB is limited by comparator noise: require `σ_comp ≤ 0.5 LSB = Vref / 2^(N+1)`. For 16-bit, σ_comp ≤ 7.6 µV. This is achievable with a dynamic latch comparator.

**ECG INA design:**
- Use the 3-op-amp INA topology. The first stage (two input op-amps with gain resistor Rg) provides high CMRR if mismatches in the second-stage (differential) are small.
- CMRR = 20*log10(A_diff / A_cm). For the 3-op-amp INA: `CMRR ≈ (1 + 2*R1/Rg) * resistor_CMRR`, where resistor_CMRR = ratio_mismatch^(-1).
- For 100 dB CMRR with gain = 100 (40 dB): need `CMRR_resistors ≥ 100 dB - 40 dB = 60 dB`, meaning 0.1% matched resistors are sufficient if trimmed/laser-trimmed.
- Noise: for an instrumentation amplifier with gain G, `IRN = sqrt(2 * en_amp^2 + (2 * in_amp * Rs)^2) / G`. At low frequencies, use chopper-stabilised op-amps to eliminate 1/f noise.

**PPG TIA:**
- Transimpedance gain: `Z_T = Rf` (feedback resistor). For minimum photodiode current I_min = 100 pA and minimum detectable output ≈ 1 mV, `Rf ≥ 1e-3 / 100e-12 = 10 MΩ`.
- Bandwidth: `f_-3dB = 1 / (2*pi * Rf * Cf)`. For bandwidth > 1 kHz (PPG signal), `Cf ≤ 1 / (2*pi * 10e6 * 1000) ≈ 16 pF`.
- Shot noise current: `in_shot = sqrt(2 * q * Idc * B)`. For I_dc = 1 µA, B = 1 kHz: `in_shot ≈ 0.57 pA/√Hz`.
- Ambient light rejection: use synchronous detection (lock-in) with LED modulated at 50 kHz. Low-pass filter rejects DC ambient.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**SAR ADC step-by-step:**

1. **CDAC sizing** (`design_sar_adc()`):
   - Set C_unit = 30 fF (safe margin above kT/C requirement).
   - Total capacitance: `C_total = C_unit * sum(2^i for i in range(16)) = C_unit * 65535 ≈ 1.97 pF`.
   - CDAC power: `P_CDAC = 0.5 * C_total * Vref^2 * fs * N` (average switching energy).
   - Comparator dynamic power: `P_comp = C_L * Vdd^2 * fs * N * log2(N)` (rough estimate).

2. **Linearity (ENOB, INL, DNL)**:
   - INL arises from capacitor mismatch. For unit capacitance σ(C)/C = 1%, the maximum INL ≈ `sqrt(2^N) * σ(C)/C * 2^N` in LSBs. This is why matching matters.
   - Monte Carlo estimate: draw N_CDAC cap values from N(C_unit, sigma_C), simulate the DAC transfer function, compute INL/DNL.
   - ENOB = `(SNDR - 1.76) / 6.02` where SNDR is signal-to-noise-and-distortion ratio.

3. **ECG INA** (`design_ecg_frontend()`):
   - First stage: two op-amps, gain = `1 + 2*R1/Rg`. Choose Rg for desired gain (e.g., Rg = 2 kΩ, R1 = 100 kΩ → gain = 101).
   - Second stage: differential amp with gain = R3/R2. Overall gain must be ~100–1000 for ECG signals (0.5 mV) to fill ADC range (1V).
   - Noise: dominant contributor at low freq is 1/f noise of input transistors. Use large PMOS input pair (larger W*L → lower 1/f corner). Or use chopper stabilisation: modulate input at f_chop > 1/f corner.
   - Power: for a class-AB op-amp, `P = Vdd * I_bias * N_opamps`. Minimise bias current while meeting noise spec.

4. **PPG TIA** (`design_ppg_frontend()`):
   - TIA with Rf = 10 MΩ, Cf = 10 pF for bandwidth.
   - Sample-and-hold on LED-on phase. LED drive: 20 mA for 100 µs pulse → duty cycle = 10% if PRF = 1 kHz.
   - LED power: `P_LED = I_LED * Vf * duty_cycle` where Vf ≈ 1.8 V (red/IR LED).

5. **Power budget** (`compute_power_budget()`):
   - Sum: P_INA + P_LPF + P_HPF + P_TIA + P_LED + P_ADC_x8 + P_bias.
   - Must be < 500 µW total. Typical breakdown: INA 50 µW, TIA 30 µW, LED ~36 µW average, ADC 8×40 µW = 320 µW, bias 20 µW → total ~456 µW.

6. **Populate submission.json** with all design values and computed performance metrics.
