# VibeKill — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
The problem is a **self-excited vibration** (regenerative chatter), not a simple forced vibration. The cutting force at time t depends on the surface left by the previous tooth pass — creating a delayed feedback loop. Your active control system must add damping specifically in the 250–400 Hz band without destabilising other modes. The clearest path is **piezoelectric direct velocity feedback (DVF)**: mount a piezoelectric actuator on the spindle housing, sense spindle velocity with an accelerometer (integrate in software), and feed back with gain to actively increase damping. DVF is unconditionally stable for collocated actuator-sensor pairs — a huge practical advantage.

## Tier 2 — Technique Guidance (-10% score penalty)
**Chatter stability criterion** (Tobias/Tlusty 1D model):
```
b_lim = -1 / (2 * N_teeth * Re[G(j*omega_c)] * Ks)
```
where `b_lim` = limiting axial depth of cut, `N_teeth` = number of teeth, `Ks` = specific cutting force (Ti-6Al-4V: ~2,000 N/mm²), `G(j*omega_c)` = frequency response function (FRF) of the structure at chatter frequency.

Adding active damping modifies G(jω) by increasing the imaginary part at resonance, making `Re[G]` less negative, thus increasing `b_lim` (the stable depth).

**FRF of a 1-DOF system**:
```
G(jω) = 1 / (k - m*ω^2 + j*c*ω)
```
The minimum real part (most negative) occurs at `ω = ω_n * sqrt(1 - 2*zeta^2)`.

**DVF (Direct Velocity Feedback) control law**:
```
F_act = -g_dvf * v(t)     [v = spindle velocity]
```
Effective damping coefficient: `c_eff = c + g_dvf`. No stability analysis needed for collocated system.

**Required attenuation (20 dB)**:
```
20 dB = 20 * log10(|G_open| / |G_closed|)
=> |G_closed| = |G_open| / 10
```
This requires increasing the damping ratio from a typical ζ = 0.02 (bare spindle) to approximately ζ = 0.20.

**Actuator sizing**:
```
F_act_peak = g_dvf * v_max = g_dvf * (A_vib * ω_n)
```
Choose piezo stack actuator: typical PI P-844 series provides 800 N force, 30 μm stroke. Preloaded against the spindle housing.

## Tier 3 — Implementation Guidance (-15% score penalty)
Step-by-step calculation sequence:

1. **Identify 1-DOF spindle model**:
   - Stiffness: k = 50 N/μm = 50×10⁶ N/m (typical CNC spindle)
   - Modal mass: m = k / (2π × fn)² = 50×10⁶ / (2π × 300)² ≈ 0.141 kg
   - Damping (bare): ζ = 0.02 → c = 2 × ζ × sqrt(k × m) = 2 × 0.02 × sqrt(50e6 × 0.141) ≈ 336 N·s/m

2. **Target closed-loop damping for 20 dB**:
   - At resonance, peak FRF = 1/(2ζk). For 20 dB attenuation: ζ_cl = 10 × ζ_ol = 0.20
   - Required added damping: Δc = 2 × (ζ_cl - ζ_ol) × sqrt(k×m) = 2 × 0.18 × sqrt(7.05×10⁶) ≈ 956 N·s/m
   - DVF gain: g_dvf = Δc = 956 N·s/m

3. **Actuator force requirement**:
   - Typical chatter amplitude before control: A = 20 μm (0-peak)
   - Peak velocity: v_max = A × ω_n = 20×10⁻⁶ × 2π × 300 ≈ 0.038 m/s
   - Peak force: F = g_dvf × v_max = 956 × 0.038 ≈ 36 N
   - Select PI P-844.10 (800 N force, 15 μm stroke) — adequate with large margin.

4. **Controller implementation** (digital, 10 kHz sampling):
   - Discrete integrator (trapezoidal) for acceleration → velocity
   - Low-pass filter at 600 Hz to limit high-frequency gain (prevents spillover)
   - Phase compensation: all-pass filter to correct for actuator dynamics (resonance ~5 kHz)

5. **Stability margins** — plot Nyquist diagram of L(jω) = G(jω) × C(jω) × H_act(jω):
   - Phase margin target: ≥ 45°
   - Gain margin target: ≥ 10 dB
   - With DVF + low-pass filter at 600 Hz: both margins typically met.

6. **Response time**: settling time of damped system ≈ 4/(ζ_cl × ω_n) = 4/(0.20 × 2π × 300) ≈ 10.6 ms — meets any practical requirement.
