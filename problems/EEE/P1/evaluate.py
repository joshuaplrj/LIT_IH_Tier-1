"""
GridBrain — Evaluation / Scoring Script
EEE-P1

Usage:
    python evaluate.py --submission submission/schedule.json \
                       [--data prerequisites/EEE/EEE-P1/microgrid_data.csv] \
                       [--specs prerequisites/EEE/EEE-P1/equipment_specs.json]

Outputs a JSON scoring report to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

WEIGHT_COST      = 0.35
WEIGHT_EMISSIONS = 0.25
WEIGHT_CONSTRAINTS = 0.25
WEIGHT_QUALITY   = 0.15

MAX_LOAD_SHED_HOURS  = 10        # per year
MAX_DIESEL_KW        = 300.0
SOC_MIN_PCT          = 10.0
SOC_MAX_PCT          = 90.0
CO2_PER_KWH_KG       = 0.7      # kg CO2 per kWh diesel


def error_result(msg: str) -> dict:
    return {
        "total": 0,
        "breakdown": {},
        "errors": [msg],
    }


# ─────────────────────────────────────────────
# BASELINE RUNNER (mirrors starter.py)
# ─────────────────────────────────────────────

def compute_baseline_cost(df: pd.DataFrame, specs: dict) -> float:
    """Greedy baseline total fuel cost."""
    die = specs["diesel_generator"]
    bat = specs["battery"]

    E_cap      = bat["capacity_kwh"]
    soc_min    = bat["soc_min_pct"] / 100.0
    soc_max    = bat["soc_max_pct"] / 100.0
    eta_chg    = bat["charge_efficiency_pct"] / 100.0
    eta_dis    = bat["discharge_efficiency_pct"] / 100.0
    p_die_max  = die["capacity_kw"]
    fuel_usd_kwh = die["fuel_cost_usd_per_liter"] * die["fuel_consumption_l_per_kwh"]

    soc = 0.5
    total_fuel_cost = 0.0

    for _, row in df.iterrows():
        net = row["net_load_kW"]
        p_die = 0.0

        if net < 0:
            surplus = -net
            max_chg_kwh = (soc_max - soc) * E_cap
            p_chg = min(surplus, max_chg_kwh / eta_chg)
            soc += p_chg * eta_chg / E_cap
        else:
            avail_dis_kwh = (soc - soc_min) * E_cap
            p_dis = min(net, avail_dis_kwh * eta_dis)
            soc -= (p_dis / eta_dis) / E_cap
            remaining = net - p_dis
            p_die = min(remaining, p_die_max)

        total_fuel_cost += p_die * fuel_usd_kwh

    return total_fuel_cost


def compute_baseline_emissions(df: pd.DataFrame, specs: dict) -> float:
    """Return baseline total CO2 kg (from diesel kWh × CO2_PER_KWH_KG)."""
    die = specs["diesel_generator"]
    bat = specs["battery"]

    E_cap      = bat["capacity_kwh"]
    soc_min    = bat["soc_min_pct"] / 100.0
    soc_max    = bat["soc_max_pct"] / 100.0
    eta_chg    = bat["charge_efficiency_pct"] / 100.0
    eta_dis    = bat["discharge_efficiency_pct"] / 100.0
    p_die_max  = die["capacity_kw"]

    soc = 0.5
    total_diesel_kwh = 0.0

    for _, row in df.iterrows():
        net = row["net_load_kW"]
        p_die = 0.0

        if net < 0:
            surplus = -net
            max_chg_kwh = (soc_max - soc) * E_cap
            p_chg = min(surplus, max_chg_kwh / eta_chg)
            soc += p_chg * eta_chg / E_cap
        else:
            avail_dis_kwh = (soc - soc_min) * E_cap
            p_dis = min(net, avail_dis_kwh * eta_dis)
            soc -= (p_dis / eta_dis) / E_cap
            remaining = net - p_dis
            p_die = min(remaining, p_die_max)

        total_diesel_kwh += p_die

    return total_diesel_kwh * CO2_PER_KWH_KG


# ─────────────────────────────────────────────
# CONSTRAINT CHECKER
# ─────────────────────────────────────────────

def check_constraints(hourly: list, specs: dict) -> dict:
    """
    Returns a dict with:
      violations: list of violation strings
      constraint_score: 0–25 (full marks if all pass)
    """
    bat  = specs["battery"]
    die  = specs["diesel_generator"]

    soc_min = bat["soc_min_pct"]
    soc_max = bat["soc_max_pct"]
    p_die_max = die["capacity_kw"]

    violations = []
    soc_violations = 0
    diesel_violations = 0
    shed_hours = 0

    for row in hourly:
        soc = row.get("battery_soc_pct", 50.0)
        p_die = row.get("diesel_output_kw", 0.0)
        p_shed = row.get("load_shed_kw", 0.0)

        if soc < soc_min - 0.5:
            soc_violations += 1
        if soc > soc_max + 0.5:
            soc_violations += 1
        if p_die > p_die_max + 1.0:
            diesel_violations += 1
        if p_shed > 0.1:
            shed_hours += 1

    if soc_violations > 0:
        violations.append(f"SOC out-of-bounds in {soc_violations} hours")
    if diesel_violations > 0:
        violations.append(f"Diesel over-limit in {diesel_violations} hours")
    if shed_hours > MAX_LOAD_SHED_HOURS:
        violations.append(
            f"Load shedding in {shed_hours} hours (limit: {MAX_LOAD_SHED_HOURS})"
        )

    # Scoring: full 25 pts if zero violations, deduct per category
    score = 25.0
    if soc_violations > 0:
        score -= 8.0 * min(soc_violations / 100.0, 1.0)
    if diesel_violations > 0:
        score -= 7.0 * min(diesel_violations / 50.0, 1.0)
    if shed_hours > MAX_LOAD_SHED_HOURS:
        excess = shed_hours - MAX_LOAD_SHED_HOURS
        score -= 10.0 * min(excess / 100.0, 1.0)

    return {
        "violations": violations,
        "shed_hours": shed_hours,
        "soc_violations": soc_violations,
        "diesel_violations": diesel_violations,
        "constraint_score": max(round(score, 2), 0.0),
    }


# ─────────────────────────────────────────────
# QUALITY CHECKER
# ─────────────────────────────────────────────

def check_quality(submission: dict) -> dict:
    """Check metadata completeness and sensitivity analysis."""
    score = 0.0
    notes = []

    meta = submission.get("metadata", {})
    if meta.get("solver"):
        score += 3.0
    else:
        notes.append("Missing 'solver' field in metadata")

    if meta.get("total_cost_usd", 0) > 0:
        score += 3.0
    else:
        notes.append("total_cost_usd is zero or missing")

    sens = submission.get("sensitivity_analysis", {})
    if "fuel_price_2x" in sens and sens["fuel_price_2x"].get("total_cost_usd", 0) > 0:
        score += 4.5
    else:
        notes.append("Missing or zero fuel_price_2x sensitivity result")

    if "solar_capacity_1_5x" in sens and sens["solar_capacity_1_5x"].get("total_cost_usd", 0) > 0:
        score += 4.5
    else:
        notes.append("Missing or zero solar_capacity_1_5x sensitivity result")

    return {"quality_score": round(score, 2), "notes": notes}


# ─────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────

def evaluate(submission_path: str, data_path: str, specs_path: str) -> dict:
    errors = []

    # --- Load submission ---
    try:
        with open(submission_path) as f:
            submission = json.load(f)
    except FileNotFoundError:
        return error_result(f"Submission file not found: {submission_path}")
    except json.JSONDecodeError as e:
        return error_result(f"Invalid JSON in submission: {e}")

    hourly = submission.get("hourly_schedule", [])
    if not hourly:
        return error_result("'hourly_schedule' is empty or missing")

    # --- Load ground truth data ---
    try:
        df = pd.read_csv(data_path, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        with open(specs_path) as f:
            specs = json.load(f)
    except FileNotFoundError as e:
        return error_result(f"Data file not found: {e}")

    # ── COST SCORE (35 pts) ──────────────────
    baseline_cost = compute_baseline_cost(df, specs)
    sub_cost = submission.get("metadata", {}).get("total_cost_usd", None)

    if sub_cost is None:
        # Try to compute from hourly
        die = specs["diesel_generator"]
        fuel_usd_kwh = die["fuel_cost_usd_per_liter"] * die["fuel_consumption_l_per_kwh"]
        sub_cost = sum(r.get("diesel_output_kw", 0) for r in hourly) * fuel_usd_kwh

    if baseline_cost > 0:
        cost_reduction = max(0.0, 1.0 - sub_cost / baseline_cost)
    else:
        cost_reduction = 0.0

    # Score: 35 pts for ≥50% cost reduction, linear scaling
    cost_score = round(min(35.0, 35.0 * cost_reduction / 0.50), 2)

    # ── EMISSIONS SCORE (25 pts) ─────────────
    baseline_emissions = compute_baseline_emissions(df, specs)
    sub_emissions = submission.get("metadata", {}).get("total_emissions_kg_co2", None)

    if sub_emissions is None:
        diesel_kwh = sum(r.get("diesel_output_kw", 0) for r in hourly)
        sub_emissions = diesel_kwh * CO2_PER_KWH_KG

    if baseline_emissions > 0:
        emission_reduction = max(0.0, 1.0 - sub_emissions / baseline_emissions)
    else:
        emission_reduction = 0.0

    emission_score = round(min(25.0, 25.0 * emission_reduction / 0.50), 2)

    # ── CONSTRAINT SCORE (25 pts) ────────────
    constraint_result = check_constraints(hourly, specs)
    constraint_score = constraint_result["constraint_score"]
    if constraint_result["violations"]:
        errors.extend(constraint_result["violations"])

    # ── QUALITY SCORE (15 pts) ───────────────
    quality_result = check_quality(submission)
    quality_score = quality_result["quality_score"]
    if quality_result["notes"]:
        errors.extend(quality_result["notes"])

    total = round(cost_score + emission_score + constraint_score + quality_score, 2)

    return {
        "total": total,
        "breakdown": {
            "cost_reduction": {
                "score": cost_score,
                "max": 35,
                "detail": f"Cost ${sub_cost:,.0f} vs baseline ${baseline_cost:,.0f} "
                          f"({100*cost_reduction:.1f}% reduction)",
            },
            "emission_reduction": {
                "score": emission_score,
                "max": 25,
                "detail": f"Emissions {sub_emissions:,.0f} kg vs baseline "
                          f"{baseline_emissions:,.0f} kg ({100*emission_reduction:.1f}% reduction)",
            },
            "constraint_satisfaction": {
                "score": constraint_score,
                "max": 25,
                "detail": {
                    "shed_hours": constraint_result["shed_hours"],
                    "soc_violations": constraint_result["soc_violations"],
                    "diesel_violations": constraint_result["diesel_violations"],
                },
            },
            "solution_quality": {
                "score": quality_score,
                "max": 15,
                "detail": quality_result["notes"],
            },
        },
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="GridBrain Evaluator")
    parser.add_argument("--submission", required=True, help="Path to schedule.json")
    parser.add_argument("--data",  default="prerequisites/EEE/EEE-P1/microgrid_data.csv")
    parser.add_argument("--specs", default="prerequisites/EEE/EEE-P1/equipment_specs.json")
    args = parser.parse_args()

    result = evaluate(args.submission, args.data, args.specs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
