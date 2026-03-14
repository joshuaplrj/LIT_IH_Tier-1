# HyperCool — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
Choose **direct-to-chip microchannel two-phase cooling with Novec 7100**. At 100 W/cm², single-phase water can barely manage the heat flux; Novec 7100 boiling in microchannels unlocks flow boiling HTC of 20,000–80,000 W/(m²·K) — far exceeding single-phase performance. The system architecture: a cold plate (microchannel evaporator) is bonded directly to each chip; vapor rises to a condenser (air-cooled or liquid-to-air) mounted at the top of the rack; liquid returns by gravity/pump. The key design tradeoff is **channel width vs. pressure drop vs. CHF**: narrower channels give higher HTC but higher pressure drop and lower CHF.

## Tier 2 — Technique Guidance (-10% score penalty)
**Two-phase HTC (Kandlikar correlation, simplified)**:
```
h_tp = h_sl * (C1 * Co^C2 * (25*Fr_lo)^C5 + C3 * Bo^C4 * Ffl)
```
where Co = convection number, Bo = boiling number, Fr_lo = Froude number, h_sl = single-phase liquid HTC. For a quick estimate, use the enhanced HTC approximation:

```
h_tp ≈ F_enhancement * h_lo
```
where F_enhancement = 5–10 for saturated flow boiling in microchannels, and:
```
h_lo = Nu * k_l / D_h     (Dittus-Boelter: Nu = 0.023 * Re^0.8 * Pr^0.4)
```

**CHF (Katto-Ohno correlation)**:
```
q_CHF = C * (rho_v / rho_l)^0.043 * h_fg * G * (L/D)^(-0.54)
```
where G = mass flux [kg/(m²·s)], h_fg = latent heat, C ≈ 0.25.

**Microchannel pressure drop** (two-phase, Lockhart-Martinelli):
```
delta_P_tp = phi_lo^2 * delta_P_lo
phi_lo^2 = 1 + C/X + 1/X^2
```
where X = Martinelli parameter. For a quick estimate: `delta_P ≈ 2 * f * L * G^2 / (rho_l * D_h)` with two-phase multiplier ~3–5.

**Thermal resistance network** (junction to ambient):
```
R_total = R_jc + R_TIM + R_spreading + R_conv + R_cond_to_ambient
```
Typical: R_jc = 0.01 K/W, R_TIM = 0.005 K/W, R_spreading = 0.005 K/W (Cu cold plate), R_conv = 1/(h_tp × A_base).

**Novec 7100 properties** (at 61°C saturation):
- rho_l = 1,390 kg/m³, rho_v = 9.9 kg/m³
- mu_l = 3.0×10⁻⁴ Pa·s
- k_l = 0.069 W/(m·K)
- h_fg = 111,600 J/kg
- sigma = 0.0095 N/m

## Tier 3 — Implementation Guidance (-15% score penalty)
Step-by-step calculation:

1. **Thermal budget**:
   - Q_chip = 500 W (100 W/cm² × 5 cm² = 5 cm² effective die area)
   - R_total_budget = (85 - 61) / 500 = 0.048 K/W
   - Allocate: R_jc = 0.008, R_TIM = 0.004, R_spreading = 0.004, R_conv = 0.032 K/W

2. **Required HTC**:
   - A_base = 1 cm × 1 cm = 1×10⁻⁴ m² (assuming 1 cm² die, tight coupling)
   - Increase base area with fin efficiency to e.g. 5 cm² effective
   - h_req = 1 / (R_conv × A_eff) = 1 / (0.032 × 5×10⁻⁴) = 62,500 W/(m²·K)
   - This is achievable with microchannels (w=200 μm, d=500 μm) in Novec 7100

3. **Microchannel geometry** (per chip, 1 cm × 1 cm base):
   - Channel width w = 200 μm, height H = 500 μm, fin width t = 100 μm
   - Number of channels in 10 mm: N_ch = 10,000 / (200+100) = 33 channels
   - D_h = 2*w*H/(w+H) = 2×200×500/(700) = 286 μm
   - Flow area = N_ch × w × H = 33 × 2×10⁻⁴ × 5×10⁻⁴ = 3.3×10⁻⁶ m² per chip

4. **Mass flow per chip**:
   - Q = m_dot × h_fg × x_exit (assume exit quality x = 0.3)
   - m_dot = Q / (h_fg × x) = 500 / (111,600 × 0.3) = 0.0149 kg/s per chip
   - G = m_dot / A_flow = 0.0149 / 3.3×10⁻⁶ = 4,515 kg/(m²·s)

5. **Pressure drop**:
   - Single-phase: delta_P_lo = f × (L/D_h) × G²/(2×rho_l) ≈ 8 kPa (for L=10 mm)
   - Two-phase multiplier ~4: delta_P_tp ≈ 32 kPa per chip

6. **CHF check**:
   - q_CHF ≈ 0.25 × (9.9/1390)^0.043 × 111600 × 4515 × (10/0.286)^(-0.54) ≈ 380 W/cm²
   - CHF SF = 380 / 100 = 3.8 — excellent

7. **System COP** = Q_cooling / W_pump. Pump power for 50 kW (10 chips): total delta_P = 32 kPa, total flow = 10 × 0.0149 = 0.149 kg/s = 0.107×10⁻³ m³/s: W_pump = Q_vol × delta_P / eta_pump = 0.107×10⁻³ × 32,000 / 0.5 = 6.9 W. COP = 50,000 / 6.9 = 7,246 — extremely efficient.
