# GridBrain — Hints

> Each tier reveals progressively more implementation detail and carries a score penalty. Only request a tier when you are genuinely stuck. Penalties are cumulative — requesting Tier 3 costs -30% in total.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

This is a **multi-objective energy dispatch problem** on a time series. You need to decide, for each hour, how much power to take from the battery, how much to run the diesel generator, and whether any load must be shed — subject to physics constraints (energy balance, SOC bounds). The key insight is that decisions today (charging the battery) affect your options tomorrow (having reserve for tonight). Think about how to represent state, transitions, and cost over a planning horizon.

---

## Tier 2 — Technique Guidance (-10% score penalty)

Use **Mixed-Integer Linear Programming (MILP)** with a **rolling 24-hour horizon** (also called Model Predictive Control, MPC). Specifically:

- **Decision variables per hour:** battery charge power P_chg (kW), battery discharge power P_dis (kW), diesel output P_die (kW), load shed P_shed (kW), binary diesel-on flag u_die (0/1).
- **State variable:** battery SOC carried forward across windows.
- **Objective:** minimize hourly fuel cost + startup cost + battery degradation penalty + load shed penalty, summed over 24 hours.
- **Library:** `PuLP` or `cvxpy` with the `GLPK` or `CBC` solver (both free, both installable via pip).
- Roll the window forward 1 hour at a time, always re-solving with updated forecasts — this is why it is called "receding horizon."

For the 20-year projection, scale up the single-year results and apply the battery degradation model from `equipment_specs.json` to estimate when battery replacement occurs.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**MILP formulation (per-hour index t, window T = 24):**

1. **Energy balance constraint:**
   `P_solar[t] + P_wind[t] + P_dis[t] + P_die[t] = P_load[t] - P_shed[t] + P_chg[t]`

2. **SOC dynamics:**
   `SOC[t+1] = SOC[t] + (eta_chg * P_chg[t] - P_dis[t] / eta_dis) / E_cap`
   where `eta_chg = 0.95`, `eta_dis = 0.95`, `E_cap = 2000 kWh`.

3. **SOC bounds:** `0.10 * E_cap <= SOC[t] <= 0.90 * E_cap`

4. **Diesel limits:** `0 <= P_die[t] <= 300 * u_die[t]`, `u_die[t]` is binary.

5. **No simultaneous charge and discharge:** add `P_chg[t] * P_dis[t] = 0` (linearize with a binary: introduce b_chg, b_dis binary flags with P_chg <= M * b_chg, P_dis <= M * b_dis, b_chg + b_dis <= 1).

6. **Objective (minimize):**
   ```
   sum_t [ fuel_cost_usd_per_kwh * P_die[t]
         + startup_cost * u_die[t]
         + deg_penalty * (P_chg[t] + P_dis[t]) / (2 * E_cap)
         + shed_penalty * P_shed[t] ]
   ```
   Use `fuel_cost_usd_per_kwh = 1.50 * 0.25 = 0.375`, `startup_cost = 5`, `deg_penalty = 400000 * 0.0001` (per cycle fraction), `shed_penalty = 10` (large penalty to discourage shedding).

7. **Carry forward:** after solving window [t, t+24), fix `SOC_init` for the next window to `SOC[24]` from the solution.

8. **Sensitivity analysis:** re-run with `fuel_cost_usd_per_liter = 3.00` (×2) and with solar scaled by 1.5 in the data, report the new total annual cost.
