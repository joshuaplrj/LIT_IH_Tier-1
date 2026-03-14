# E-Harvest — Hints

> Each tier reveals progressively more implementation detail and carries a score penalty. Penalties are cumulative — requesting Tier 3 costs -30% in total.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

RF energy harvesting is a **cascaded efficiency problem**: available RF power × antenna efficiency × matching network efficiency × rectifier efficiency × regulator efficiency = usable DC power. At -10 dBm input (100 μW), there is very little room for loss in any stage. The system must be designed as a **coupled chain**, not as isolated blocks — the rectifier's input impedance changes with input power, which detuned the matching network if you designed it for a different power level. Focus first on getting the rectifier right (it is the hardest stage), then design the matching network around it.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Antenna:** Use a **planar inverted-F antenna (PIFA)** or a **dual-band patch antenna** that resonates at both 915 MHz and 2.4 GHz on 50 mm × 50 mm FR4 (εr ≈ 4.4, h = 1.6 mm). A dual-band PIFA typically achieves 2–3 dBi gain and -10 dB S11 bandwidth of ~50 MHz at 915 MHz and ~200 MHz at 2.4 GHz on this form factor.

**Matching network:** L-network (2-element) between antenna (50 Ω) and rectifier (typically 200–1000 Ω at -10 dBm). Use the equation: `Q = sqrt(R_rect / R_ant - 1)`, then `X_series = R_ant × Q`, `X_shunt = R_rect / Q`. For dual-band, use a diplexer to split the signal before two separate rectifiers.

**Rectifier topology:** **Single-series rectifier with SMS7630-061** Schottky diode (V_th ≈ 80 mV, C_j ≈ 0.14 pF at zero bias). At -10 dBm, this gives ~40–50% PCE. At -20 dBm, switch to a voltage doubler to ensure the output clears 1.8 V.

**Regulator:** Use an **ultra-low quiescent current LDO** (e.g., TI TPS7A02, Iq = 25 nA) or a switched-capacitor converter (Seiko S-882Z, starts at 0.3 V input). The regulator quiescent current must be < 1 μA to avoid consuming more power than the load.

**Storage capacitor:** Size for worst-case duty cycle: `C_min = I_load × t_active / ΔV_max` where ΔV_max = 0.09 V (5% of 1.8 V). For a 10 ms active burst at 100 μA: C = 11 μF. Use a 47 μF 4 V tantalum or ceramic capacitor with low ESR.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**PCE calculation model for rectifier (implement in `starter.py`):**

For a single-series rectifier with one Schottky diode:
```
PCE = P_out / P_in_rf
P_out = V_out² / R_load
```

Using the Shockley diode model with junction capacitance:
```python
def pce_single_series(P_in_dbm, R_ant, R_load, V_th, I_s, eta, C_j_pF, freq_ghz):
    """Estimate PCE using analytical model."""
    P_in_w = 10**(P_in_dbm / 10) * 1e-3
    omega = 2 * math.pi * freq_ghz * 1e9

    # Rectifier input impedance (approximate):
    R_rect = V_th / (2 * math.pi * freq_ghz * 1e9 * C_j_pF * 1e-12 * V_th)

    # Available voltage at rectifier input (after matching):
    V_in_pk = math.sqrt(2 * P_in_w * R_ant)

    # Output voltage (approximate ideal doubler / series):
    V_out = max(0, V_in_pk - V_th)  # simplified; Spice gives more accurate result

    P_out = V_out**2 / R_load
    pce = min(P_out / P_in_w, 0.98) if P_in_w > 0 else 0
    return pce, V_out
```

**Key numbers to verify in your report:**

1. At -10 dBm, 50 Ω source: `V_rf_peak = sqrt(2 × 100e-6 × 50) ≈ 0.10 V`. With SMS7630 V_th ≈ 80 mV, V_out ≈ 20 mV from a single rectifier pass — you need a voltage multiplier (Dickson ×4 minimum).

2. **Dickson multiplier stage count:** number of stages N to achieve V_out = 1.8 V: `V_out ≈ N × (V_pk - V_th)` so `N ≈ V_out / (V_pk - V_th)`. For V_pk = 0.10 V and V_th = 0.08 V: N ≈ 90 — impractical. This shows you need a matching network to boost V_pk, or use a higher-power source. Design the matching network to present a 400 Ω load at the rectifier and step down from 50 Ω: this boosts V_pk by sqrt(400/50) = 2.83×, giving V_pk ≈ 0.28 V → N ≈ 9 stages.

3. **Startup time from empty capacitor:** `t_start = C × V_startup / I_harvest_avg`. For C = 47 μF, V_startup = 1.8 V, I_harvest = 50 μA (from rectifier): t_start ≈ 1.7 seconds.
