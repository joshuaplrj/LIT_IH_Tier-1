"""
IT-P1: SmartCity Digital Twin — Starter Skeleton
=================================================
Run:
    python starter.py --data_dir ./data --output_dir ./submission

Requirements (install before the hackathon):
    pip install fastapi uvicorn[standard] websockets aiohttp aiokafka asyncpg
    pip install pandas pyarrow geopandas osmnx networkx
    pip install scikit-learn torch prophet influxdb-client redis
    pip install deck-gl-jupyter  # optional, for notebook exploration
"""

import argparse
import asyncio
import json
import logging
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import geopandas as gpd
import networkx as nx

# FastAPI & WebSocket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

# Async HTTP
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = "./data"
DEFAULT_OUTPUT_DIR = "./submission"
SENSOR_STREAM_FILENAME = "sensor_stream.jsonl"
SENSORS_FILENAME = "sensors.json"
ROAD_NETWORK_FILENAME = "road_network.osm"
BUILDINGS_FILENAME = "buildings.geojson"
HISTORICAL_TRAFFIC_FILENAME = "historical_traffic.parquet"
HISTORICAL_ENERGY_FILENAME = "historical_energy.parquet"
INCIDENTS_FILENAME = "incidents.jsonl"

# ---------------------------------------------------------------------------
# Data loading utilities
# ---------------------------------------------------------------------------


def load_sensors(data_dir: Path) -> List[Dict]:
    """Load sensor definitions from sensors.json.

    Returns a list of dicts: [{id, lat, lon, type}, ...]
    """
    sensor_path = data_dir / SENSORS_FILENAME
    if not sensor_path.exists():
        log.warning("sensors.json not found — returning empty list")
        return []
    with open(sensor_path) as f:
        sensors = json.load(f)
    log.info("Loaded %d sensor definitions", len(sensors))
    return sensors


def load_road_network(data_dir: Path) -> nx.MultiDiGraph:
    """Parse road_network.osm into a NetworkX graph.

    TODO: Replace stub with osmnx.graph_from_xml() call.
    """
    # TODO: implement actual OSM parsing
    # import osmnx as ox
    # return ox.graph_from_xml(str(data_dir / ROAD_NETWORK_FILENAME))
    log.warning("Road network loading is a stub — returning empty graph")
    return nx.MultiDiGraph()


def load_buildings(data_dir: Path) -> gpd.GeoDataFrame:
    """Load building footprints from buildings.geojson."""
    buildings_path = data_dir / BUILDINGS_FILENAME
    if not buildings_path.exists():
        log.warning("buildings.geojson not found — returning empty GeoDataFrame")
        return gpd.GeoDataFrame()
    gdf = gpd.read_file(buildings_path)
    log.info("Loaded %d building footprints", len(gdf))
    return gdf


def load_historical_traffic(data_dir: Path) -> pd.DataFrame:
    """Load 1-year traffic parquet into a DataFrame."""
    path = data_dir / HISTORICAL_TRAFFIC_FILENAME
    if not path.exists():
        log.warning("historical_traffic.parquet not found")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    log.info("Loaded historical traffic: %s rows", len(df))
    return df


def load_historical_energy(data_dir: Path) -> pd.DataFrame:
    """Load 1-year energy parquet into a DataFrame."""
    path = data_dir / HISTORICAL_ENERGY_FILENAME
    if not path.exists():
        log.warning("historical_energy.parquet not found")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    log.info("Loaded historical energy: %s rows", len(df))
    return df


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------


class SensorIngestionPipeline:
    """Reads sensor events from a JSONL file (or a live stream) and
    buffers them for downstream consumers."""

    def __init__(self, stream_path: Path, buffer_size: int = 500):
        self.stream_path = stream_path
        self.buffer_size = buffer_size
        self._buffer: List[Dict] = []
        self._total_ingested = 0

    async def ingest(self) -> None:
        """Continuously read events from the stream.

        TODO: Replace file-based reading with an aiokafka consumer for
              production-level throughput (10,000 events/sec).
        """
        if not self.stream_path.exists():
            log.warning("Sensor stream file not found: %s", self.stream_path)
            return

        with open(self.stream_path) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    log.debug("Skipping malformed event: %s", exc)
                    continue

                await self._process_event(event)

                # Yield control every buffer_size events to stay non-blocking
                if self._total_ingested % self.buffer_size == 0:
                    await asyncio.sleep(0)

        log.info("Ingestion complete — total events: %d", self._total_ingested)

    async def _process_event(self, event: Dict) -> None:
        """Write a single event to the time-series store.

        TODO: Replace with actual DB write (asyncpg / TimescaleDB bulk insert).
        """
        self._buffer.append(event)
        self._total_ingested += 1
        # TODO: when len(self._buffer) >= self.buffer_size, flush to DB


# ---------------------------------------------------------------------------
# Prediction models
# ---------------------------------------------------------------------------


class TrafficPredictor:
    """30-minute-ahead traffic congestion predictor.

    TODO: Train an LSTM or Prophet model on historical_traffic DataFrame.
    """

    def __init__(self):
        self.model = None  # TODO: initialise model (e.g. torch LSTM)
        self.is_trained = False

    def train(self, df: pd.DataFrame) -> None:
        """Fit the model on historical traffic data.

        Args:
            df: DataFrame with columns [timestamp, sensor_id, value]

        TODO:
            1. Pivot df to wide format (rows=timestamps, cols=sensor_ids).
            2. Create sliding-window sequences (look-back = 30 min @ 30s intervals → 60 steps).
            3. Fit LSTM with hidden_size=64, 2 layers, dropout=0.1.
            4. Set self.is_trained = True after convergence.
        """
        log.warning("TrafficPredictor.train() is a stub — no model fitted")
        self.is_trained = False

    def predict(self, horizon_minutes: int = 30) -> Dict[str, float]:
        """Return predicted traffic values per sensor for the next horizon_minutes.

        Returns: {sensor_id: predicted_value}

        TODO: Run model forward pass on latest sensor readings.
        """
        return {}


class EnergyPredictor:
    """1-hour-ahead energy demand predictor.

    TODO: Train a gradient boosting or LSTM model on historical_energy DataFrame.
    """

    def __init__(self):
        self.model = None
        self.is_trained = False

    def train(self, df: pd.DataFrame) -> None:
        """Fit on historical energy data.

        TODO: Feature-engineer time-of-day, day-of-week, weather lag features.
              Use LightGBM or XGBoost for quick iteration.
        """
        log.warning("EnergyPredictor.train() is a stub")

    def predict(self, horizon_minutes: int = 60) -> Dict[str, float]:
        """Return predicted energy demand per zone for the next hour.

        Returns: {zone_id: predicted_kwh}
        """
        return {}


# ---------------------------------------------------------------------------
# Scenario simulation
# ---------------------------------------------------------------------------


def simulate_road_closure(graph: nx.MultiDiGraph, road_edge_id: Any) -> Dict:
    """What-if: remove road_edge_id and recompute shortest paths.

    TODO:
        1. Remove the edge from a copy of graph.
        2. Recompute betweenness centrality or shortest-path lengths.
        3. Return impact summary {affected_routes: int, avg_detour_km: float}.
    """
    return {"affected_routes": 0, "avg_detour_km": 0.0}


# ---------------------------------------------------------------------------
# Connection manager (WebSocket fan-out)
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages all active WebSocket connections and broadcasts delta updates."""

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        log.info("WS connected — total: %d", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        self.active.remove(ws)
        log.info("WS disconnected — total: %d", len(self.active))

    async def broadcast(self, payload: Dict) -> None:
        message = json.dumps(payload)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="SmartCity Digital Twin API")
manager = ConnectionManager()

# Global state (populated on startup)
_sensors: List[Dict] = []
_road_graph: nx.MultiDiGraph = nx.MultiDiGraph()
_buildings: gpd.GeoDataFrame = gpd.GeoDataFrame()
_traffic_predictor = TrafficPredictor()
_energy_predictor = EnergyPredictor()


@app.on_event("startup")
async def on_startup() -> None:
    """Load all datasets and kick off background ingestion."""
    data_dir = Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR))
    global _sensors, _road_graph, _buildings, _traffic_predictor, _energy_predictor

    _sensors = load_sensors(data_dir)
    _road_graph = load_road_network(data_dir)
    _buildings = load_buildings(data_dir)

    hist_traffic = load_historical_traffic(data_dir)
    hist_energy = load_historical_energy(data_dir)

    _traffic_predictor.train(hist_traffic)
    _energy_predictor.train(hist_energy)

    pipeline = SensorIngestionPipeline(data_dir / SENSOR_STREAM_FILENAME)
    asyncio.create_task(pipeline.ingest())

    # TODO: start periodic broadcast loop (every 5 s push delta to all WS clients)
    asyncio.create_task(_broadcast_loop())


async def _broadcast_loop() -> None:
    """Push live state updates to all connected WebSocket clients every 5 seconds.

    TODO: Query TimescaleDB for latest 1-minute rollups, build delta payload,
          call manager.broadcast(payload).
    """
    while True:
        await asyncio.sleep(5)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "traffic": _traffic_predictor.predict(30),
            "energy": _energy_predictor.predict(60),
            # TODO: add live sensor readings pulled from DB
        }
        await manager.broadcast(payload)


@app.get("/sensors")
async def get_sensors():
    """Return all sensor definitions."""
    return JSONResponse(content=_sensors)


@app.get("/graph")
async def get_graph():
    """Return road network as node-link JSON for the frontend."""
    # TODO: serialise _road_graph with nx.node_link_data()
    return JSONResponse(content={"nodes": [], "links": []})


@app.get("/predict/traffic")
async def predict_traffic(horizon: int = 30):
    """Return 30-min-ahead traffic predictions."""
    return JSONResponse(content=_traffic_predictor.predict(horizon))


@app.get("/predict/energy")
async def predict_energy(horizon: int = 60):
    """Return 1-hour-ahead energy predictions."""
    return JSONResponse(content=_energy_predictor.predict(horizon))


@app.post("/simulate/road_closure")
async def simulate_road_closure_endpoint(body: Dict):
    """Run a what-if road closure scenario."""
    edge_id = body.get("road_edge_id")
    result = simulate_road_closure(_road_graph, edge_id)
    return JSONResponse(content=result)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive; server pushes via broadcast_loop
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


async def run_benchmarks(api_base_url: str, num_clients: int = 50) -> Dict:
    """Connect num_clients WebSocket clients simultaneously and measure performance.

    TODO: Extend to measure ingestion_rate_eps via the /sensors endpoint under load.
    """
    latencies_ms: List[float] = []

    async def single_client(session_id: int):
        import websockets  # type: ignore

        uri = api_base_url.replace("http", "ws") + "/ws"
        try:
            async with websockets.connect(uri) as ws:
                t0 = time.monotonic()
                await ws.recv()  # wait for first broadcast
                latencies_ms.append((time.monotonic() - t0) * 1000)
        except Exception as exc:
            log.warning("Client %d error: %s", session_id, exc)

    tasks = [single_client(i) for i in range(num_clients)]
    await asyncio.gather(*tasks, return_exceptions=True)

    p99 = statistics.quantiles(latencies_ms, n=100)[98] if len(latencies_ms) >= 2 else 0.0

    benchmarks = {
        "ingestion_rate_eps": 0,   # TODO: measure from pipeline metrics
        "concurrent_users_tested": num_clients,
        "p99_latency_ms": round(p99, 2),
        "prediction_mae_traffic": 0,   # TODO: compute on held-out set
        "prediction_mae_energy": 0,    # TODO: compute on held-out set
        "visualization_fps": 0,        # TODO: measure in frontend
    }
    return benchmarks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_submission(output_dir: Path, benchmarks: Dict) -> None:
    """Write benchmark results and confirm submission layout."""
    output_dir.mkdir(parents=True, exist_ok=True)
    bench_path = output_dir / "benchmarks.json"
    with open(bench_path, "w") as f:
        json.dump(benchmarks, f, indent=2)
    log.info("Benchmarks written to %s", bench_path)


async def _async_main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    if args.mode == "serve":
        # Export DATA_DIR so on_startup can find it
        os.environ["DATA_DIR"] = str(data_dir)
        config = uvicorn.Config(app, host="0.0.0.0", port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    elif args.mode == "benchmark":
        url = f"http://localhost:{args.port}"
        benchmarks = await run_benchmarks(url, num_clients=50)
        build_submission(output_dir, benchmarks)

    elif args.mode == "build":
        # Standalone: load data, train models, write submission artefacts
        sensors = load_sensors(data_dir)
        hist_traffic = load_historical_traffic(data_dir)
        hist_energy = load_historical_energy(data_dir)

        tp = TrafficPredictor()
        ep = EnergyPredictor()
        tp.train(hist_traffic)
        ep.train(hist_energy)

        benchmarks = {
            "ingestion_rate_eps": 0,
            "concurrent_users_tested": 0,
            "p99_latency_ms": 0,
            "prediction_mae_traffic": 0,
            "prediction_mae_energy": 0,
            "visualization_fps": 0,
        }
        build_submission(output_dir, benchmarks)
        log.info("Submission scaffold written to %s", output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartCity Digital Twin — IT-P1")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Path to input data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Path to submission output directory")
    parser.add_argument("--mode", choices=["serve", "benchmark", "build"], default="build",
                        help="serve: start API server | benchmark: run load test | build: write submission artifacts")
    parser.add_argument("--port", type=int, default=8000, help="API server port (used in serve/benchmark modes)")
    args = parser.parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
