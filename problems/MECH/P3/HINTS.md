# GearPro — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
A planetary gearbox is fundamentally different from a parallel-shaft gearbox. In a simple planetary stage with a fixed ring gear, the gear ratio is `i = 1 + Z_ring / Z_sun`. The key insight is that **multiple planets share the load simultaneously** — a 3-planet stage divides the tooth force by (roughly) 3 at each mesh, dramatically reducing module requirements compared to a single-mesh gear. Focus your design effort on: (1) balancing the ratio split to minimise Stage 1 tooth loads (it sees the highest torque), (2) satisfying all three planetary geometric constraints simultaneously, and (3) verifying AGMA safety factors for both bending and surface fatigue at each stage.

## Tier 2 — Technique Guidance (-10% score penalty)
**Three mandatory geometric conditions** for a valid planetary stage:
1. **Ratio**: `i = 1 + Z_ring / Z_sun` (ring is fixed)
2. **Mesh condition**: `Z_ring = Z_sun + 2 * Z_planet`
3. **Assembly condition**: `(Z_sun + Z_ring) mod N_planets == 0`

**AGMA 2101 bending stress** (metric form):
```
sigma_b = W_t * Ko * Kv * Ks * (1/b*mt) * (1/Yj) * Km * Cf
```
where `W_t` = tangential tooth load = `2*T / d` (d = pitch diameter), `Ko` = overload factor (~1.75 for wind), `Kv` = dynamic factor (~1.2), `Ks` = size factor, `Km` = load distribution factor (~1.3), `Yj` = geometry factor. Allowable: `sigma_b_allow = St * Yn / (SF * KT * KR)` with `St` = 380 MPa for carburised 9310 steel.

**AGMA contact stress**:
```
sigma_c = Zе * sqrt(W_t * Ko * Kv * Ks * Km / (d*b) * Zr / Zi)
```
Allowable: `sigma_c_allow = Sc * Zn * Zw / (SH * KT * KR)` with `Sc` = 1,550 MPa for carburised 9310.

**Bearing L10 life** (ISO 281):
```
L10 = (C/P)^p * 10^6 / (60 * n)    [hours]
```
where `C` = dynamic load rating, `P` = equivalent dynamic load, `p` = 10/3 for roller bearings.

## Tier 3 — Implementation Guidance (-15% score penalty)
Step-by-step design sequence:

1. **Ratio split**: Use 5.0 × 5.0 × 4.0 = 100. Check: `i1 = 1 + Z_r1/Z_s1 = 5 => Z_r1 = 4*Z_s1`. Try `Z_s1=18, Z_r1=72, Z_p1=27`. Assembly check: `(18+72)/3 = 30` — integer, pass.

2. **Stage 1 module** (highest torque: T1 = 3.2e6 N·m):
   - Tangential load per planet: `W_t = 2*T1 / (3 * d_s1)` where `d_s1 = Z_s1 * m`.
   - Try m = 20 mm: `d_s1 = 18*20 = 360 mm`. `W_t = 2*3.2e6 / (3 * 0.36) = 592,593 N`.
   - Face width `b = 10*m = 200 mm` (start here, widen if SF fails).
   - Compute `sigma_b` and check against 380/SF — target SF_b >= 1.56 (AGMA 6006 uses SF = 1.56 for 20-yr life).

3. **Stage 2 (ratio 5:1)**: Input torque = T1/5 = 640,000 N·m. Module 12 mm is typically sufficient.

4. **Stage 3 (ratio 4:1)**: Input torque = T2/5 = 128,000 N·m. Module 8 mm typically sufficient.

5. **Efficiency**: Per-stage mesh efficiency `η_mesh ≈ 1 - f * (1/Z_s + 1/Z_p) * (1 + i)/(2*i)` where f = 0.05 (lubricated). Overall `η = η1 * η2 * η3 * η_bearings`. Target: each stage > 99%, bearings 99.5%.

6. **Bearings**: Planet pin bearings (cylindrical roller) see load `P = W_t / N_planets`. Use `C/P = (L10_hr * 60 * n_planet / 10^6)^(3/10)` to find required C, then select from SKF/NSK catalogue. L10 target: 350,000 hr (2x design life for 90% reliability).
