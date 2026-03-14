# ThermoCell — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Select **two-tank molten salt** with Solar Salt (60% NaNO3 + 40% KNO3) as your technology — it is the proven CSP industry standard (Andasol, Crescent Dunes). The central challenge is **thermal loss vs. insulation mass/cost** and **cyclic thermal stress** in the tank shell. Focus on: (1) sizing the tank conservatively with 15% design margin on volume, (2) choosing Alloy 800H or 304 SS for the shell (verified for 565°C service), and (3) demonstrating that daily cycling between 290°C and 565°C for 30 years gives an acceptable fatigue life.

## Tier 2 — Technique Guidance (-10% score penalty)
Use these key relationships:

**Salt mass** (sensible heat storage):
```
m_salt = Q_storage / (cp_salt * delta_T)
       = (1000 MWh * 3600 s/hr) / (1520 J/kg/K * (565-290) K)
       ≈ 8.57e6 kg  (~8,570 tonnes)
```

**Tank volume**: `V = m / rho_salt`; rho_salt ≈ 1,800 kg/m³ at average temperature.

**Thermal losses** (cylindrical tank, mineral wool insulation, k = 0.05 W/m·K):
```
Q_loss = k * A_surface * (T_tank - T_ambient) / t_insulation
```
Target Q_loss < 0.5% of stored energy per hour to maintain > 99% thermal retention efficiency. Combined with HX losses, total round-trip can still exceed 95%.

**Heat exchanger** (shell-and-tube, NTU-effectiveness method):
```
NTU = UA / C_min
effectiveness = NTU / (1 + NTU)  [for Cmin/Cmax -> 0]
```
Target effectiveness > 0.92 for the steam generator.

**Cyclic thermal stress** (hoop + thermal):
```
sigma_thermal = E * alpha * delta_T / (2 * (1 - nu))
```
For 304 SS: E = 193 GPa, alpha = 17.2e-6 /K, nu = 0.29. Keep below 0.5 * S_y for infinite fatigue life.

## Tier 3 — Implementation Guidance (-15% score penalty)
Step-by-step calculation sequence:

1. **Salt mass**: m = 3.6e12 J / (1520 * 275) = 8.608e6 kg.
2. **Tank sizing**: V_salt = 8.608e6 / 1800 = 4,782 m³. Each tank holds half → V_tank = 2,391 m³ + 10% ullage = 2,630 m³. Cylindrical, H/D = 1: D = (4*V/pi)^(1/3) = 14.7 m, H = 14.7 m. Two tanks.
3. **Insulation**: Use 0.5 m mineral wool (k = 0.04 W/m·K). Surface area hot tank ≈ pi*D*(D/2 + H) ≈ 1,020 m². Q_loss_hot = 0.04 * 1020 * (565-20) / 0.5 = 44.6 kW. Over 10 hr discharge: 446 kWh lost = 0.045% of 1,000 MWh → negligible.
4. **Round-trip efficiency**: eta_rt = eta_charge * eta_HX_charge * eta_HX_discharge * eta_parasitic. With each HX at 98% and parasitic losses 1.5%: eta_rt ≈ 96.5%. Meets > 95% requirement.
5. **Heat exchanger area**: For 100 MW discharge, LMTD ≈ 50 K, U = 800 W/m²K (shell-and-tube, steam/salt): A = Q / (U * LMTD) = 100e6 / (800 * 50) = 2,500 m².
6. **Thermal stress**: sigma = 193e9 * 17.2e-6 * 275 / (2 * 0.71) = 643 MPa — this exceeds S_y of 304 SS at 565°C (≈205 MPa). Solution: (a) use slow ramp-up rate (< 2°C/min), (b) use stress-relief grooves, (c) design for low-cycle fatigue (LCF) using Coffin-Manson: N_f = (eps_f / eps_range)^(1/c); target N_f > 15,000 cycles.
7. **Cost**: Salt cost at $1/kg × 8,608 tonnes = $8.6M. Tanks at $200/m² × 2 × 1,020 m² = $0.4M. HX at $500/m² × 2,500 m² = $1.25M. Total ≈ $15M for 1,000 MWh → $15/kWh — within $20/kWh target.
