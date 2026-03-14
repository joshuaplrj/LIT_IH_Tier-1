# EventHorizon — Quick Start

## Objective
Design and implement a serverless event-driven backend for a flash-sale e-commerce platform that handles 10,000+ events per second with exactly-once inventory deduction, zero data loss, and sub-second P99 latency.

## Inputs
- `data/config.json` — Platform configuration: `{num_items, item_quantity, flash_sale_duration_sec, target_users}`
- `data/event_log.jsonl` — Newline-delimited JSON: pre-recorded event trace used as replay input for load testing. Each line: `{event_id, user_id, type, item_id, timestamp_ms}`
- `data/iac/` — Infrastructure-as-Code starter templates (Terraform stubs)

## Expected Output
Submission directory `submission/` containing:
- `submission/architecture.png` or `submission/architecture.md` — C4 model architecture diagram or description
- `submission/load_test_results.json` — k6/Locust output summarised into the schema below
- `submission/cost_estimate.json` — cost model for 5 million events
- `submission/iac/` — Terraform/Pulumi/CloudFormation files
- `submission/src/` — Source code for all functions/services

`load_test_results.json` schema:
```json
{
  "throughput_eps": 0,
  "p50_latency_ms": 0,
  "p95_latency_ms": 0,
  "p99_latency_ms": 0,
  "error_rate_pct": 0.0,
  "oversell_count": 0,
  "total_events_processed": 0
}
```

## Recommended First Steps
1. Implement an in-process event bus (Python asyncio.Queue) to simulate the serverless flow — Order -> Inventory -> Payment -> Fulfillment -> Notification — before worrying about cloud infrastructure.
2. Add idempotency: give every order a UUID, store processed UUIDs in a set (later Redis), and reject duplicate events; this is the exact-once foundation.
3. Write a simple load generator that replays `event_log.jsonl` at 10x speed and measures throughput + P99 latency using `statistics.quantiles`.

## Scoring Breakdown
| Metric            | Weight |
|-------------------|--------|
| Throughput (eps)  | 30%    |
| P99 latency       | 25%    |
| Correctness       | 25%    |
| Architecture      | 20%    |

## Common Pitfalls
- Overselling: without an atomic compare-and-swap on inventory, two simultaneous requests can both read "1 item left" and both succeed — use Redis DECR with a Lua script or a conditional DB write.
- Cold starts degrading P99: pre-warm your function instances or keep at least one instance alive; a single cold start can spike P99 by 500ms.
- Losing events on retry: make your handlers idempotent before enabling retries; otherwise a retry after partial processing double-charges or double-deducts.
