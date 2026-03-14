# PowerShield — Hints

> Each tier reveals progressively more implementation detail and carries a score penalty. Penalties are cumulative — requesting Tier 3 costs -30% in total.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

A solid-state circuit breaker replaces the mechanical arc-interruption process with ultra-fast semiconductor switching. The fundamental challenge in DC systems is that there is no natural current zero — you must **force the current to zero** by turning off the semiconductor and then absorbing the energy stored in the line inductance. The three sub-problems are:
1. **Detect** the fault faster than the current can reach 10 kA (you have ~10–50 μs).
2. **Turn off** the semiconductor before the current destroys it (gate driver speed is critical).
3. **Clamp** the resulting voltage spike from the L × di/dt inductive kick (without this, you will exceed MOSFET/IGBT breakdown voltage).

Think of the system as three cascaded blocks: current sensor → logic/comparator → gate driver → power switch → energy absorber.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Semiconductor choice: SiC MOSFET** (preferred for this spec):
- SiC MOSFETs have ~10× lower Rds_on per chip area compared to Si IGBTs at 600–1200 V, enabling faster switching (sub-microsecond) and lower conduction losses. A suitable part: Wolfspeed C3M0016120K (1200 V, 16 mΩ, 115 A) — use 2 in parallel per current direction.
- **Topology:** two back-to-back SiC MOSFETs (common-source configuration) for bidirectional operation. Each device handles one current direction.
- **Clamping:** Transient Voltage Suppressor (TVS) array or Metal Oxide Varistor (MOV) across the switch to clamp at 550 V (< 600 V limit). For fast response, add a parallel RC snubber (R = 1–5 Ω, C = 100–470 nF) to limit dv/dt.
- **Detection:** Rogowski coil + analog comparator with threshold set to ~500 A (2.5× rated). Detection time ≈ 1–2 μs.
- **Gate driver:** Isolated gate driver (e.g., IXYS IXD_614) with negative turn-off voltage (−5 V gate) to maximize dv/dt immunity and minimize fall time.

**Timing budget (must total < 100 μs):**
| Stage | Target |
|---|---|
| Fault detection (comparator) | ≤ 2 μs |
| Gate driver propagation delay | ≤ 0.5 μs |
| MOSFET current fall time | ≤ 5 μs |
| Energy absorption (MOV clamp) | ≤ 20 μs |
| Total | ≤ 27.5 μs (well within 100 μs) |

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Simulation model (implement in `starter.py`):**

The fault circuit is an RL series circuit with:
- `V_dc = 400 V`, `L_fault = 100 μH` (typical DC bus stray inductance), `R_fault = 0.04 Ω`
- Fault current without breaker: `I(t) = (V_dc / R_fault) × (1 - exp(-R_fault × t / L_fault))`
- With SSCB: integrate the RL ODE with the MOSFET switch:
  - For `t < t_detect`: switch closed, `dI/dt = (V_dc - I × R_on) / L_fault`
  - For `t_detect < t < t_detect + t_falltime`: switch opening, `dI/dt = -(V_clamp - V_dc) / L_fault` (clamped regime)
  - Current reaches zero at `t_interrupt`

**Key sizing calculations:**

1. **MOV energy requirement:**
   `E_mov = 0.5 × L_fault × I_at_detect²`
   where `I_at_detect = I(t_detect)`. Size MOV for at least 2× this energy for margin.

2. **Conduction losses at rated current (200 A):**
   With 2 back-to-back MOSFETs in common-source:
   `P_cond = I_rated² × (Rds_on_device / N_parallel)` per switch × 2 switches
   For 16 mΩ, 2 parallel: `P = 200² × (0.016/2) × 2 = 640 W` — this is high.
   Use 4 parallel devices per direction to get `Rds_on_eff = 4 mΩ` → `P = 160 W`.

3. **Heat sink sizing:**
   `R_th_jc = 0.5 °C/W` (per MOSFET datasheet), `R_th_cs = 0.1 °C/W` (thermal pad).
   For 160 W total, target `T_junction ≤ 150 °C` at 40 °C ambient:
   `R_th_sa ≤ (150 - 40) / 160 - R_th_jc - R_th_cs = 0.687 - 0.5 - 0.1 = 0.087 °C/W`
   This requires forced-air cooling or a large passive heat sink.

4. **Fault current simulation (Python):**
   ```python
   dt = 0.1e-6  # 100 ns timestep
   L_fault = 100e-6
   R_fault = 0.04
   V_dc = 400.0
   V_clamp = 550.0  # MOV clamping voltage
   t_detect = 2e-6
   t_fall = 5e-6    # MOSFET fall time

   I = 0.0; t = 0.0
   while I >= 0:
       if t < t_detect:
           dI = (V_dc - I * R_fault) / L_fault
       elif t < t_detect + t_fall:
           # Linear current ramp-down during fall time
           dI = -I / t_fall
       else:
           dI = -(V_clamp - V_dc) / L_fault
       I += dI * dt; t += dt
   ```
