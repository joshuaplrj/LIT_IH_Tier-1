# MotorForge — Hints

> Each tier reveals progressively more implementation detail and carries a score penalty. Penalties are cumulative — requesting Tier 3 costs -30% in total.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

BLDC motor design is fundamentally about managing **flux density in the magnetic circuit**. Every design choice — pole/slot combination, magnet grade, stator bore diameter, air gap length — flows from a target peak air-gap flux density (typically 0.85–1.0 T for NdFeB magnets). The key trade-off is between **torque density** (packing more magnetic material in a small volume) and **losses** (copper losses increase with current density; iron losses increase with frequency and flux swing). Start by deciding your pole/slot combination, then work outward: stator bore → stator OD → stack length → winding turns → losses → temperature rise.

---

## Tier 2 — Technique Guidance (-10% score penalty)

Use the **specific magnetic loading / specific electric loading** method to size the machine, then validate with an equivalent magnetic circuit:

- **Torque equation:** `T = (π/2) × D² × L × A × B`
  where D = stator bore diameter (m), L = axial stack length (m), A = electric loading (A/m, typically 20,000–40,000 A/m), B = air-gap flux density (T, target 0.85 T).
- **Choose 8-pole / 12-slot** (fractional-pitch, reduces cogging torque) or **10-pole / 12-slot** (very popular for e-scooters, good winding factor ~0.933).
- **Losses:** copper = I²R per phase × 3 phases; iron = Steinmetz equation `P_fe = k_h × f × B^α + k_e × f² × B²` with typical coefficients for M19 silicon steel.
- **Thermal:** thermal resistance of stator to ambient `R_th = ΔT / P_loss`; use a lumped-parameter thermal model with three nodes: winding → stator lamination → housing → ambient.
- **FOC controller:** design two nested PI loops — an inner current (torque) loop with bandwidth ~1 kHz, outer speed loop ~100 Hz. Tune using `Kp = L × ω_c`, `Ki = R × ω_c` where ω_c is the desired crossover frequency.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Key formulas to implement in `starter.py`:**

1. **Back-EMF constant (Ke):** `Ke = (N_ph × k_w × p × Φ_m) / (2π)`
   where N_ph = series turns per phase, k_w = winding factor (~0.933 for 10p/12s), p = pole pairs, Φ_m = magnet flux per pole = B_g × τ_p × L (τ_p = pole pitch = π × D / (2p)).

2. **Torque constant:** `Kt = 3/2 × p × Φ_m × N_ph × k_w` (same numerical value as Ke in SI units per phase — Kt = Ke).

3. **Peak current required for 40 Nm:** `I_peak = T_peak / Kt`; check this against the conductor current density J = I / (A_conductor). Keep J ≤ 6 A/mm² for air-cooling.

4. **Copper losses:** `P_cu = 3 × I_rms² × R_phase`; `R_phase = (ρ_cu × L_turn_avg × N_ph) / (A_conductor × N_parallel)`.

5. **Steinmetz iron losses per kg:** `P_fe_kg = k_h × f × B_pk^2 + k_e × f² × B_pk²`
   Use k_h = 0.0275, k_e = 1.83e-5, α = 2 for M19 26-gauge steel at 1.0 T, 50 Hz.

6. **Thermal resistance (simplified):** `R_th_winding_ambient ≈ 0.20 K/W` for a 200 mm OD, air-cooled motor at natural convection. Scale as `R_th ∝ 1 / (π × D × L × h)` where h ≈ 25 W/m²K for natural convection.

7. **Winding temperature:** `T_winding = T_ambient + P_total × R_th_winding_ambient`. Limit to 155°C (Class F). If exceeded, increase D or L, or add fins to reduce R_th.

8. **Efficiency map:** Loop over speed (0–5000 RPM) and torque (0–40 Nm), compute copper + iron + mechanical losses at each operating point, compute η = P_out / (P_out + P_losses).
