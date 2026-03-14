# PhotonLink — Hints

> Each tier costs score points. Only request when genuinely stuck. Read all lower tiers before moving to the next.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This problem sits at the intersection of **optical communications, atmospheric physics, and adaptive optics**. There are four distinct impairments, and you must model all of them:

1. **Geometric loss** — optical beam spreading over 5 km. Unlike RF, this is set by the transmitter's beam divergence and the receiver's aperture area, not by a fixed path-loss formula.
2. **Atmospheric attenuation** — fog is catastrophic (>100 dB/km), rain is moderate (~0.5 dB/km at 50 mm/hr), clear-air absorption is small.
3. **Scintillation** — turbulence-induced amplitude fluctuations cause deep, rapid fades. The statistics are described by the log-normal distribution (weak turbulence) or gamma-gamma distribution (all regimes).
4. **Pointing errors** — building sway of ±1 mrad displaces the beam. For a narrow beam, even 1 mrad can cause significant loss.

The key insight: **fog makes a pure FSO link fundamentally unable to achieve 99.9% availability**. You need a hybrid FSO + 60 GHz RF backup that switches seamlessly. Design both links.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Geometric loss:**
- Beam divergence `theta` (half-angle, radians) and link range `L` determine the beam radius at receiver: `w(L) = theta * L` (Gaussian beam approx).
- Geometric loss: `L_geo = (w(L) / D_rx)^2` if `w(L) >> D_rx`, or more accurately use aperture averaging.
- Target: choose `theta` to match `D_rx` ≈ beam waist at receiver.

**Kim model for fog attenuation:**
- `alpha(lambda) = (3.91 / V) * (lambda / 550)^(-q)` dB/km, where V is visibility in km.
- `q = 1.6` for V > 50 km, `q = 1.3` for 6–50 km, `q = 0.585 * V^(1/3)` for V < 0.5 km (dense fog), `q = 0.16*V + 0.34` for 0.5–1 km.
- Total fog attenuation over 5 km: `A_fog = alpha * 5` dB.

**Scintillation and Rytov variance:**
- Rytov variance (spherical wave): `sigma_R^2 = 0.5 * Cn2 * k^(7/6) * L^(11/6)` where `k = 2*pi/lambda`.
- Gamma-gamma distribution parameters: `alpha = [exp(sigma_lnx^2) - 1]^(-1)`, `beta = [exp(sigma_lny^2) - 1]^(-1)` where `sigma_lnx^2` and `sigma_lny^2` are large- and small-scale scintillation variances.
- For weak turbulence (`sigma_R^2 < 0.3`): log-normal model is sufficient. For `sigma_R^2 > 1`, use gamma-gamma.

**Aperture averaging:**
- Using a larger receiver aperture reduces scintillation. Aperture averaging factor: `A = [1 + 1.1*(D_rx^2 / lambda / L)^(7/6)]^(-1)`.
- Effective scintillation: `sigma_eff^2 = A * sigma_R^2`.

**Pointing error:**
- For Gaussian beam: pointing loss ≈ `exp(-2*(pointing_error / w_L)^2)`.
- With `w_L` = beam radius at receiver and `pointing_error = 1 mrad * L = 5 m`.

**Hybrid 60 GHz RF backup:**
- 60 GHz has ~15 dB/km oxygen absorption — for 5 km, that's 75 dB. However, a high-gain dish system can overcome this.
- Design a 60 GHz link with enough margin to operate when FSO is down (fog conditions).
- Switching criterion: monitor received optical power; switch to RF when below threshold.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation:**

1. **Kim model** (`fog_attenuation_kim_model(visibility_m, wavelength_nm, range_km)`):
   - Implement the q(V) piecewise function.
   - Return attenuation in dB.
   - Test: V = 50 m → alpha ≈ 340 dB/km → A_fog = 1700 dB (completely opaque — hybrid is mandatory).

2. **Link budget** (`compute_link_budget(params, conditions)`):
   - Tx power (laser): start with 100 mW (+20 dBm) — eye-safe class 1M at 1550 nm.
   - Geometric loss: `L_geo_dB = 20*log10(theta_rad * L_km * 1000 / (D_rx / 2))` when beam > aperture.
   - Sum: `P_rx = P_tx - L_geo - A_fog - A_rain - L_point - L_scint`.
   - Receiver sensitivity at 10 Gbps: for APD + PIN, sensitivity ≈ -28 dBm for BER = 10^-9 with OOK.
   - Link margin = P_rx - sensitivity.

3. **Scintillation BER** (`compute_ber_scintillation(snr_mean, sigma_I2, modulation)`):
   - For log-normal fading channel with OOK:
     - `BER = 0.5 * erfc(SNR * exp(sigma_x) / sqrt(2))` averaged over log-normal PDF.
     - Numerical integration over the fading PDF: `BER = integral(BER_AWGN(SNR*I) * p(I) dI)`.
   - Use 1000-point Gaussian quadrature or Monte Carlo (draw 1e5 samples from log-normal).

4. **Spatial diversity** (`compute_diversity_gain(n_apertures, separation_m, r0_m)`):
   - Diversity gain from N independent apertures: `G_div = 10*log10(N)` if fully decorrelated.
   - Decorrelation distance ≈ Fried parameter `r0 = 0.185 * (lambda^2 / Cn2 / L)^(3/5)`.
   - If aperture separation > r0, diversity is near-ideal.

5. **Adaptive optics** (`design_adaptive_optics(Cn2, L, D_tx)`):
   - Number of actuators needed: `N_act ≈ (D_tx / r0)^2`.
   - Residual wavefront error after correction: `sigma_phi^2 ≈ (D_tx / r0)^(5/3) / N_act^(5/6)` (approximate).
   - Required AO bandwidth: Greenwood frequency `f_G = 0.427 * v_wind / r0`.

6. **Availability** (`compute_availability_fso()`):
   - Use visibility statistics for your city: PDF of visibility (from meteorological data or ITU-R).
   - Simplified: assume fog (V < 200 m) occurs 0.1% of the time → hybrid 60 GHz handles those events → availability = 99.9%.
   - Scintillation fades: model as outage probability from gamma-gamma CDF below a threshold SNR.

7. **Populate submission.json** with all computed values, including BER under clear-sky and foggy conditions.
