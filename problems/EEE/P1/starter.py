"""
GridBrain — AI-Optimized Microgrid Energy Management
Starter skeleton for EEE-P1.

Usage:
    python starter.py --data microgrid_data.csv \
                      --specs equipment_specs.json \
                      --output submission/schedule.json \
                      [--horizon 24] [--fuel_multiplier 1.0]
"""

import argparse
import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Optimization — uncomment the library you prefer.
# Option A: PuLP (LP/MILP, free, no extra license)
try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    warnings.warn("PuLP not found. Install with: pip install pulp")

# Option B: CVXPY (convex + MILP via CBC/GLPK)
try:
    import cvxpy as cp
    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False

# ─────────────────────────────────────────────
# 1. DATA LOADING
# ─────────────────────────────────────────────

def load_data(data_path: str, specs_path: str):
    """Load the microgrid CSV and equipment JSON."""
    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    with open(specs_path) as f:
        specs = json.load(f)

    print(f"[INFO] Loaded {len(df)} hourly rows from {data_path}")
    print(f"[INFO] Date range: {df['timestamp'].iloc[0]} — {df['timestamp'].iloc[-1]}")
    print(f"[INFO] Equipment specs keys: {list(specs.keys())}")
    return df, specs


# ─────────────────────────────────────────────
# 2. BASELINE (rule-based: renewables → battery → diesel)
# ─────────────────────────────────────────────

def run_baseline(df: pd.DataFrame, specs: dict) -> pd.DataFrame:
    """
    Greedy rule-based dispatch:
      1. Use all available renewable generation.
      2. Charge / discharge battery to cover the net load.
      3. Use diesel only when battery cannot cover the deficit.
      4. Shed load if diesel + battery at maximum still cannot cover demand.

    Returns a DataFrame with the same index as df, plus dispatch columns.
    """
    bat = specs["battery"]
    die = specs["diesel_generator"]

    E_cap = bat["capacity_kwh"]
    soc_min = bat["soc_min_pct"] / 100.0
    soc_max = bat["soc_max_pct"] / 100.0
    eta_chg = bat["charge_efficiency_pct"] / 100.0
    eta_dis = bat["discharge_efficiency_pct"] / 100.0
    p_die_max = die["capacity_kw"]
    fuel_usd_kwh = die["fuel_cost_usd_per_liter"] * die["fuel_consumption_l_per_kwh"]

    soc = 0.5  # start at 50 %
    records = []

    for _, row in df.iterrows():
        net = row["net_load_kW"]  # positive = deficit, negative = surplus

        p_chg = p_dis = p_die = p_shed = 0.0

        if net < 0:
            # Surplus renewable — charge battery
            surplus = -net
            max_charge_kwh = (soc_max - soc) * E_cap
            p_chg = min(surplus, max_charge_kwh / eta_chg)
            soc += p_chg * eta_chg / E_cap

        else:
            # Deficit — discharge battery first
            avail_dis_kwh = (soc - soc_min) * E_cap
            p_dis = min(net, avail_dis_kwh * eta_dis)
            soc -= (p_dis / eta_dis) / E_cap
            remaining = net - p_dis

            if remaining > 0:
                # Use diesel
                p_die = min(remaining, p_die_max)
                remaining -= p_die

            if remaining > 0:
                # Load shed
                p_shed = remaining

        fuel_cost = fuel_usd_kwh * p_die
        records.append({
            "battery_charge_kw": round(p_chg, 3),
            "battery_discharge_kw": round(p_dis, 3),
            "diesel_output_kw": round(p_die, 3),
            "load_shed_kw": round(p_shed, 3),
            "battery_soc_pct": round(soc * 100, 2),
            "hourly_fuel_cost_usd": round(fuel_cost, 4),
        })

    result = df.copy()
    result = pd.concat([result, pd.DataFrame(records, index=df.index)], axis=1)
    return result


# ─────────────────────────────────────────────
# 3. MILP OPTIMIZER (rolling horizon MPC)
# ─────────────────────────────────────────────

def solve_window_pulp(
    net_load: np.ndarray,
    soc_init: float,
    specs: dict,
    fuel_multiplier: float = 1.0,
) -> dict:
    """
    Solve a single MILP window using PuLP.

    Parameters
    ----------
    net_load    : array of shape (T,), kW — positive = deficit
    soc_init    : initial SOC as a fraction [0, 1]
    specs       : equipment_specs dict
    fuel_multiplier : scale fuel cost (1.0 = nominal, 2.0 = doubled)

    Returns
    -------
    dict with keys: p_chg, p_dis, p_die, p_shed, soc (all numpy arrays, length T),
                    and final_soc (float).
    """
    if not HAS_PULP:
        raise ImportError("PuLP is required for solve_window_pulp.")

    T = len(net_load)
    bat = specs["battery"]
    die = specs["diesel_generator"]

    E_cap = bat["capacity_kwh"]
    soc_min = bat["soc_min_pct"] / 100.0
    soc_max = bat["soc_max_pct"] / 100.0
    eta_chg = bat["charge_efficiency_pct"] / 100.0
    eta_dis = bat["discharge_efficiency_pct"] / 100.0
    p_die_max = die["capacity_kw"]
    p_chg_max = E_cap * (soc_max - soc_min)  # max 1-hour charge rate (conservative)
    p_dis_max = E_cap * (soc_max - soc_min)

    fuel_cost_per_kwh = (
        die["fuel_cost_usd_per_liter"]
        * die["fuel_consumption_l_per_kwh"]
        * fuel_multiplier
    )
    startup_cost = die["startup_cost_usd"]
    deg_penalty = bat["replacement_cost_usd"] * (bat["degradation_per_cycle_pct"] / 100.0)
    shed_penalty = 1000.0  # large $/kWh to strongly discourage load shedding

    prob = pulp.LpProblem("GridBrain_Window", pulp.LpMinimize)

    # Decision variables
    P_chg = [pulp.LpVariable(f"P_chg_{t}", lowBound=0, upBound=p_chg_max) for t in range(T)]
    P_dis = [pulp.LpVariable(f"P_dis_{t}", lowBound=0, upBound=p_dis_max) for t in range(T)]
    P_die = [pulp.LpVariable(f"P_die_{t}", lowBound=0, upBound=p_die_max) for t in range(T)]
    P_shed = [pulp.LpVariable(f"P_shed_{t}", lowBound=0) for t in range(T)]
    u_die = [pulp.LpVariable(f"u_die_{t}", cat="Binary") for t in range(T)]
    b_chg = [pulp.LpVariable(f"b_chg_{t}", cat="Binary") for t in range(T)]
    b_dis = [pulp.LpVariable(f"b_dis_{t}", cat="Binary") for t in range(T)]
    SOC = [pulp.LpVariable(f"SOC_{t}", lowBound=soc_min * E_cap, upBound=soc_max * E_cap)
           for t in range(T + 1)]

    # Initial SOC
    prob += SOC[0] == soc_init * E_cap

    for t in range(T):
        net_t = net_load[t]

        # Energy balance: supply = demand
        # supply = renewable (already in net_load as deficit) + discharge + diesel
        # demand = net_load + charge
        # net_load = load - renewable  =>  load = net_load + renewable (positive deficit)
        # Balance: P_dis[t] + P_die[t] + P_shed_unused = net_load[t] + P_chg[t]
        # Rewritten: P_dis[t] + P_die[t] - P_chg[t] - P_shed[t] + P_shed[t] = net_load[t]
        # i.e. net supply covers net demand, load shed reduces required supply
        prob += P_dis[t] + P_die[t] + P_shed[t] - P_chg[t] == net_t

        # SOC dynamics (1 hour timestep)
        prob += SOC[t + 1] == SOC[t] + eta_chg * P_chg[t] - P_dis[t] / eta_dis

        # Diesel linked to binary
        prob += P_die[t] <= p_die_max * u_die[t]

        # No simultaneous charge and discharge
        prob += P_chg[t] <= p_chg_max * b_chg[t]
        prob += P_dis[t] <= p_dis_max * b_dis[t]
        prob += b_chg[t] + b_dis[t] <= 1

    # Objective: fuel + startup + degradation + shed penalty
    cost_terms = []
    for t in range(T):
        cost_terms.append(fuel_cost_per_kwh * P_die[t])
        cost_terms.append(startup_cost * u_die[t])
        cost_terms.append(deg_penalty / (2 * E_cap) * (P_chg[t] + P_dis[t]))
        cost_terms.append(shed_penalty * P_shed[t])
    prob += pulp.lpSum(cost_terms)

    # Solve (suppress solver output)
    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)

    def val(v):
        return max(pulp.value(v) or 0.0, 0.0)

    return {
        "p_chg": np.array([val(P_chg[t]) for t in range(T)]),
        "p_dis": np.array([val(P_dis[t]) for t in range(T)]),
        "p_die": np.array([val(P_die[t]) for t in range(T)]),
        "p_shed": np.array([val(P_shed[t]) for t in range(T)]),
        "soc": np.array([val(SOC[t + 1]) / E_cap * 100 for t in range(T)]),
        "final_soc": val(SOC[T]) / E_cap,
        "status": pulp.LpStatus[prob.status],
    }


def run_milp_optimizer(
    df: pd.DataFrame,
    specs: dict,
    horizon: int = 24,
    fuel_multiplier: float = 1.0,
) -> pd.DataFrame:
    """
    Roll a MILP window of length `horizon` across the full year.
    Returns a DataFrame with dispatch decisions for each hour.
    """
    net_load = df["net_load_kW"].values
    N = len(net_load)
    soc_carry = 0.5  # starting SOC

    all_chg, all_dis, all_die, all_shed, all_soc = ([] for _ in range(5))

    for start in range(0, N, horizon):
        end = min(start + horizon, N)
        window = net_load[start:end]

        # TODO: replace with your own optimizer if not using PuLP
        result = solve_window_pulp(window, soc_carry, specs, fuel_multiplier)

        steps = end - start
        all_chg.extend(result["p_chg"][:steps])
        all_dis.extend(result["p_dis"][:steps])
        all_die.extend(result["p_die"][:steps])
        all_shed.extend(result["p_shed"][:steps])
        all_soc.extend(result["soc"][:steps])
        soc_carry = result["final_soc"]

        if (start // horizon) % 30 == 0:
            pct = 100 * start / N
            print(f"[INFO] MILP progress: {pct:.0f}% (hour {start}/{N})")

    result_df = df.copy()
    result_df["battery_charge_kw"] = np.round(all_chg, 3)
    result_df["battery_discharge_kw"] = np.round(all_dis, 3)
    result_df["diesel_output_kw"] = np.round(all_die, 3)
    result_df["load_shed_kw"] = np.round(all_shed, 3)
    result_df["battery_soc_pct"] = np.round(all_soc, 2)
    return result_df


# ─────────────────────────────────────────────
# 4. METRICS
# ─────────────────────────────────────────────

def compute_metrics(dispatch_df: pd.DataFrame, specs: dict, fuel_multiplier: float = 1.0) -> dict:
    """Compute cost, emissions, shedding, and battery cycle count."""
    die = specs["diesel_generator"]
    bat = specs["battery"]

    fuel_usd_kwh = (
        die["fuel_cost_usd_per_liter"]
        * die["fuel_consumption_l_per_kwh"]
        * fuel_multiplier
    )
    CO2_per_kwh_kg = 0.7  # ~0.7 kg CO2 per kWh diesel (typical)

    total_diesel_kwh = dispatch_df["diesel_output_kw"].sum()
    total_cost_usd = total_diesel_kwh * fuel_usd_kwh
    total_emissions_kg = total_diesel_kwh * CO2_per_kwh_kg
    load_shedding_hours = int((dispatch_df["load_shed_kw"] > 0.1).sum())

    # Battery equivalent full cycles (sum of discharge / 2 / capacity)
    E_cap = bat["capacity_kwh"]
    battery_cycles = dispatch_df["battery_discharge_kw"].sum() / (2.0 * E_cap)

    return {
        "total_cost_usd": round(total_cost_usd, 2),
        "total_emissions_kg_co2": round(total_emissions_kg, 2),
        "load_shedding_hours": load_shedding_hours,
        "battery_cycles": round(battery_cycles, 2),
        "total_diesel_kwh": round(total_diesel_kwh, 2),
    }


# ─────────────────────────────────────────────
# 5. OUTPUT
# ─────────────────────────────────────────────

def build_submission(dispatch_df: pd.DataFrame, metrics: dict,
                     sens_fuel2x: dict, sens_solar15x: dict) -> dict:
    """Assemble the submission JSON."""
    hourly = []
    for i, row in dispatch_df.iterrows():
        hourly.append({
            "hour": int(i),
            "battery_charge_kw": float(row["battery_charge_kw"]),
            "battery_discharge_kw": float(row["battery_discharge_kw"]),
            "diesel_output_kw": float(row["diesel_output_kw"]),
            "load_shed_kw": float(row["load_shed_kw"]),
            "battery_soc_pct": float(row["battery_soc_pct"]),
        })

    return {
        "metadata": {
            "solver": "MILP-MPC (PuLP/CBC)",
            "horizon_hours": 8760,
            "total_cost_usd": metrics["total_cost_usd"],
            "total_emissions_kg_co2": metrics["total_emissions_kg_co2"],
            "load_shedding_hours": metrics["load_shedding_hours"],
            "battery_cycles": metrics["battery_cycles"],
        },
        "hourly_schedule": hourly,
        "sensitivity_analysis": {
            "fuel_price_2x": {"total_cost_usd": sens_fuel2x.get("total_cost_usd", 0)},
            "solar_capacity_1_5x": {"total_cost_usd": sens_solar15x.get("total_cost_usd", 0)},
        },
    }


# ─────────────────────────────────────────────
# 6. MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GridBrain EMS Optimizer")
    parser.add_argument("--data",    default="prerequisites/EEE/EEE-P1/microgrid_data.csv",
                        help="Path to microgrid_data.csv")
    parser.add_argument("--specs",   default="prerequisites/EEE/EEE-P1/equipment_specs.json",
                        help="Path to equipment_specs.json")
    parser.add_argument("--output",  default="submission/schedule.json",
                        help="Output schedule JSON path")
    parser.add_argument("--horizon", type=int, default=24,
                        help="MPC rolling window length in hours (default: 24)")
    parser.add_argument("--fuel_multiplier", type=float, default=1.0,
                        help="Multiply fuel cost for sensitivity (1.0 = nominal)")
    args = parser.parse_args()

    # --- Load data ---
    df, specs = load_data(args.data, args.specs)

    # --- Baseline ---
    print("[INFO] Running rule-based baseline...")
    baseline_df = run_baseline(df, specs)
    baseline_metrics = compute_metrics(baseline_df, specs)
    print(f"[BASELINE] Cost=${baseline_metrics['total_cost_usd']:,.0f}  "
          f"Shed={baseline_metrics['load_shedding_hours']}h  "
          f"Cycles={baseline_metrics['battery_cycles']:.1f}")

    # --- MILP optimizer ---
    print(f"[INFO] Running MILP optimizer (horizon={args.horizon}h)...")
    dispatch_df = run_milp_optimizer(df, specs, args.horizon, args.fuel_multiplier)
    metrics = compute_metrics(dispatch_df, specs, args.fuel_multiplier)
    print(f"[MILP]     Cost=${metrics['total_cost_usd']:,.0f}  "
          f"Shed={metrics['load_shedding_hours']}h  "
          f"Cycles={metrics['battery_cycles']:.1f}")

    # --- Sensitivity: fuel price × 2 ---
    print("[INFO] Sensitivity: fuel × 2 ...")
    sens_df_fuel = run_milp_optimizer(df, specs, args.horizon, fuel_multiplier=2.0)
    sens_fuel2x = compute_metrics(sens_df_fuel, specs, fuel_multiplier=2.0)

    # --- Sensitivity: solar capacity × 1.5 ---
    print("[INFO] Sensitivity: solar capacity × 1.5 ...")
    df_solar15x = df.copy()
    df_solar15x["solar_output_kW"] = df_solar15x["solar_output_kW"] * 1.5
    df_solar15x["renewable_total_kW"] = df_solar15x["solar_output_kW"] + df_solar15x["wind_output_kW"]
    df_solar15x["net_load_kW"] = df_solar15x["load_demand_kW"] - df_solar15x["renewable_total_kW"]
    sens_df_solar = run_milp_optimizer(df_solar15x, specs, args.horizon, args.fuel_multiplier)
    sens_solar15x = compute_metrics(sens_df_solar, specs, args.fuel_multiplier)

    # --- Build & save submission ---
    submission = build_submission(dispatch_df, metrics, sens_fuel2x, sens_solar15x)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"[INFO] Submission written to {out_path}")
    print(f"[INFO] Cost improvement vs. baseline: "
          f"{100*(1 - metrics['total_cost_usd']/baseline_metrics['total_cost_usd']):.1f}%")


if __name__ == "__main__":
    main()
