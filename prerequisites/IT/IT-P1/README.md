# IT-P1: SmartCity Digital Twin — Dataset

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
