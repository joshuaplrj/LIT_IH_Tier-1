# AeroBot — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Focus on the **quad-plane** configuration (fixed wing + four dedicated VTOL rotors that fold during cruise). It cleanly decouples hover and cruise optimization, simplifying the design space. The core challenge is the **mass budget**: the extra VTOL motors and rotors add 1–2 kg, so the wing and battery must be sized tightly. Think in terms of two independent subsystems — a conventional fixed-wing aircraft for cruise, and a multirotor for hover — that share only the airframe and battery.

## Tier 2 — Technique Guidance (-10% score penalty)
Use the **Breguet endurance equation** for fixed-wing cruise:

```
E = (eta_prop * eta_motor / g) * (CL / CD) * ln(W_initial / W_final)
```

Target CL/CD >= 14 with a NACA 4412 or Clark-Y airfoil at AR = 8–10. For VTOL hover, use **actuator disk theory** to find hover power:

```
P_hover = W * sqrt(W / (2 * rho * A_disk))
```

Keep disk loading (W/A_disk) below 12–15 kg/m² to keep hover current manageable. For structural sizing of the wing spar, model it as a **cantilever beam** with distributed elliptic lift load and apply a 1.5x safety factor; use CFRP (E = 70 GPa, allowable bending stress ~600 MPa) for minimum mass.

## Tier 3 — Implementation Guidance (-15% score penalty)
Follow this calculation sequence:

1. **Mass estimation**: Start with MTOW = 12 kg (leave 3 kg margin to 15 kg limit). Use fractions: payload = 2 kg, battery = 3.5 kg, structure = 3.5 kg, propulsion = 2 kg, avionics = 1 kg.
2. **Wing sizing**: `S = W / (0.5 * 1.225 * 20^2 * 0.8)` → S ≈ 0.38 m². Choose AR = 9 → span b = sqrt(AR * S) ≈ 1.85 m.
3. **Drag polar**: `CD = CD0 + CL^2 / (pi * AR * e)` with CD0 = 0.025, Oswald e = 0.8. At cruise CL = 0.8: CD ≈ 0.054, L/D ≈ 14.8.
4. **Cruise power**: `P_cruise = (W/LD) * V` = (12*9.81/14.8) * 20 ≈ 159 W shaft; with 0.8 prop efficiency → 200 W electrical.
5. **Battery**: `E_batt = P * t = 200 * 2.0 = 400 Wh`. At 200 Wh/kg: 2.0 kg — fits budget.
6. **VTOL rotors** (quad, each supporting W/4): disk area per rotor for 12 kg/m² loading = (12/4)/12 = 0.25 m² → D_rotor = 0.56 m.
7. **Hover power per rotor**: `P = (m*g/4) * sqrt((m*g/4)/(2*rho*A))` ≈ 150 W each → 600 W total hover. Add 1-min hover budget = 10 Wh — add to battery.
8. **Spar**: bending moment at root = `M = (L/2) * (b/4)` using half-span elliptic load. Required section modulus = `M / sigma_allow`. Circular CFRP tube — check SF >= 2.5.
9. **Static margin**: place CG at 25–30% MAC; ensure neutral point is at 35–40% MAC for SM = 8–12%.
