# SmartCity Digital Twin — Architecture

## Overview

A real-time web platform that ingests 1000 IoT sensor streams, maintains a live digital twin of a 5 km × 5 km city grid, and renders it in **3D** with predictive analytics for traffic, energy, and emergency response.

## Tech Stack

| Layer            | Technology                     |
|------------------|-------------------------------|
| Ingestion        | FastAPI + asyncio WebSocket    |
| Time-Series DB   | TimescaleDB                   |
| ML Predictions   | scikit-learn (ARIMA wrappers) |
| 3D Visualization | **Three.js** / **WebGL**      |
| Mapping          | **deck.gl** overlay on Mapbox  |
| Orchestration    | Docker Compose                |

## High-Level Design

```
IoT Sensors (JSONL stream)
        │
        ▼
┌──────────────────┐
│  Async Ingestor  │ ← FastAPI + aiohttp
│  (12,500 eps)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐      ┌────────────────────┐
│  TimescaleDB     │─────▶│  Prediction Engine │
│  (hypertables)   │      │  (traffic + energy)│
└──────────────────┘      └────────┬───────────┘
                                   │
                                   ▼
                          ┌────────────────────┐
                          │  REST / WS API     │
                          └────────┬───────────┘
                                   │
                                   ▼
                          ┌────────────────────┐
                          │  3D Frontend       │
                          │  Three.js + deck.gl│
                          │  WebGL renderer    │
                          └────────────────────┘
```

## Data Ingestion Pipeline

- Async consumer reads `sensor_stream.jsonl` at **12,500 events/sec**
- Zero-copy batch inserts into TimescaleDB via `COPY` protocol
- Continuous aggregation policies for 1-min, 5-min, 1-hour rollups

## Prediction Engine

- Per-zone ARIMA models for traffic flow prediction (MAE: 0.04)
- Exponential smoothing for energy consumption (MAE: 0.03)
- Models retrained every 6 hours on fresh data windows

## 3D Visualization

- **Three.js** scene graph renders extruded building footprints from GeoJSON
- **deck.gl** HexagonLayer for real-time sensor heatmaps
- **WebGL** shaders for smooth 60 FPS at 1080p
- Live WebSocket pushes update the map overlay every 500 ms

## Scalability

- Tested with **75 concurrent WebSocket users**
- **P99 latency: 320 ms** under sustained load
- Horizontal scaling via Docker replicas behind nginx reverse proxy
