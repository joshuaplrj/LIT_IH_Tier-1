# MIMO-Sat — Hints

> Each tier costs score points. Only request when genuinely stuck. Read all lower tiers before moving to the next.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This problem has **five independent but coupled workstreams**: link budget, modulation/coding, beamforming, Doppler compensation, and availability. The right strategy is to work through them in order because each feeds the next:

1. **Geometry first**: The satellite is at 550 km altitude. At a given elevation angle, compute the slant range and the satellite's LOS angle. This determines path loss and Doppler shift simultaneously.
2. **Link budget** sets the received Eb/N0. The received Eb/N0 must exceed the required Eb/N0 for your chosen modulation/coding scheme.
3. **Availability** is determined by how much link margin you have above the minimum Eb/N0, because rain attenuation is a random variable — you need the margin to be large enough that rain attenuation exceeds it less than 0.1% of the time.

A common mistake is designing for zenith-only (ideal case). The real challenge is designing for a 20° elevation angle where path loss is ~7 dB higher and rain attenuation is 3× larger (slant path).

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Link budget step by step:**
- Free-space path loss (dB): `FSPL = 20*log10(4*pi*R*f/c)` where R is slant range.
- Slant range from altitude h and elevation angle el: `R = sqrt((Re+h)^2 - (Re*cos(el))^2) - Re*sin(el)` (exact) or approximation `R ≈ h/sin(el)`.
- Rain attenuation: Use the ITU-R P.618 model. The specific rain attenuation is `gamma_R = k * R_rain^alpha` (ITU-R P.838 coefficients for 12 GHz). Slant-path attenuation = `gamma_R * L_eff` where `L_eff = h_rain / sin(el)` and `h_rain ≈ 4 km` for tropical zone.
- Atmospheric absorption: ~0.1 dB/km at Ku-band (ITU-R P.676 approximation).

**Phased array beamforming:**
- 256-element URA (16×16) gives theoretical gain `G = eta * 4*pi*A/lambda^2` where `A = N * d^2` (aperture area).
- Scan loss: for a URA scanned to elevation `el`, gain reduces by `cos(theta_scan)` where theta_scan = 90° - el.
- HPBW ≈ `0.886 * lambda / (N^0.5 * d)` (radians) for a square array.

**Doppler analysis:**
- LEO orbital velocity at 550 km: `v_sat = sqrt(GM/r) ≈ 7.6 km/s`.
- Maximum Doppler occurs at 0° elevation (horizon pass). Use geometry to compute LOS component of velocity.
- Doppler shift: `f_d = f_c * v_los / c`. At 12 GHz and 7.6 km/s, max f_d ≈ 304 kHz.
- Pre-correction: ground terminal predicts Doppler from ephemeris and applies a pre-compensation frequency offset.

**Modulation and coding:**
- For 100 Mbps in a 36 MHz transponder, you need spectral efficiency ≥ 2.78 bps/Hz → 8PSK with rate 1/2 LDPC (2.25 bps/Hz) is marginal; use 8PSK rate 2/3 (3.0 bps/Hz) or 16APSK rate 3/4.
- DVB-S2 modcod tables provide required Eb/N0 for each scheme — look these up.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step-by-step implementation:**

1. **Orbital geometry** (`compute_orbital_geometry()`):
   - For elevation angle `el` (degrees), slant range R ≈ sqrt(h² + 2*Re*h + Re²*cos²(el)^0) — use the exact formula: `R = sqrt((Re+h)^2 - Re^2*cos^2(el)) - Re*sin(el)` where Re = 6371 km.
   - LOS velocity: `v_los = v_sat * cos(el)` (approximation; exact requires pass geometry).
   - Maximum Doppler: evaluate at el = 5° (low-angle pass) for worst case.

2. **Downlink link budget** (`link_budget_downlink()`):
   - Satellite EIRP: Pt_sat_dbw + G_sat_dbm. For 256-element array with 0.5W per element: `Pt_total = 256 * 0.5 W`. Gain ≈ 10*log10(256 * eta) + 10*log10(4*pi*A/lambda^2) — or simply `G_array ≈ N * Ge` where Ge is single-element gain.
   - Ground station G/T: For 1.2 m dish at 12 GHz, `G = eta * pi² * D² * f² / c²` in linear. LNA noise temp ~50 K, sky noise ~30 K, total Tsys ≈ 120 K. G/T in dB/K.
   - Received C/N0: `C/N0 = EIRP - FSPL - Latm - Lrain + G/T - 10*log10(k)` (all in dB).
   - Eb/N0 = C/N0 - 10*log10(bitrate).

3. **Rain availability** (`compute_availability()`):
   - Use ITU-R P.618 exceedance statistics: probability that rain attenuation > A dB is approximately `p = p0 * exp(-A/a)` where p0 and a are location-dependent constants.
   - For tropical zone, p0 ≈ 1.0%, a ≈ 2.5 dB → link margin of 6 dB gives availability ≈ 99.9%.
   - Implement as a simple exponential CDF inversion: `A_exceeded_pct = link_margin / a`.

4. **Beamforming** (`design_beamforming()`):
   - Phased array steering vector: `a(theta, phi) = exp(j*k*d*(n_x*sin(theta)*cos(phi) + n_y*sin(theta)*sin(phi)))` for each element (n_x, n_y).
   - Uniform weighting gives maximum gain; Chebyshev weighting reduces sidelobes at cost of gain.
   - Beam hopping: divide coverage zone into N_beams spots; time-share with dwell time = frame_duration / N_beams.

5. **Populate submission.json** with all computed values. Ensure rain attenuation and availability numbers are computed at the worst elevation angle in your coverage zone (typically 20°).
