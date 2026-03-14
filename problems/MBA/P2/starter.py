"""
MBA-P2: PricingGenius — Dynamic Pricing Analysis Scaffold
==========================================================
GoRide ride-hailing platform: build a dynamic pricing model using
rides.csv, competitor_prices.csv, events.csv, and weather.csv.

Data directory (default): prerequisites/MBA/MBA-P2/

Usage:
    python starter.py [--data-dir <path>] [--output analysis.json] [--sample 50000]

Outputs:
    analysis.json  — demand statistics, elasticity estimates, pricing simulation
"""

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: str, max_rows: int = None) -> list:
    """Load a CSV file as a list of dicts. Optionally cap at max_rows."""
    if not os.path.exists(path):
        print(f"  [WARNING] File not found: {path}")
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break
            rows.append(row)
    return rows


def parse_hour(ts_str: str) -> int:
    """Extract hour-of-day from timestamp string 'YYYY-MM-DD HH:MM:SS'."""
    try:
        return int(ts_str[11:13])
    except (IndexError, ValueError):
        return -1


def parse_dow(ts_str: str) -> int:
    """Return day-of-week (0=Mon, 6=Sun) from timestamp string."""
    try:
        dt = datetime.strptime(ts_str[:10], "%Y-%m-%d")
        return dt.weekday()
    except ValueError:
        return -1


def is_peak(hour: int) -> bool:
    """Morning peak 7–9, evening peak 17–20."""
    return (7 <= hour <= 9) or (17 <= hour <= 20)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: DEMAND SUMMARY STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_demand_stats(rides: list) -> dict:
    """
    Aggregate ride demand patterns:
    - Rides by hour of day
    - Rides by day of week
    - Cancellation rate by surge bucket
    - Average price by peak/off-peak
    """
    hour_counts = defaultdict(int)
    dow_counts = defaultdict(int)
    surge_buckets = {"1.0-1.5": [], "1.5-2.0": [], "2.0-3.0": []}
    peak_prices = []
    offpeak_prices = []

    for r in rides:
        ts = r.get("timestamp", "")
        hour = parse_hour(ts)
        dow = parse_dow(ts)

        if hour >= 0:
            hour_counts[hour] += 1
        if dow >= 0:
            dow_counts[dow] += 1

        try:
            surge = float(r.get("surge_multiplier", 1.0))
            cancelled = int(r.get("cancelled", 0))
            price = float(r.get("final_price_usd", 0))

            if 1.0 <= surge < 1.5:
                surge_buckets["1.0-1.5"].append(cancelled)
            elif 1.5 <= surge < 2.0:
                surge_buckets["1.5-2.0"].append(cancelled)
            elif surge >= 2.0:
                surge_buckets["2.0-3.0"].append(cancelled)

            if hour >= 0:
                if is_peak(hour):
                    peak_prices.append(price)
                else:
                    offpeak_prices.append(price)
        except (ValueError, TypeError):
            continue

    # Cancellation rate per surge bucket
    cancellation_by_surge = {}
    for bucket, cancelled_list in surge_buckets.items():
        if cancelled_list:
            rate = sum(cancelled_list) / len(cancelled_list)
            cancellation_by_surge[bucket] = {
                "n_rides": len(cancelled_list),
                "cancellation_rate": round(rate, 4),
            }

    def safe_mean(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    return {
        "total_rides_sampled": len(rides),
        "rides_by_hour": {str(h): hour_counts[h] for h in sorted(hour_counts)},
        "rides_by_dow": {str(d): dow_counts[d] for d in sorted(dow_counts)},
        "cancellation_by_surge_bucket": cancellation_by_surge,
        "avg_price_peak_usd": safe_mean(peak_prices),
        "avg_price_offpeak_usd": safe_mean(offpeak_prices),
        "peak_ride_count": len(peak_prices),
        "offpeak_ride_count": len(offpeak_prices),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: PRICE ELASTICITY ESTIMATION (OLS log-log stub)
# ─────────────────────────────────────────────────────────────────────────────

def estimate_price_elasticity(rides: list, segment: str = "all") -> dict:
    """
    Estimate price elasticity of demand using a simplified log-log regression stub.

    Full approach:
        log(demand_zone_hour) = α + β × log(avg_price_zone_hour) + γ × features
        β = price elasticity of demand

    This stub aggregates rides by (city, hour_bucket, dow) and computes
    correlation between log(price) and log(ride_count) as a proxy.

    TODO: Replace with a proper OLS or ML model using sklearn or statsmodels.
    """
    # Aggregate: (city, hour_bucket, dow) -> (total_rides, avg_price, cancellation_rate)
    agg = defaultdict(lambda: {"rides": 0, "prices": [], "cancelled": 0})

    for r in rides:
        ts = r.get("timestamp", "")
        hour = parse_hour(ts)
        dow = parse_dow(ts)
        city = r.get("city", "unknown")

        if hour < 0 or dow < 0:
            continue

        # Apply segment filter
        if segment == "peak" and not is_peak(hour):
            continue
        if segment == "offpeak" and is_peak(hour):
            continue

        hour_bucket = hour // 3    # 0-7 (3-hour buckets)
        key = (city, hour_bucket, dow)

        try:
            price = float(r.get("final_price_usd", 0))
            cancelled = int(r.get("cancelled", 0))
            agg[key]["rides"] += 1
            agg[key]["prices"].append(price)
            agg[key]["cancelled"] += cancelled
        except (ValueError, TypeError):
            continue

    if len(agg) < 10:
        return {
            "segment": segment,
            "elasticity": None,
            "n_observations": len(agg),
            "note": "Insufficient data for elasticity estimation — load more rows",
        }

    # Compute log(price) and log(ride_count) for each cell
    log_prices = []
    log_counts = []

    for key, data in agg.items():
        if data["rides"] > 0 and data["prices"]:
            avg_price = sum(data["prices"]) / len(data["prices"])
            if avg_price > 0 and data["rides"] > 0:
                log_prices.append(math.log(avg_price))
                log_counts.append(math.log(data["rides"]))

    n = len(log_prices)
    if n < 5:
        return {"segment": segment, "elasticity": None, "n_observations": n,
                "note": "Too few observations after log transform"}

    # Simple Pearson correlation as proxy for log-log slope
    mean_lp = sum(log_prices) / n
    mean_lc = sum(log_counts) / n
    cov = sum((log_prices[i] - mean_lp) * (log_counts[i] - mean_lc) for i in range(n)) / n
    var_lp = sum((x - mean_lp) ** 2 for x in log_prices) / n
    var_lc = sum((x - mean_lc) ** 2 for x in log_counts) / n

    # Regression slope = cov / var(log_price) (simplified OLS)
    slope = cov / var_lp if var_lp > 0 else 0.0
    r_squared_proxy = (cov ** 2 / (var_lp * var_lc)) if (var_lp * var_lc) > 0 else 0.0

    return {
        "segment": segment,
        "elasticity": round(slope, 4),
        "n_observations": n,
        "r_squared_proxy": round(r_squared_proxy, 4),
        "interpretation": (
            "Elasticity < -1: elastic (price-sensitive)"
            if slope < -1 else
            "-1 < elasticity < 0: inelastic (price-insensitive)"
            if -1 <= slope < 0 else
            "Positive elasticity unexpected — check data/model"
        ),
        "note": "TODO: Replace with proper OLS (sklearn LinearRegression or statsmodels.OLS) "
                "with controls for distance, city, weather, events",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: SURGE MULTIPLIER OPTIMISER
# ─────────────────────────────────────────────────────────────────────────────

def optimise_surge(
    elasticity: float,
    base_price: float,
    competitor_price: float,
    city_surge_cap: float = 2.0,
    competitor_premium_cap: float = 1.15,
    min_surge: float = 1.0,
) -> dict:
    """
    Compute revenue-maximising surge multiplier subject to constraints.

    Revenue-maximising price (Lerner condition):
        P* = MC / (1 + 1/ε)   [but we use surge relative to base price]

    For simplicity: optimal_surge = 1 / (1 + 1/ε) when ε < -1,
    otherwise surge = 1 (price increase would reduce total revenue).

    Constraints:
        1. surge <= city_surge_cap (regulatory)
        2. base_price × surge <= competitor_price × competitor_premium_cap
        3. surge >= min_surge (never below base price)

    TODO: Replace with a full revenue maximisation model calibrated to
          your estimated demand curve from Section 2.
    """
    if elasticity is None or elasticity >= 0:
        return {
            "optimal_surge": 1.0,
            "note": "Cannot compute — elasticity must be negative",
            "revenue_impact": "neutral",
        }

    # Unconstrained optimal surge (Lerner)
    if elasticity < -1:
        unconstrained = 1.0 / (1.0 + 1.0 / elasticity)
    else:
        # Inelastic — any price increase raises revenue (up to constraints)
        unconstrained = city_surge_cap

    # Apply constraints
    competitor_cap = (competitor_price / base_price) * competitor_premium_cap if base_price > 0 else city_surge_cap
    optimal_surge = min(unconstrained, city_surge_cap, competitor_cap)
    optimal_surge = max(optimal_surge, min_surge)
    optimal_surge = round(optimal_surge, 3)

    optimal_price = round(base_price * optimal_surge, 2)
    binding_constraint = (
        "city_surge_cap" if optimal_surge == city_surge_cap else
        "competitor_parity" if abs(optimal_surge - competitor_cap) < 0.01 else
        "revenue_optimum"
    )

    return {
        "elasticity_used": elasticity,
        "unconstrained_optimal_surge": round(unconstrained, 3),
        "optimal_surge": optimal_surge,
        "optimal_price_usd": optimal_price,
        "binding_constraint": binding_constraint,
        "city_surge_cap": city_surge_cap,
        "competitor_parity_cap": round(competitor_cap, 3),
        "note": "TODO: Calibrate with your segment-level elasticity estimates",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: REVENUE SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def simulate_revenue_impact(
    rides: list,
    elasticity: float,
    new_surge_avg: float,
    current_surge_avg: float = 1.25,
) -> dict:
    """
    Estimate revenue uplift by comparing new vs. baseline pricing strategy
    on the sampled rides data.

    Assumes demand changes proportionally to price change (log-log model).

    TODO: Replace with a full simulation that applies your pricing algorithm
          to each ride in the holdout set and computes realised revenue.
    """
    if elasticity is None or elasticity >= 0 or not rides:
        return {
            "revenue_uplift_pct": None,
            "note": "Simulation requires negative elasticity and ride data",
        }

    # Baseline revenue from sampled rides
    baseline_revenue = sum(
        float(r.get("final_price_usd", 0)) for r in rides
        if r.get("cancelled", "0") == "0"
    )
    baseline_rides_completed = sum(
        1 for r in rides if r.get("cancelled", "0") == "0"
    )

    # Price change ratio
    price_ratio = new_surge_avg / current_surge_avg if current_surge_avg > 0 else 1.0

    # Demand change from elasticity: Δ%demand = ε × Δ%price
    demand_change = price_ratio ** elasticity    # log-log relationship
    new_rides_completed = baseline_rides_completed * demand_change
    new_revenue = baseline_revenue * price_ratio * demand_change

    revenue_uplift = (new_revenue - baseline_revenue) / baseline_revenue if baseline_revenue > 0 else 0
    cancellation_change = 1 - demand_change   # fraction of rides lost

    return {
        "baseline_revenue_sample_usd": round(baseline_revenue, 2),
        "new_revenue_sample_usd": round(new_revenue, 2),
        "revenue_uplift_pct": round(revenue_uplift * 100, 2),
        "demand_change_pct": round((demand_change - 1) * 100, 2),
        "estimated_cancellation_increase_pct": round(cancellation_change * 100, 2),
        "current_avg_surge": current_surge_avg,
        "new_avg_surge": new_surge_avg,
        "elasticity_used": elasticity,
        "note": "TODO: Run full simulation on holdout data with your pricing algorithm",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: COMPETITOR PRICE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyse_competitor_prices(comp_prices: list) -> dict:
    """Compute summary statistics on competitor pricing relative to GoRide."""
    if not comp_prices:
        return {"note": "No competitor price data loaded"}

    prices_by_competitor = defaultdict(list)
    for row in comp_prices:
        comp = row.get("competitor_name", "unknown")
        try:
            p = float(row.get("price_usd", 0))
            if p > 0:
                prices_by_competitor[comp].append(p)
        except (ValueError, TypeError):
            continue

    stats = {}
    for comp, prices in prices_by_competitor.items():
        n = len(prices)
        mean_p = sum(prices) / n if n else 0
        sorted_p = sorted(prices)
        p25 = sorted_p[n // 4] if n >= 4 else sorted_p[0]
        p75 = sorted_p[3 * n // 4] if n >= 4 else sorted_p[-1]
        stats[comp] = {
            "n_observations": n,
            "mean_price_usd": round(mean_p, 2),
            "p25_usd": round(p25, 2),
            "p75_usd": round(p75, 2),
        }

    return {
        "competitors_analysed": list(stats.keys()),
        "stats_by_competitor": stats,
        "note": "TODO: Join with rides.csv on (timestamp, city, origin_zone, dest_zone) "
                "to compute GoRide vs competitor price delta per ride",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MBA-P2 PricingGenius — Dynamic Pricing Analysis Scaffold"
    )
    parser.add_argument(
        "--data-dir",
        default=r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P2",
        help="Directory containing rides.csv, competitor_prices.csv, events.csv, weather.csv",
    )
    parser.add_argument("--output", default="analysis.json",
                        help="Output path for analysis JSON (default: analysis.json)")
    parser.add_argument("--sample", type=int, default=50_000,
                        help="Max rows to load from rides.csv (default: 50000)")
    parser.add_argument("--scenario-surge", type=float, default=1.35,
                        help="Target average surge multiplier to simulate (default: 1.35)")

    args = parser.parse_args()

    print(f"[MBA-P2] PricingGenius Analysis — GoRide")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Sample size: {args.sample:,} rides")

    # Load data
    print("\n[1/5] Loading data...")
    rides = load_csv(os.path.join(args.data_dir, "rides.csv"), max_rows=args.sample)
    comp_prices = load_csv(os.path.join(args.data_dir, "competitor_prices.csv"), max_rows=10_000)
    events = load_csv(os.path.join(args.data_dir, "events.csv"))
    weather = load_csv(os.path.join(args.data_dir, "weather.csv"), max_rows=5_000)
    print(f"  Rides: {len(rides):,}  Competitor rows: {len(comp_prices):,}  "
          f"Events: {len(events):,}  Weather: {len(weather):,}")

    # Demand stats
    print("[2/5] Computing demand statistics...")
    demand_stats = compute_demand_stats(rides)
    print(f"  Avg price peak: ${demand_stats['avg_price_peak_usd']}  "
          f"Avg price off-peak: ${demand_stats['avg_price_offpeak_usd']}")

    # Elasticity estimation
    print("[3/5] Estimating price elasticity (log-log OLS proxy)...")
    elasticity_all = estimate_price_elasticity(rides, segment="all")
    elasticity_peak = estimate_price_elasticity(rides, segment="peak")
    elasticity_offpeak = estimate_price_elasticity(rides, segment="offpeak")
    print(f"  Elasticity (all): {elasticity_all.get('elasticity')}  "
          f"(peak): {elasticity_peak.get('elasticity')}  "
          f"(offpeak): {elasticity_offpeak.get('elasticity')}")

    # Surge optimisation (using all-segment elasticity)
    print("[4/5] Computing optimal surge multiplier...")
    elas_val = elasticity_all.get("elasticity")
    surge_opt = optimise_surge(
        elasticity=elas_val if elas_val is not None else -0.7,
        base_price=demand_stats["avg_price_peak_usd"] or 12.0,
        competitor_price=(demand_stats["avg_price_peak_usd"] or 12.0) * 1.05,
        city_surge_cap=2.0,
    )
    print(f"  Optimal surge: {surge_opt['optimal_surge']}x  "
          f"(binding constraint: {surge_opt.get('binding_constraint', 'N/A')})")

    # Revenue simulation
    print("[5/5] Simulating revenue impact...")
    sim = simulate_revenue_impact(
        rides=rides,
        elasticity=elas_val if elas_val is not None else -0.7,
        new_surge_avg=args.scenario_surge,
        current_surge_avg=1.25,
    )
    print(f"  Revenue uplift: {sim.get('revenue_uplift_pct', 'N/A')}%  "
          f"Demand change: {sim.get('demand_change_pct', 'N/A')}%")

    # Competitor analysis
    comp_stats = analyse_competitor_prices(comp_prices)

    # Assemble output
    analysis = {
        "problem": "MBA-P2: PricingGenius",
        "parameters": {
            "sample_rides": len(rides),
            "scenario_surge": args.scenario_surge,
        },
        "demand_statistics": demand_stats,
        "elasticity_estimates": {
            "all_segments": elasticity_all,
            "peak_hours": elasticity_peak,
            "offpeak_hours": elasticity_offpeak,
        },
        "optimal_surge": surge_opt,
        "revenue_simulation": sim,
        "competitor_analysis": comp_stats,
        "summary": {
            "estimated_elasticity_all": elas_val,
            "optimal_surge_multiplier": surge_opt["optimal_surge"],
            "estimated_revenue_uplift_pct": sim.get("revenue_uplift_pct"),
            "next_steps": [
                "TODO: Add event and weather features to elasticity model",
                "TODO: Segment customers by CLV and apply discount tiers",
                "TODO: Build driver incentive optimisation model",
                "TODO: Design A/B test switchback experiment",
                "TODO: Document ethical/fairness policies",
            ],
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nOutput written to: {args.output}")
    print("NEXT STEPS:")
    print("  1. Add proper OLS/sklearn regression in estimate_price_elasticity()")
    print("  2. Segment by city, weather condition, event proximity")
    print("  3. Build driver incentive model (supply elasticity)")
    print("  4. Design A/B switchback experiment framework")
    print("  5. Write submission.json with all required sections")


if __name__ == "__main__":
    main()
