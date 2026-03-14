# EventHorizon — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
This problem is fundamentally about **distributed transactions without a distributed transaction coordinator**. The classic approach is the **Saga pattern**: each step in the event flow (Order, Inventory, Payment, Fulfillment, Notification) succeeds or publishes a compensating event to undo prior steps. Combine this with **idempotency keys** (a UUID per order that all steps check before processing) and you get exactly-once semantics without 2-phase commit. The load and latency challenges then become an engineering problem of queue depth, concurrency, and connection pooling — not architecture.

## Tier 2 — Technique Guidance (-10% score penalty)
- **Event bus**: Use **Redis Streams** (`XADD` / `XREADGROUP`) as a lightweight, persistent, ordered event log. Consumer groups give you competing-consumer parallelism and automatic re-delivery of unacked messages.
- **Exactly-once inventory**: Use a Redis Lua script combining `GET`, `DECRBY`, and `SET` atomically — Lua scripts execute as a single transaction on Redis. If stock reaches 0, return an error without decrementing.
- **Dead letter queue**: After 3 retries with exponential backoff (1s, 2s, 4s), `XADD` the failed event to a `dlq:orders` stream. A separate worker can inspect and replay these.
- **Serverless simulation**: Represent each microservice as an `async def handler(event)` coroutine running in a `asyncio.TaskGroup`. Throttle concurrency per handler with an `asyncio.Semaphore(max_concurrency)` to model Lambda concurrency limits.
- **Observability**: Use `opentelemetry-sdk` with a `ConsoleSpanExporter` during development. Each event should carry a `trace_id` field; propagate it through all handlers for end-to-end tracing.
- **Load testing**: Write a Locust `HttpUser` or a pure asyncio load generator that opens 1000 concurrent coroutines, each sending 5 events (the flash-sale user model), and collect latency with `time.monotonic()`.

## Tier 3 — Implementation Guidance (-15% score penalty)
1. **Event schema** (`models.py`): `@dataclass class Event`: fields `event_id: str` (UUID4), `user_id: str`, `type: Literal["order","inventory_check","payment","fulfillment","notification"]`, `item_id: str`, `timestamp_ms: int`, `trace_id: str`, `retry_count: int = 0`.
2. **Redis inventory service** (`services/inventory.py`): on startup `SET inventory:{item_id} {quantity}`. Handler: run Lua script `if redis.call("GET", KEYS[1]) > 0 then return redis.call("DECR", KEYS[1]) else return -1 end`. Return -1 means out-of-stock — publish `order_failed` event.
3. **Event router** (`router.py`): `async def route(event: Event)`: match `event.type` to the correct service handler coroutine. Wrap in a try/except; on failure increment `event.retry_count` and re-enqueue with `asyncio.sleep(2**retry_count)` backoff; after 3 failures push to DLQ.
4. **Idempotency store** (`store.py`): `processed_ids: set[str]` (in-memory for prototype; Redis `SADD` / `SISMEMBER` for production). In each handler, check `event.event_id` before processing and `SADD` after.
5. **Load generator** (`load_gen.py`): read `data/event_log.jsonl`, replay through `router.route()` using `asyncio.gather(*[route(e) for e in events])`. Measure: record `time.monotonic()` before/after each `route()` call; write sorted latencies to `load_test_results.json` using `statistics.quantiles`.
6. **Oversell checker**: after the load test, `GET inventory:{item_id}` from Redis; if value < 0, `oversell_count = abs(value)`.
7. **IaC** (`iac/main.tf`): define resources: `aws_lambda_function` for each service, `aws_sqs_queue` for the main bus and DLQ, `aws_dynamodb_table` for idempotency keys with TTL. Use `aws_lambda_event_source_mapping` to connect SQS to Lambda.
