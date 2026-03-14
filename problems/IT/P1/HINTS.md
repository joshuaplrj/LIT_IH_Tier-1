# SmartCity Digital Twin — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
This problem is a classic **real-time streaming + spatial computing** challenge. Split your thinking into three independent planes: (1) the data plane — how sensor events flow from source to storage, (2) the compute plane — how stored data feeds predictive models, and (3) the presentation plane — how computed state reaches the browser in 3D. Nail the interface contracts between these planes first, then build each independently.

## Tier 2 — Technique Guidance (-10% score penalty)
- **Ingestion**: Use Apache Kafka (or a lightweight substitute like Redpanda) as the event broker between sensor feed and the DB writer. Kafka's consumer groups let you scale writers horizontally without duplicating work.
- **Time-series storage**: TimescaleDB (Postgres extension) gives you SQL familiarity plus hypertable compression. Write a continuous aggregate view for 1-minute rollups — this is what the prediction model should read, not raw rows.
- **Traffic prediction**: A simple LSTM trained on `historical_traffic.parquet` with a 30-minute look-back window achieves good MAE and trains fast. Consider Facebook Prophet as a faster-to-iterate baseline.
- **3D visualization**: deck.gl's `HexagonLayer` for traffic density heatmap and `ScenegraphLayer` for 3D buildings keeps the frontend under 200 lines of JS while delivering WebGL performance.
- **Scalability**: Use Redis pub/sub to fan out state updates to all 50+ WebSocket connections rather than querying the DB once per client per tick.

## Tier 3 — Implementation Guidance (-15% score penalty)
1. **Sensor ingestor** (`ingestor/main.py`): open `sensor_stream.jsonl`, parse each line as JSON, produce to Kafka topic `sensor-raw`. Use `aiokafka.AIOKafkaProducer` so you never block. Batch 500 messages per `send_batch()` call for throughput.
2. **DB writer** (`writer/main.py`): consume `sensor-raw` with `AIOKafkaConsumer`, bulk-insert into TimescaleDB using `asyncpg.executemany()`. Create a hypertable on `(sensor_id, ts)`.
3. **Prediction service** (`predictor/main.py`): on startup load `historical_traffic.parquet` with pandas, fit one LSTM per sensor cluster (k-means, 20 clusters). Expose `GET /predict/traffic?t=<iso>` that returns a JSON array of (sensor_id, predicted_value).
4. **API gateway** (`api/main.py`): FastAPI app, WebSocket endpoint `/ws` that pushes delta updates every 5 seconds by reading the latest TimescaleDB rollup. REST endpoints `/sensors`, `/graph`, `/predict`.
5. **Frontend** (`frontend/index.html`): deck.gl `DeckGL` component, layers: `GeoJsonLayer` for buildings, `HexagonLayer` for live traffic, `ScatterplotLayer` for incidents. Connect to `/ws` and call `deck.setProps({layers: updatedLayers})` on each message.
6. **Docker Compose**: services `zookeeper`, `kafka`, `timescaledb`, `redis`, `ingestor`, `writer`, `predictor`, `api`, `frontend`. Use health-checks so dependent services wait for their upstreams.
7. **Benchmark harness** (`benchmark.py`): spin up 50 `websockets.connect()` coroutines concurrently, measure message receipt rate, record P99 latency with `statistics.quantiles()`, write `submission/benchmarks.json`.
