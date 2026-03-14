"""
generate_it_p1.py
Generates all prerequisite files for IT-P1: SmartCity Digital Twin
"""

import os
import json
import csv
import math
import random
import numpy as np
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IT-P1")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Coordinate helpers ──────────────────────────────────────────────────────
CENTER_LAT = 12.9716
CENTER_LON = 77.5946
M_PER_DEG_LAT = 111000.0
M_PER_DEG_LON = 97000.0   # at ~13° latitude

def xy_to_latlon(x_m, y_m):
    lat = CENTER_LAT + (y_m - 2500) / M_PER_DEG_LAT
    lon = CENTER_LON + (x_m - 2500) / M_PER_DEG_LON
    return round(lat, 7), round(lon, 7)

def coord(x_m, y_m):
    lat, lon = xy_to_latlon(x_m, y_m)
    return [lon, lat]   # GeoJSON uses [lon, lat]

# ─── 1. road_network.geojson ─────────────────────────────────────────────────
print("Generating road_network.geojson ...")

road_names_ns = [f"North-South Ave {i}" for i in range(1, 11)]
road_names_ew = [f"East-West Blvd {i}" for i in range(1, 11)]

features = []
road_id = 1

# 10 horizontal roads (constant y, vary x)
for i, y in enumerate(range(500, 5001, 500)):
    feat = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [coord(0, y), coord(5000, y)]
        },
        "properties": {
            "id": f"road_{road_id:03d}",
            "name": road_names_ew[i],
            "road_type": "primary",
            "speed_limit": 60,
            "lanes": 4
        }
    }
    features.append(feat)
    road_id += 1

# 10 vertical roads (constant x, vary y)
for i, x in enumerate(range(500, 5001, 500)):
    feat = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [coord(x, 0), coord(x, 5000)]
        },
        "properties": {
            "id": f"road_{road_id:03d}",
            "name": road_names_ns[i],
            "road_type": "primary",
            "speed_limit": 60,
            "lanes": 4
        }
    }
    features.append(feat)
    road_id += 1

# 30 secondary roads — diagonal/irregular
rng = np.random.default_rng(SEED)
secondary_types = ["secondary", "residential"]
speed_limits_sec = [30, 50]
grid_xs = list(range(500, 5001, 500))
grid_ys = list(range(500, 5001, 500))

for k in range(30):
    # pick two random grid intersection points (not the same)
    ix1, iy1 = rng.integers(0, 10), rng.integers(0, 10)
    ix2, iy2 = rng.integers(0, 10), rng.integers(0, 10)
    while ix1 == ix2 and iy1 == iy2:
        ix2, iy2 = rng.integers(0, 10), rng.integers(0, 10)
    x1, y1 = grid_xs[ix1], grid_ys[iy1]
    x2, y2 = grid_xs[ix2], grid_ys[iy2]
    # add a midpoint offset to make it slightly curved
    mx = (x1 + x2) / 2 + float(rng.integers(-300, 300))
    my = (y1 + y2) / 2 + float(rng.integers(-300, 300))
    mx = max(0, min(5000, mx))
    my = max(0, min(5000, my))
    rtype = secondary_types[k % 2]
    slimit = speed_limits_sec[k % 2]
    lanes = 2
    feat = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [coord(x1, y1), coord(mx, my), coord(x2, y2)]
        },
        "properties": {
            "id": f"road_{road_id:03d}",
            "name": f"Secondary Rd {k+1}",
            "road_type": rtype,
            "speed_limit": slimit,
            "lanes": lanes
        }
    }
    features.append(feat)
    road_id += 1

road_network = {"type": "FeatureCollection", "features": features}
with open(os.path.join(OUT_DIR, "road_network.geojson"), "w", encoding="utf-8") as f:
    json.dump(road_network, f, indent=2)
print(f"  -> {len(features)} road features written.")

# collect all road IDs for later use
all_road_ids = [feat["properties"]["id"] for feat in features]

# ─── 2. buildings.geojson ────────────────────────────────────────────────────
print("Generating buildings.geojson ...")

building_types = ["residential", "commercial", "office", "hospital"]
bld_features = []
rng2 = np.random.default_rng(SEED + 1)

for b in range(200):
    # place in a block — pick a cell between grid lines
    cell_x = int(rng2.integers(0, 9))   # 0..8
    cell_y = int(rng2.integers(0, 9))
    # block spans [cell_x*500+0 .. cell_x*500+500]
    bx_min = cell_x * 500 + 50
    bx_max = cell_x * 500 + 450
    by_min = cell_y * 500 + 50
    by_max = cell_y * 500 + 450
    # random building within block
    w = int(rng2.integers(30, 120))
    h_dim = int(rng2.integers(30, 120))
    bx = int(rng2.integers(bx_min, max(bx_min + 1, bx_max - w)))
    by = int(rng2.integers(by_min, max(by_min + 1, by_max - h_dim)))
    # polygon corners (clockwise)
    corners = [
        coord(bx, by),
        coord(bx + w, by),
        coord(bx + w, by + h_dim),
        coord(bx, by + h_dim),
        coord(bx, by)   # close ring
    ]
    floors = int(rng2.integers(1, 31))
    height = floors * 3 + int(rng2.integers(0, 5))
    btype = building_types[b % 4]
    bld_feat = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [corners]},
        "properties": {
            "id": f"bld_{b+1:04d}",
            "building_type": btype,
            "height": height,
            "floors": floors
        }
    }
    bld_features.append(bld_feat)

buildings = {"type": "FeatureCollection", "features": bld_features}
with open(os.path.join(OUT_DIR, "buildings.geojson"), "w", encoding="utf-8") as f:
    json.dump(buildings, f, indent=2)
print(f"  -> {len(bld_features)} building features written.")

# ─── 3. elevation.csv ────────────────────────────────────────────────────────
print("Generating elevation.csv ...")

xs = np.linspace(0, 5000, 100)
ys = np.linspace(0, 5000, 100)
noise = np.random.normal(0, 2, (100, 100))

with open(os.path.join(OUT_DIR, "elevation.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["x_m", "y_m", "elevation_m"])
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            elev = 900 + 20 * math.sin(x / 1000) + 15 * math.cos(y / 800) + noise[i, j]
            writer.writerow([round(x, 2), round(y, 2), round(elev, 3)])

print("  -> 10,000 elevation rows written.")

# ─── 4. sensors.csv ──────────────────────────────────────────────────────────
print("Generating sensors.csv ...")

sensor_types = ["speed", "volume", "occupancy"]
sensors = []
sensor_id = 1
rng3 = np.random.default_rng(SEED + 2)

# Main horizontal roads (y = 500..5000, x from 0 to 5000, every 500m)
for i, y in enumerate(range(500, 5001, 500)):
    road_ref = f"road_{i+1:03d}"
    for x in range(0, 5001, 500):
        stype = sensor_types[sensor_id % 3]
        lat, lon = xy_to_latlon(x, y)
        sensors.append({
            "sensor_id": f"S{sensor_id:04d}",
            "x_m": x, "y_m": y,
            "lat": lat, "lon": lon,
            "road_id": road_ref,
            "sensor_type": stype
        })
        sensor_id += 1

# Main vertical roads (x = 500..5000, y from 0 to 5000, every 500m)
for i, x in enumerate(range(500, 5001, 500)):
    road_ref = f"road_{i+11:03d}"
    for y in range(0, 5001, 500):
        stype = sensor_types[sensor_id % 3]
        lat, lon = xy_to_latlon(x, y)
        sensors.append({
            "sensor_id": f"S{sensor_id:04d}",
            "x_m": x, "y_m": y,
            "lat": lat, "lon": lon,
            "road_id": road_ref,
            "sensor_type": stype
        })
        sensor_id += 1

# Fill up to 1000 with random secondary sensors
sec_road_ids = all_road_ids[20:]  # secondary road IDs
while sensor_id <= 1000:
    rx = float(rng3.integers(0, 5001))
    ry = float(rng3.integers(0, 5001))
    lat, lon = xy_to_latlon(rx, ry)
    rid = sec_road_ids[sensor_id % len(sec_road_ids)]
    stype = sensor_types[sensor_id % 3]
    sensors.append({
        "sensor_id": f"S{sensor_id:04d}",
        "x_m": rx, "y_m": ry,
        "lat": lat, "lon": lon,
        "road_id": rid,
        "sensor_type": stype
    })
    sensor_id += 1

with open(os.path.join(OUT_DIR, "sensors.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["sensor_id", "x_m", "y_m", "lat", "lon", "road_id", "sensor_type"])
    writer.writeheader()
    writer.writerows(sensors[:1000])

print(f"  -> {min(len(sensors), 1000)} sensor rows written.")

# ─── 5. historical_traffic.csv ───────────────────────────────────────────────
print("Generating historical_traffic.csv  (876,000 rows — this may take a moment) ...")

START_DATE = datetime(2024, 1, 1, 0, 0, 0)
representative_sensors = [s["sensor_id"] for s in sensors[:100]]

rng4 = np.random.default_rng(SEED)

with open(os.path.join(OUT_DIR, "historical_traffic.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "sensor_id", "vehicle_count", "avg_speed_kmph", "occupancy_pct"])

    total_rows = 0
    for day in range(365):
        dt_day = START_DATE + timedelta(days=day)
        weekday = dt_day.weekday()   # 0=Mon, 6=Sun
        is_weekend = weekday >= 5
        for hour in range(24):
            dt = dt_day + timedelta(hours=hour)
            ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            # hour factor: peaks at 8am and 6pm
            if hour == 8 or hour == 9:
                hour_factor = 1.8 if not is_weekend else 1.2
            elif hour == 17 or hour == 18:
                hour_factor = 1.9 if not is_weekend else 1.3
            elif 23 <= hour or hour <= 5:
                hour_factor = 0.15
            else:
                hour_factor = 0.8 if not is_weekend else 0.6

            base_counts = rng4.integers(50, 300, size=100).astype(float)
            counts = (base_counts * hour_factor).astype(int)
            counts = np.clip(counts, 0, 600)

            base_speeds = rng4.uniform(20, 70, size=100)
            # speed inversely related to count
            speed_factor = 1.0 - 0.4 * (counts / 600.0)
            speeds = (base_speeds * speed_factor).clip(5, 80)

            occ = (counts / 600.0 * 100 + rng4.uniform(-5, 5, size=100)).clip(0, 100)

            for idx, sid in enumerate(representative_sensors):
                writer.writerow([
                    ts, sid,
                    int(counts[idx]),
                    round(float(speeds[idx]), 1),
                    round(float(occ[idx]), 1)
                ])
            total_rows += 100

print(f"  -> {total_rows:,} traffic rows written.")

# ─── 6. historical_energy.csv ────────────────────────────────────────────────
print("Generating historical_energy.csv  (87,600 rows) ...")

rng5 = np.random.default_rng(SEED + 3)

with open(os.path.join(OUT_DIR, "historical_energy.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "zone_id", "consumption_kwh", "grid_voltage_kv", "power_factor"])

    total_rows = 0
    for day in range(365):
        dt_day = START_DATE + timedelta(days=day)
        # summer months (Apr-Sep in India) get higher consumption
        month = dt_day.month
        season_factor = 1.3 if 4 <= month <= 9 else 1.0
        for hour in range(24):
            dt = dt_day + timedelta(hours=hour)
            ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            # daytime (8-20) higher, night lower
            if 8 <= hour <= 20:
                hour_factor = 1.4
            elif 6 <= hour < 8 or 20 < hour <= 22:
                hour_factor = 1.0
            else:
                hour_factor = 0.5
            for zone in range(1, 11):
                base = rng5.uniform(800, 2000)
                consumption = base * hour_factor * season_factor + rng5.normal(0, 50)
                consumption = max(100.0, consumption)
                voltage = rng5.uniform(10.8, 11.2)
                pf = rng5.uniform(0.85, 0.99)
                writer.writerow([ts, f"zone_{zone:02d}", round(consumption, 2), round(voltage, 4), round(pf, 4)])
            total_rows += 10

print(f"  -> {total_rows:,} energy rows written.")

# ─── 7. incidents.csv ────────────────────────────────────────────────────────
print("Generating incidents.csv  (~2000 rows) ...")

incident_types = ["traffic_accident", "road_closure", "emergency_response", "construction", "flooding"]
severities = ["low", "medium", "high", "critical"]
rng6 = np.random.default_rng(SEED + 4)

with open(os.path.join(OUT_DIR, "incidents.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["incident_id", "timestamp", "type", "x_m", "y_m", "lat", "lon",
                     "severity", "duration_minutes", "affected_road_id"])
    inc_id = 1
    for day in range(365):
        dt_day = START_DATE + timedelta(days=day)
        # 5-6 incidents per day
        n_incidents = int(rng6.integers(5, 7))
        for _ in range(n_incidents):
            hour = int(rng6.integers(0, 24))
            minute = int(rng6.integers(0, 60))
            dt = dt_day + timedelta(hours=hour, minutes=minute)
            ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            ix = float(rng6.uniform(0, 5000))
            iy = float(rng6.uniform(0, 5000))
            lat, lon = xy_to_latlon(ix, iy)
            itype = incident_types[int(rng6.integers(0, 5))]
            severity = severities[int(rng6.integers(0, 4))]
            duration = int(rng6.integers(10, 240))
            road_ref = all_road_ids[int(rng6.integers(0, len(all_road_ids)))]
            writer.writerow([
                f"INC_{inc_id:05d}", ts, itype,
                round(ix, 2), round(iy, 2), lat, lon,
                severity, duration, road_ref
            ])
            inc_id += 1

print(f"  -> {inc_id - 1} incident rows written.")

# ─── 8. README.md ────────────────────────────────────────────────────────────
readme = """# IT-P1: SmartCity Digital Twin — Dataset

## Overview
This dataset simulates a 5km x 5km downtown area (centered on Bangalore, India)
providing multi-modal city data for building a Digital Twin platform.

## Coordinate System
- Local: x in [0, 5000] m, y in [0, 5000] m
- Geographic: WGS84 lat/lon, center lat=12.9716, lon=77.5946
- 1° lat ≈ 111,000 m | 1° lon ≈ 97,000 m at this latitude

## Files

| File | Description | Rows/Features |
|------|-------------|---------------|
| road_network.geojson | Road network LineStrings | ~50 features |
| buildings.geojson | Building footprint Polygons | 200 features |
| elevation.csv | 100×100 elevation grid | 10,000 rows |
| sensors.csv | Traffic sensor positions | 1,000 rows |
| historical_traffic.csv | 1-year hourly traffic data | 876,000 rows |
| historical_energy.csv | 1-year hourly energy data | 87,600 rows |
| incidents.csv | 1-year incident log | ~2,000 rows |

## Schema

### road_network.geojson
- `id`: Road identifier (road_001 … road_050)
- `name`: Human-readable road name
- `road_type`: primary | secondary | residential
- `speed_limit`: 30 | 50 | 60 km/h
- `lanes`: 2 | 4

### buildings.geojson
- `id`: Building identifier (bld_0001 … bld_0200)
- `building_type`: residential | commercial | office | hospital
- `height`: Building height in metres
- `floors`: Number of floors

### elevation.csv
- `x_m`, `y_m`: Local coordinates (metres)
- `elevation_m`: Terrain elevation in metres (base ~900 m ASL)

### sensors.csv
- `sensor_id`: S0001 … S1000
- `x_m`, `y_m`, `lat`, `lon`: Position
- `road_id`: Associated road
- `sensor_type`: speed | volume | occupancy

### historical_traffic.csv
- `timestamp`: YYYY-MM-DD HH:MM:SS (hourly, 2024)
- `sensor_id`: One of 100 representative sensors
- `vehicle_count`: Vehicles per hour
- `avg_speed_kmph`: Average speed in km/h
- `occupancy_pct`: Lane occupancy percentage

### historical_energy.csv
- `timestamp`: YYYY-MM-DD HH:MM:SS (hourly, 2024)
- `zone_id`: zone_01 … zone_10
- `consumption_kwh`: Energy consumed in the hour
- `grid_voltage_kv`: Grid voltage in kV
- `power_factor`: Power factor (dimensionless, 0–1)

### incidents.csv
- `incident_id`: INC_00001 …
- `timestamp`, `type`, coordinates, `severity`, `duration_minutes`, `affected_road_id`
- Types: traffic_accident | road_closure | emergency_response | construction | flooding
- Severities: low | medium | high | critical

## Random Seed
All stochastic data generated with seed = 42.
"""

with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)

print("  -> README.md written.")
print("\nIT-P1 generation complete.")
