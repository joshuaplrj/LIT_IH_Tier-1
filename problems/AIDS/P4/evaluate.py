"""
AIDS-P4: AutoTrader — Evaluation / Scoring Script

Usage:
    python evaluate.py --submission <path> [--ground_truth <path>]

Options:
    --submission     Path to trades.csv produced by starter.py
                     (columns: date, ticker, action, weight, portfolio_value)
    --ground_truth   Path to benchmark CSV (default: ground_truth/AIDS_P4_gt.csv)
                     (columns: date, sp500_return, equal_weight_return)
    --metrics_json   Path to metrics.json produced by starter.py (speeds up eval)

Prints a JSON scoring result to stdout.
"""

import argparse
import csv
import json
import math
import os
import sys

import numpy as np

WEIGHTS = {
    "sharpe_ratio": 40,
    "drawdown_control": 25,
    "transaction_cost_awareness": 20,
    "strategy_documentation": 15,
}
GROUND_TRUTH_PATH = "ground_truth/AIDS_P4_gt.csv"

SHARPE_TARGET = 2.0
SHARPE_FLOOR = 0.0
MAX_DD_TARGET = 0.15   # <= 15% = full marks
MAX_DD_CEILING = 0.50
TURNOVER_PENALISE_ABOVE = 0.20   # > 20% daily turnover = zero TC score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def safe_load(path: str, label: str):
    if not os.path.exists(path):
        return None, f"{label} not found: {path}"
    try:
        rows = load_csv(path)
        return (rows, None) if rows else (None, f"{label} is empty")
    except Exception as exc:
        return None, f"Failed to parse {label}: {exc}"


def parse_float(val, default=float("nan")):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def extract_portfolio_series(trades: list) -> dict:
    """
    Extract one portfolio_value per date (take last entry for the day).
    Returns dict {date_str: value}.
    """
    pv = {}
    for row in trades:
        d = row.get("date", "")
        v = parse_float(row.get("portfolio_value"))
        if d and not math.isnan(v):
            pv[d] = v
    return pv


def compute_metrics_from_series(values_dict: dict) -> dict:
    """Compute Sharpe, max drawdown, total return from daily portfolio values."""
    sorted_dates = sorted(values_dict)
    if len(sorted_dates) < 2:
        return {"sharpe": 0.0, "max_drawdown": 1.0, "total_return": 0.0,
                "calmar": 0.0}

    values = np.array([values_dict[d] for d in sorted_dates], dtype=np.float64)
    daily_rets = np.diff(values) / (values[:-1] + 1e-9)
    sharpe = float(daily_rets.mean() / (daily_rets.std() + 1e-9) * np.sqrt(252))
    total_ret = float((values[-1] - values[0]) / (values[0] + 1e-9))

    # Max drawdown
    peak = values[0]
    max_dd = 0.0
    for v in values:
        peak = max(peak, v)
        dd = (peak - v) / (peak + 1e-9)
        max_dd = max(max_dd, dd)

    n_years = max(len(sorted_dates) / 252, 1e-6)
    ann_ret = (1 + total_ret) ** (1 / n_years) - 1
    calmar = float(ann_ret / (max_dd + 1e-9))

    return {
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "total_return": total_ret,
        "calmar": calmar,
    }


def compute_turnover(trades: list) -> float:
    """
    Estimate daily portfolio turnover as mean absolute weight change.
    Groups trades by date, computes sum(|w_new - w_prev|) per day.
    """
    by_date = {}
    for row in trades:
        d = row.get("date", "")
        ticker = row.get("ticker", "")
        w = parse_float(row.get("weight"))
        if d and ticker and not math.isnan(w):
            by_date.setdefault(d, {})[ticker] = w

    sorted_dates = sorted(by_date)
    if len(sorted_dates) < 2:
        return 0.0

    turnovers = []
    prev_weights = by_date[sorted_dates[0]]
    for d in sorted_dates[1:]:
        curr_weights = by_date[d]
        all_tickers = set(prev_weights) | set(curr_weights)
        tv = sum(abs(curr_weights.get(t, 0) - prev_weights.get(t, 0))
                 for t in all_tickers)
        turnovers.append(tv)
        prev_weights = curr_weights

    return float(np.mean(turnovers)) if turnovers else 0.0


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_sharpe(sharpe: float) -> dict:
    """
    Full marks at Sharpe >= 2.0; zero at Sharpe <= 0.0.
    Penalty for negative Sharpe.
    """
    clipped = max(SHARPE_FLOOR, min(sharpe, SHARPE_TARGET * 1.5))
    ratio = max(0.0, (clipped - SHARPE_FLOOR) / (SHARPE_TARGET - SHARPE_FLOOR))
    ratio = min(1.0, ratio)
    raw_score = ratio * WEIGHTS["sharpe_ratio"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["sharpe_ratio"],
        "details": {"sharpe_ratio": round(sharpe, 4), "target": SHARPE_TARGET},
    }


def score_drawdown(max_dd: float) -> dict:
    """
    Full marks at max_drawdown <= 15%; zero at >= 50%.
    """
    if max_dd <= MAX_DD_TARGET:
        ratio = 1.0
    elif max_dd >= MAX_DD_CEILING:
        ratio = 0.0
    else:
        ratio = 1.0 - (max_dd - MAX_DD_TARGET) / (MAX_DD_CEILING - MAX_DD_TARGET)
    raw_score = ratio * WEIGHTS["drawdown_control"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["drawdown_control"],
        "details": {"max_drawdown": round(max_dd, 4), "target": MAX_DD_TARGET},
    }


def score_transaction_cost_awareness(turnover: float,
                                      total_return: float) -> dict:
    """
    Reward low turnover (cost efficiency) while still generating returns.
    Full marks: turnover < 5% daily AND return > 0.
    Penalty if turnover > 20% daily (churning).
    """
    if total_return <= 0:
        return {"score": 0, "max": WEIGHTS["transaction_cost_awareness"],
                "details": {"note": "negative total return — TC efficiency irrelevant"}}

    if turnover <= 0.05:
        ratio = 1.0
    elif turnover >= TURNOVER_PENALISE_ABOVE:
        ratio = 0.0
    else:
        ratio = 1.0 - (turnover - 0.05) / (TURNOVER_PENALISE_ABOVE - 0.05)

    raw_score = ratio * WEIGHTS["transaction_cost_awareness"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["transaction_cost_awareness"],
        "details": {
            "avg_daily_turnover": round(turnover, 4),
            "implied_annual_cost_%": round(turnover * 252 * 0.1, 2),
        },
    }


def score_strategy_documentation(submission_dir: str) -> dict:
    """
    Check for strategy documentation file.
    Automated proxy — full review requires human assessment.
    """
    candidates = ["strategy.pdf", "strategy.txt", "strategy.md",
                  "README.md", "report.pdf", "ablation_study.csv"]
    found = [f for f in candidates
             if os.path.exists(os.path.join(submission_dir, f))]
    ratio = min(1.0, len(found) / 2)  # full marks for 2+ docs
    raw_score = ratio * WEIGHTS["strategy_documentation"]
    return {
        "score": round(raw_score, 2),
        "max": WEIGHTS["strategy_documentation"],
        "details": {
            "docs_found": found,
            "note": "Full strategy score requires human review of content",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIDS-P4 AutoTrader Evaluator")
    parser.add_argument("--submission", required=True,
                        help="Path to trades.csv")
    parser.add_argument("--ground_truth", default=GROUND_TRUTH_PATH,
                        help="Path to benchmark CSV")
    parser.add_argument("--metrics_json", default=None,
                        help="Path to metrics.json (optional speedup)")
    args = parser.parse_args()

    errors = []
    breakdown = {}

    # --- Load pre-computed metrics if provided ---
    pre_metrics = None
    mj = args.metrics_json
    if mj and os.path.exists(mj):
        try:
            with open(mj) as f:
                pre_metrics = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to load metrics.json: {exc}")

    # --- Load trades ---
    sub_rows, err = safe_load(args.submission, "trades.csv")
    if err:
        errors.append(err)
        sub_rows = []

    submission_dir = os.path.dirname(os.path.abspath(args.submission))

    # --- Compute or load metrics ---
    if pre_metrics:
        sharpe = parse_float(pre_metrics.get("sharpe_ratio"), 0.0)
        max_dd = parse_float(pre_metrics.get("max_drawdown"), 1.0)
        total_ret = parse_float(pre_metrics.get("total_return"), 0.0)
        turnover = parse_float(pre_metrics.get("avg_turnover"), 0.5)
    elif sub_rows:
        pv_series = extract_portfolio_series(sub_rows)
        if len(pv_series) < 2:
            errors.append("Not enough trading days in submission to compute metrics.")
            sharpe, max_dd, total_ret = 0.0, 1.0, 0.0
            turnover = 1.0
        else:
            computed = compute_metrics_from_series(pv_series)
            sharpe = computed["sharpe"]
            max_dd = computed["max_drawdown"]
            total_ret = computed["total_return"]
            turnover = compute_turnover(sub_rows)
    else:
        sharpe, max_dd, total_ret, turnover = 0.0, 1.0, 0.0, 1.0

    # --- Score each dimension ---
    breakdown["sharpe_ratio"] = score_sharpe(sharpe)
    breakdown["drawdown_control"] = score_drawdown(max_dd)
    breakdown["transaction_cost_awareness"] = score_transaction_cost_awareness(
        turnover, total_ret)
    breakdown["strategy_documentation"] = score_strategy_documentation(
        submission_dir)

    total = sum(v["score"] for v in breakdown.values())
    result = {
        "total": round(total, 2),
        "breakdown": breakdown,
        "errors": errors,
        "computed_metrics": {
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 4),
            "total_return": round(total_ret, 4),
            "avg_daily_turnover": round(turnover, 4),
        },
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
