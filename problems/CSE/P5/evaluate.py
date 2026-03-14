"""
Quantum-Safe Encrypted Database — Evaluation Script
CSE Problem 5

Usage:
    python evaluate.py --db_path db.json --client_key client_key.hex \
        --benchmarks benchmarks.json [--arch architecture.md]

Output (JSON to stdout):
    {
        "total": 0-100,
        "breakdown": {
            "functionality": {"score": X, "max": 40},
            "security_model":{"score": X, "max": 25},
            "performance":   {"score": X, "max": 20},
            "documentation": {"score": X, "max": 15}
        },
        "errors": []
    }
"""

import argparse
import json
import os
import random
import sys
import time
from typing import List, Optional, Tuple

GROUND_TRUTH_PATH = "ground_truth/CSE_P5_gt.csv"   # placeholder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(total, breakdown, errors):
    return {"total": round(float(total), 2), "breakdown": breakdown, "errors": errors}


def zero_result(reason: str):
    return result(
        0,
        {
            "functionality":  {"score": 0, "max": 40},
            "security_model": {"score": 0, "max": 25},
            "performance":    {"score": 0, "max": 20},
            "documentation":  {"score": 0, "max": 15},
        },
        [reason],
    )


# ---------------------------------------------------------------------------
# Metric: Functionality (40 pts)
# ---------------------------------------------------------------------------

def score_functionality(db_path: str, client_key_path: str) -> tuple:
    """
    Test the three query types against a ground-truth plaintext table.
    Requires the SSEClient and SSEServer from starter.py (or equivalent).

    Auto-loads the database, runs sample queries, and checks correctness.
    """
    errors = []

    if not os.path.isfile(db_path):
        errors.append(f"Database file not found: {db_path}")
        return 0.0, errors
    if not os.path.isfile(client_key_path):
        errors.append(f"Client key file not found: {client_key_path}")
        return 0.0, errors

    # Attempt dynamic import of the submission's SSEClient / SSEServer
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location("submission",
               os.path.join(os.path.dirname(db_path), "starter.py")
               if not os.path.isfile("server.py") else "server.py")
        # Fallback: try to import starter.py from cwd
        if not spec:
            raise ImportError("Could not locate submission module.")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        SSEClient = mod.SSEClient
        SSEServer = mod.SSEServer
    except Exception as e:
        errors.append(
            f"Could not import SSEClient/SSEServer: {e}. "
            "Functionality scored at 0 — ensure starter.py or server.py is in the same directory."
        )
        return 0.0, errors

    try:
        key = bytes.fromhex(open(client_key_path).read().strip())
        client = SSEClient(master_key=key)
        server = SSEServer()
        server.load(db_path)
    except Exception as e:
        errors.append(f"Failed to load database: {e}")
        return 0.0, errors

    score = 0.0
    MAX_FUNC = 40.0
    pts_per_test = MAX_FUNC / 10   # 10 test queries

    # --- Equality queries (4 tests = 16 pts) ---
    n_eq_passed = 0
    for _ in range(4):
        col = random.randint(0, 4)
        val = random.randint(0, SSEClient.VALUE_DOMAIN - 1)
        try:
            token = client.equality_token(col, val)
            results_enc = server.query_equality(token, client)
            # Verify: decrypt and check all returned records have record[col] == val
            verified = True
            for enc in results_enc:
                rec = client.decrypt_record(enc)
                if rec["data"][col] != val:
                    verified = False
                    errors.append(f"Equality query returned wrong record: col={col} val={val}")
                    break
            if verified:
                n_eq_passed += 1
        except Exception as e:
            errors.append(f"Equality query error: {e}")

    score += pts_per_test * n_eq_passed
    errors.append(f"Equality queries: {n_eq_passed}/4 correct.")

    # --- Range queries (3 tests = 12 pts) ---
    n_range_passed = 0
    for _ in range(3):
        col = random.randint(0, 4)
        lo  = random.randint(0, 1000)
        hi  = lo + random.randint(10, 500)
        try:
            tokens = client.range_tokens(col, lo, hi)
            results_enc = server.query_range(tokens, client)
            verified = True
            for enc in results_enc:
                rec = client.decrypt_record(enc)
                if not (lo <= rec["data"][col] <= hi):
                    verified = False
                    errors.append(f"Range query returned out-of-range record.")
                    break
            if verified:
                n_range_passed += 1
        except Exception as e:
            errors.append(f"Range query error: {e}")

    score += pts_per_test * n_range_passed
    errors.append(f"Range queries: {n_range_passed}/3 correct.")

    # --- COUNT queries (3 tests = 12 pts) ---
    n_count_passed = 0
    for _ in range(3):
        col = random.randint(0, 4)
        val = random.randint(0, SSEClient.VALUE_DOMAIN - 1)
        try:
            token = client.count_token(col, val)
            count = server.count_matching(token, client)
            # We cannot verify exact count without ground truth, but check type
            if isinstance(count, int) and count >= 0:
                n_count_passed += 1
            else:
                errors.append(f"COUNT returned non-integer: {count}")
        except Exception as e:
            errors.append(f"COUNT query error: {e}")

    score += pts_per_test * n_count_passed
    errors.append(f"COUNT queries: {n_count_passed}/3 correct.")

    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Security Model (25 pts)
# ---------------------------------------------------------------------------

def score_security_model(arch_path: Optional[str],
                          judge_score: float) -> tuple:
    """
    Auto-check: architecture doc mentions required security topics.
    Full grading requires judge review.
    """
    errors = []
    auto = 0.0
    required_topics = [
        "access pattern", "query pattern", "leakage", "post-quantum",
        "lattice", "kyber", "shake", "sha3", "honest-but-curious",
        "oram", "mitigation", "padding", "searchable"
    ]

    if not arch_path or not os.path.isfile(arch_path):
        errors.append("Architecture document not found. Security model auto-score = 0.")
    else:
        with open(arch_path) as f:
            content = f.read().lower()
        found = sum(1 for t in required_topics if t in content)
        auto = 10.0 * (found / len(required_topics))
        errors.append(
            f"Security model auto-score: {auto:.1f}/10 "
            f"({found}/{len(required_topics)} required topics mentioned)."
        )

    judge = float(max(0, min(15, judge_score)))
    total = min(auto + judge, 25.0)
    errors.append(f"Security model judge-assigned component: {judge}/15.")
    return round(total, 2), errors


# ---------------------------------------------------------------------------
# Metric: Performance (20 pts)
# ---------------------------------------------------------------------------

def score_performance(benchmarks_path: Optional[str],
                       db_path: str,
                       client_key_path: str) -> tuple:
    """
    Reads benchmarks.json if available; otherwise runs a quick benchmark.
    Target: point query p99 < 2000ms.
    """
    errors = []

    if benchmarks_path and os.path.isfile(benchmarks_path):
        try:
            with open(benchmarks_path) as f:
                bench = json.load(f)
            p99 = bench.get("p99_latency_ms", float("inf"))
            mean = bench.get("mean_latency_ms", float("inf"))
            target_met = bench.get("target_met", False)
        except Exception as e:
            errors.append(f"Could not parse benchmarks.json: {e}")
            p99 = float("inf"); mean = float("inf"); target_met = False
    else:
        errors.append(
            "benchmarks.json not found — running quick in-process benchmark."
        )
        # Try to run a quick benchmark using the submission module
        if os.path.isfile(db_path) and os.path.isfile(client_key_path):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "submission", "starter.py"
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                key = bytes.fromhex(open(client_key_path).read().strip())
                client = mod.SSEClient(master_key=key)
                server = mod.SSEServer(); server.load(db_path)
                latencies = []
                for _ in range(20):
                    col = random.randint(0, 4)
                    val = random.randint(0, mod.SSEClient.VALUE_DOMAIN - 1)
                    token = client.equality_token(col, val)
                    t0 = time.time()
                    server.query_equality(token, client)
                    latencies.append((time.time() - t0) * 1000)
                p99 = sorted(latencies)[int(0.99 * len(latencies))]
                mean = sum(latencies) / len(latencies)
                target_met = (p99 < 2000)
                errors.append(f"In-process benchmark: p99={p99:.1f}ms, mean={mean:.1f}ms.")
            except Exception as e:
                errors.append(f"Could not run in-process benchmark: {e}")
                p99 = float("inf"); mean = float("inf"); target_met = False
        else:
            p99 = float("inf"); mean = float("inf"); target_met = False

    if target_met:
        score = 20.0
    elif p99 < 5000:
        score = 10.0   # partial credit: slower than target but within 5s
        errors.append(f"Performance: p99={p99:.0f}ms exceeds 2000ms target (partial credit).")
    elif p99 < 10000:
        score = 5.0
        errors.append(f"Performance: p99={p99:.0f}ms — significantly above target.")
    else:
        score = 0.0
        errors.append(f"Performance: p99={p99:.0f}ms — far exceeds 2000ms target.")

    errors.append(f"p99 latency: {p99:.1f}ms | target: 2000ms | met: {target_met}")
    return round(score, 2), errors


# ---------------------------------------------------------------------------
# Metric: Documentation (15 pts)
# ---------------------------------------------------------------------------

def score_documentation(arch_path: Optional[str],
                         judge_score: float) -> tuple:
    """Architecture + system design document quality."""
    errors = []
    auto = 0.0

    if arch_path and os.path.isfile(arch_path):
        with open(arch_path) as f:
            content = f.read()
        lines = len([l for l in content.splitlines() if l.strip()])
        sections = ["architecture", "security", "performance", "crypto",
                    "query", "benchmark", "leakage"]
        found = sum(1 for s in sections if s.lower() in content.lower())
        if lines >= 200:
            auto += 3.0
        auto += 2.0 * (found / len(sections))
        errors.append(
            f"Documentation auto-score: {auto:.1f}/5 ({lines} lines, {found}/7 sections)."
        )
    else:
        errors.append("No architecture.md found.")

    judge = float(max(0, min(10, judge_score)))
    return round(min(auto + judge, 15.0), 2), errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a Quantum-Safe Encrypted Database submission."
    )
    parser.add_argument("--db_path",       type=str, default="db.json",
                        help="Path to the encrypted database file.")
    parser.add_argument("--client_key",    type=str, default="client_key.hex",
                        help="Path to the client master key (hex).")
    parser.add_argument("--benchmarks",    type=str, default="benchmarks.json",
                        help="Path to benchmarks.json.")
    parser.add_argument("--arch",          type=str, default="architecture.md",
                        help="Path to architecture document.")
    parser.add_argument("--security_score",type=float, default=0.0,
                        help="Judge-assigned security model score (0–15).")
    parser.add_argument("--doc_score",     type=float, default=0.0,
                        help="Judge-assigned documentation score (0–10).")
    args = parser.parse_args()

    errors = []
    breakdown = {
        "functionality":  {"score": 0.0, "max": 40},
        "security_model": {"score": 0.0, "max": 25},
        "performance":    {"score": 0.0, "max": 20},
        "documentation":  {"score": 0.0, "max": 15},
    }

    s, e = score_functionality(args.db_path, args.client_key)
    breakdown["functionality"]["score"] = s
    errors.extend(e)

    s, e = score_security_model(args.arch, args.security_score)
    breakdown["security_model"]["score"] = s
    errors.extend(e)

    s, e = score_performance(args.benchmarks, args.db_path, args.client_key)
    breakdown["performance"]["score"] = s
    errors.extend(e)

    s, e = score_documentation(args.arch, args.doc_score)
    breakdown["documentation"]["score"] = s
    errors.extend(e)

    total = sum(v["score"] for v in breakdown.values())
    print(json.dumps(result(total, breakdown, errors), indent=2))


if __name__ == "__main__":
    main()
