"""
IT-P3: EventHorizon — Serverless Event-Driven E-Commerce Starter Skeleton
==========================================================================
Run:
    python starter.py --data_dir ./data --output_dir ./submission

Requirements:
    pip install fastapi uvicorn[standard] aiohttp aiofiles redis asyncio
    pip install opentelemetry-sdk opentelemetry-api
    pip install locust statistics uuid
"""

import argparse
import asyncio
import json
import logging
import statistics
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = "./data"
DEFAULT_OUTPUT_DIR = "./submission"
CONFIG_FILENAME = "config.json"
EVENT_LOG_FILENAME = "event_log.jsonl"

MAX_RETRIES = 3
RETRY_BASE_DELAY_SEC = 1.0
DLQ_STREAM = "dlq:orders"

# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    ORDER = "order"
    INVENTORY_CHECK = "inventory_check"
    PAYMENT = "payment"
    FULFILLMENT = "fulfillment"
    NOTIFICATION = "notification"
    ORDER_FAILED = "order_failed"
    ORDER_COMPLETED = "order_completed"


@dataclass
class Event:
    event_id: str
    user_id: str
    type: str
    item_id: str
    timestamp_ms: int
    trace_id: str
    retry_count: int = 0
    payload: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict) -> "Event":
        return cls(
            event_id=d.get("event_id", str(uuid.uuid4())),
            user_id=d.get("user_id", "unknown"),
            type=d.get("type", EventType.ORDER),
            item_id=d.get("item_id", "item_0"),
            timestamp_ms=d.get("timestamp_ms", int(time.time() * 1000)),
            trace_id=d.get("trace_id", str(uuid.uuid4())),
            retry_count=d.get("retry_count", 0),
            payload=d.get("payload", {}),
        )


# ---------------------------------------------------------------------------
# In-memory inventory store (replace with Redis for production)
# ---------------------------------------------------------------------------


class InventoryStore:
    """Simulates atomic inventory operations (Redis DECR equivalent)."""

    def __init__(self, items: Dict[str, int]):
        self._stock: Dict[str, int] = dict(items)
        self._lock = asyncio.Lock()

    async def decrement(self, item_id: str) -> int:
        """Atomically decrement stock. Returns new stock level, or -1 if out of stock.

        TODO: Replace with a Redis Lua script for distributed deployments:
            local stock = redis.call("GET", KEYS[1])
            if tonumber(stock) > 0 then return redis.call("DECR", KEYS[1])
            else return -1 end
        """
        async with self._lock:
            stock = self._stock.get(item_id, 0)
            if stock <= 0:
                return -1
            self._stock[item_id] = stock - 1
            return stock - 1

    def get_stock(self, item_id: str) -> int:
        return self._stock.get(item_id, 0)

    def oversell_count(self) -> int:
        """Return the magnitude of any negative stock (indicates oversell)."""
        return sum(abs(v) for v in self._stock.values() if v < 0)


# ---------------------------------------------------------------------------
# Idempotency store
# ---------------------------------------------------------------------------


class IdempotencyStore:
    """Prevents duplicate processing of events by tracking processed event IDs.

    TODO: Replace in-memory set with Redis SADD / SISMEMBER for distributed deployments.
    """

    def __init__(self):
        self._seen: Set[str] = set()
        self._lock = asyncio.Lock()

    async def check_and_mark(self, event_id: str) -> bool:
        """Returns True if this event_id is new (safe to process), False if duplicate."""
        async with self._lock:
            if event_id in self._seen:
                return False
            self._seen.add(event_id)
            return True


# ---------------------------------------------------------------------------
# Dead letter queue
# ---------------------------------------------------------------------------


class DeadLetterQueue:
    """Captures events that exhausted all retries."""

    def __init__(self):
        self._queue: List[Dict] = []

    async def push(self, event: Event, error: str) -> None:
        entry = {**asdict(event), "dlq_error": error, "dlq_ts_ms": int(time.time() * 1000)}
        self._queue.append(entry)
        log.warning("DLQ: event_id=%s error=%s", event.event_id, error)

    def dump(self) -> List[Dict]:
        return list(self._queue)


# ---------------------------------------------------------------------------
# Service handlers
# ---------------------------------------------------------------------------


async def handle_order(event: Event, inventory: InventoryStore) -> Optional[Event]:
    """Validate order and pass to inventory check.

    TODO: Validate user session token, check item exists in catalogue.
    """
    # Simulate validation latency
    await asyncio.sleep(0.001)
    return Event(
        event_id=str(uuid.uuid4()),
        user_id=event.user_id,
        type=EventType.INVENTORY_CHECK,
        item_id=event.item_id,
        timestamp_ms=int(time.time() * 1000),
        trace_id=event.trace_id,
        payload={"original_order_id": event.event_id},
    )


async def handle_inventory_check(event: Event, inventory: InventoryStore) -> Optional[Event]:
    """Attempt atomic inventory deduction.

    TODO: Connect to real Redis with Lua script for distributed safety.
    """
    new_stock = await inventory.decrement(event.item_id)
    if new_stock < 0:
        log.debug("Out of stock for item %s (trace=%s)", event.item_id, event.trace_id)
        return Event(
            event_id=str(uuid.uuid4()),
            user_id=event.user_id,
            type=EventType.ORDER_FAILED,
            item_id=event.item_id,
            timestamp_ms=int(time.time() * 1000),
            trace_id=event.trace_id,
            payload={"reason": "out_of_stock"},
        )
    return Event(
        event_id=str(uuid.uuid4()),
        user_id=event.user_id,
        type=EventType.PAYMENT,
        item_id=event.item_id,
        timestamp_ms=int(time.time() * 1000),
        trace_id=event.trace_id,
        payload={"stock_remaining": new_stock},
    )


async def handle_payment(event: Event, inventory: InventoryStore) -> Optional[Event]:
    """Process payment (stub — always succeeds).

    TODO: Integrate payment gateway SDK; handle declined cards by compensating
          the inventory decrement (increment stock back).
    """
    await asyncio.sleep(0.002)  # Simulate payment API latency
    return Event(
        event_id=str(uuid.uuid4()),
        user_id=event.user_id,
        type=EventType.FULFILLMENT,
        item_id=event.item_id,
        timestamp_ms=int(time.time() * 1000),
        trace_id=event.trace_id,
    )


async def handle_fulfillment(event: Event, inventory: InventoryStore) -> Optional[Event]:
    """Create fulfillment record (stub).

    TODO: Write to orders DB, trigger warehouse system API.
    """
    await asyncio.sleep(0.001)
    return Event(
        event_id=str(uuid.uuid4()),
        user_id=event.user_id,
        type=EventType.NOTIFICATION,
        item_id=event.item_id,
        timestamp_ms=int(time.time() * 1000),
        trace_id=event.trace_id,
    )


async def handle_notification(event: Event, inventory: InventoryStore) -> Optional[Event]:
    """Send confirmation notification (stub).

    TODO: Call email/SMS API with order confirmation details.
    """
    await asyncio.sleep(0.0005)
    return None  # Terminal step — pipeline complete


# ---------------------------------------------------------------------------
# Event router
# ---------------------------------------------------------------------------

HANDLER_MAP: Dict[str, Callable] = {
    EventType.ORDER: handle_order,
    EventType.INVENTORY_CHECK: handle_inventory_check,
    EventType.PAYMENT: handle_payment,
    EventType.FULFILLMENT: handle_fulfillment,
    EventType.NOTIFICATION: handle_notification,
}


class EventRouter:
    """Routes events through the pipeline with retry logic and DLQ."""

    def __init__(self, inventory: InventoryStore, idempotency: IdempotencyStore, dlq: DeadLetterQueue):
        self.inventory = inventory
        self.idempotency = idempotency
        self.dlq = dlq

    async def route(self, event: Event) -> float:
        """Process one event through the full pipeline.

        Returns the end-to-end latency in milliseconds.
        """
        t_start = time.monotonic()

        is_new = await self.idempotency.check_and_mark(event.event_id)
        if not is_new:
            log.debug("Duplicate event %s — skipped", event.event_id)
            return (time.monotonic() - t_start) * 1000

        current_event: Optional[Event] = event
        while current_event is not None:
            handler = HANDLER_MAP.get(current_event.type)
            if handler is None:
                # Terminal or unhandled event type
                break

            success = False
            for attempt in range(MAX_RETRIES):
                try:
                    next_event = await handler(current_event, self.inventory)
                    success = True
                    current_event = next_event
                    break
                except Exception as exc:
                    delay = RETRY_BASE_DELAY_SEC * (2 ** attempt)
                    log.debug("Handler %s failed (attempt %d): %s — retrying in %.1fs",
                              current_event.type, attempt + 1, exc, delay)
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(delay)
                    else:
                        await self.dlq.push(current_event, str(exc))
                        current_event = None

            if not success:
                break

        return (time.monotonic() - t_start) * 1000


# ---------------------------------------------------------------------------
# Load generator
# ---------------------------------------------------------------------------


def load_events(data_dir: Path) -> List[Event]:
    """Parse event_log.jsonl into a list of Event objects."""
    path = data_dir / EVENT_LOG_FILENAME
    events = []
    if not path.exists():
        log.warning("event_log.jsonl not found — generating synthetic events")
        for i in range(1000):
            events.append(Event(
                event_id=str(uuid.uuid4()),
                user_id=f"user_{i}",
                type=EventType.ORDER,
                item_id="item_0",
                timestamp_ms=int(time.time() * 1000) + i,
                trace_id=str(uuid.uuid4()),
            ))
        return events

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(Event.from_dict(json.loads(line)))
                except Exception as exc:
                    log.debug("Skipping malformed event: %s", exc)
    log.info("Loaded %d events from event_log.jsonl", len(events))
    return events


async def run_load_test(
    events: List[Event],
    inventory: InventoryStore,
    max_concurrency: int = 500,
) -> Dict:
    """Run all events concurrently (up to max_concurrency at a time) and collect metrics."""
    idempotency = IdempotencyStore()
    dlq = DeadLetterQueue()
    router = EventRouter(inventory, idempotency, dlq)

    semaphore = asyncio.Semaphore(max_concurrency)
    latencies_ms: List[float] = []
    errors = 0

    t_wall_start = time.monotonic()

    async def bounded_route(event: Event) -> None:
        nonlocal errors
        async with semaphore:
            try:
                lat = await router.route(event)
                latencies_ms.append(lat)
            except Exception:
                errors += 1

    await asyncio.gather(*[bounded_route(e) for e in events])
    wall_time = time.monotonic() - t_wall_start

    latencies_ms.sort()
    n = len(latencies_ms)
    throughput = n / wall_time if wall_time > 0 else 0

    def percentile(p: int) -> float:
        if not latencies_ms:
            return 0.0
        idx = max(0, int(n * p / 100) - 1)
        return round(latencies_ms[idx], 2)

    oversell = inventory.oversell_count()

    results = {
        "throughput_eps": round(throughput, 2),
        "p50_latency_ms": percentile(50),
        "p95_latency_ms": percentile(95),
        "p99_latency_ms": percentile(99),
        "error_rate_pct": round(errors / n * 100, 2) if n > 0 else 0.0,
        "oversell_count": oversell,
        "total_events_processed": n,
    }

    if oversell > 0:
        log.error("OVERSELL DETECTED: %d items over-sold!", oversell)
    else:
        log.info("Zero oversell confirmed.")

    return results


# ---------------------------------------------------------------------------
# Cost estimator
# ---------------------------------------------------------------------------


def estimate_cost(total_events: int = 5_000_000) -> Dict:
    """Rough AWS Lambda + SQS cost estimate for total_events.

    TODO: Replace with real pricing from AWS calculator for your chosen region.
    """
    # AWS Lambda: $0.20 per 1M requests + $0.0000166667 per GB-second
    # Assume avg 100ms execution, 256MB memory per invocation
    lambda_requests_cost = (total_events / 1_000_000) * 0.20
    lambda_duration_cost = total_events * (0.1) * (256 / 1024) * 0.0000166667

    # AWS SQS: $0.40 per 1M requests (standard queue)
    # Each event touches queue ~3 times (enqueue, read, delete)
    sqs_cost = (total_events * 3 / 1_000_000) * 0.40

    # Redis (ElastiCache t3.small): ~$0.034/hr; assume 2-hour flash sale window
    redis_cost = 0.034 * 2

    total = lambda_requests_cost + lambda_duration_cost + sqs_cost + redis_cost
    return {
        "total_events": total_events,
        "lambda_requests_usd": round(lambda_requests_cost, 4),
        "lambda_duration_usd": round(lambda_duration_cost, 4),
        "sqs_usd": round(sqs_cost, 4),
        "redis_usd": round(redis_cost, 4),
        "total_usd": round(total, 4),
        "note": "Approximate AWS pricing; verify with AWS Pricing Calculator",
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def load_config(data_dir: Path) -> Dict:
    config_path = data_dir / CONFIG_FILENAME
    defaults = {"num_items": 1, "item_quantity": 1000, "flash_sale_duration_sec": 600, "target_users": 1_000_000}
    if not config_path.exists():
        log.warning("config.json not found — using defaults")
        return defaults
    with open(config_path) as f:
        return {**defaults, **json.load(f)}


async def async_main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(data_dir)
    log.info("Config: %s", config)

    # Initialise inventory
    items = {f"item_{i}": config["item_quantity"] for i in range(config["num_items"])}
    inventory = InventoryStore(items)

    # Load events
    events = load_events(data_dir)

    # Run load test
    log.info("Starting load test with %d events, concurrency=%d", len(events), args.concurrency)
    results = await run_load_test(events, inventory, max_concurrency=args.concurrency)
    log.info("Load test results: %s", results)

    # Write results
    results_path = output_dir / "load_test_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Load test results written to %s", results_path)

    # Cost estimate
    cost = estimate_cost(total_events=5_000_000)
    cost_path = output_dir / "cost_estimate.json"
    with open(cost_path, "w") as f:
        json.dump(cost, f, indent=2)
    log.info("Cost estimate written to %s", cost_path)

    log.info("Throughput: %.1f eps | P99: %.1f ms | Oversell: %d",
             results["throughput_eps"], results["p99_latency_ms"], results["oversell_count"])


def main() -> None:
    parser = argparse.ArgumentParser(description="EventHorizon Serverless E-Commerce — IT-P3")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Path to input data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Path to submission output directory")
    parser.add_argument("--concurrency", type=int, default=500, help="Max concurrent event handlers")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
