# SmartCity Digital Twin — Quick Start

## Objective
Build a real-time web platform that ingests 1000 IoT sensor streams, maintains a live digital twin of a 5 km x 5 km city grid, and renders it in 3D with predictive analytics for traffic, energy, and emergency response.

## Inputs
- `data/road_network.osm` — OpenStreetMap XML: road graph for the city grid
- `data/buildings.geojson` — GeoJSON: building footprints with height attributes
- `data/elevation.tif` — GeoTIFF: elevation raster (5 km x 5 km)
- `data/sensors.json` — JSON array of 1000 sensor definitions (id, lat, lon, type)
- `data/sensor_stream.jsonl` — Newline-delimited JSON: live sensor events (sensor_id, timestamp, value, type)
- `data/historical_traffic.parquet` — Parquet: 1 year of per-sensor traffic readings
- `data/historical_energy.parquet` — Parquet: 1 year of grid-zone energy readings
- `data/incidents.jsonl` — Newline-delimited JSON: historical emergency incidents

## Expected Output
Submission directory `submission/` containing:
- `submission/architecture.md` — written architecture document
- `submission/benchmarks.json` — performance benchmark results (see schema below)
- `submission/docker-compose.yml` — runnable compose file for all services
- `submission/app/` — full application source tree

`benchmarks.json` schema:
```json
{
  "ingestion_rate_eps": 0,
  "concurrent_users_tested": 0,
  "p99_latency_ms": 0,
  "prediction_mae_traffic": 0,
  "prediction_mae_energy": 0,
  "visualization_fps": 0
}
```

## Recommended First Steps
1. Stand up a time-series data pipeline: read `sensor_stream.jsonl` with an async consumer and write to a local TimescaleDB or InfluxDB instance.
2. Load `road_network.osm` with OSMnx into a NetworkX graph; expose a `/graph` REST endpoint so the frontend can fetch road topology.
3. Scaffold the 3D frontend using deck.gl or Three.js consuming the REST/WebSocket API, rendering buildings from `buildings.geojson` before adding live overlays.

## Scoring Breakdown
| Metric                  | Weight |
|-------------------------|--------|
| Data ingestion pipeline | 25%    |
| Simulation accuracy     | 30%    |
| 3D visualization        | 25%    |
| Scalability             | 20%    |

## Common Pitfalls
- Blocking the event loop: use async I/O (asyncio / aiohttp) for sensor ingestion; never call `time.sleep()` in a hot path.
- Skipping the time-series DB: storing raw events in SQLite will collapse under 10k events/sec; use a purpose-built TSDB from the start.
- Forgetting concurrent users: test with at least 50 WebSocket connections open simultaneously before finalizing the architecture.
