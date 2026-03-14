"""
MBA-P2: PricingGenius — Ride-Hailing Data Generator
Generates rides.csv, competitor_prices.csv, events.csv, weather.csv, README.md
"""

import numpy as np
import csv
import os
import math
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)

OUT_DIR = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P2"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
N_RIDES      = 1_000_000
CHUNK_SIZE   = 100_000
N_CITIES     = 50
ZONES        = list("ABCDEFGHIJ")          # zone_A … zone_J
START_DATE   = datetime(2024, 1, 1)
END_DATE     = datetime(2024, 6, 30, 23, 59, 59)
TOTAL_SECS   = int((END_DATE - START_DATE).total_seconds())

CITIES = [f"city_{i}" for i in range(1, N_CITIES + 1)]

HOUR_WEIGHTS = np.array([
    0.2, 0.1, 0.1, 0.1, 0.1,   # 0–4  (night)
    0.4,                         # 5
    0.8,                         # 6
    3.0, 3.0, 3.0,               # 7–9  (morning peak)
    1.0, 1.0,                    # 10–11
    1.0, 1.0,                    # 12–13
    1.0, 1.0,                    # 14–15
    1.0,                         # 16
    3.5, 3.5, 3.5, 3.5,         # 17–20 (evening peak)
    0.8, 0.5, 0.3,               # 21–23 (late night)
])
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

DAY_WEIGHTS = np.array([1.0, 1.0, 1.0, 1.0, 1.3, 1.5, 0.8])  # Mon–Sun


def random_timestamps(n, rng):
    """Vectorised weighted timestamp sampling."""
    # pick day-of-week
    dow = rng.choice(7, size=n, p=DAY_WEIGHTS / DAY_WEIGHTS.sum())
    # pick hour
    hour = rng.choice(24, size=n, p=HOUR_WEIGHTS)
    # pick a random date in [START_DATE, END_DATE] and force the correct dow
    # Simplification: pick offset in days (0..180) then adjust to nearest correct dow
    total_days = (END_DATE.date() - START_DATE.date()).days  # 181
    day_offset = rng.randint(0, total_days + 1, size=n)
    minute = rng.randint(0, 60, size=n)
    second = rng.randint(0, 60, size=n)
    # Build timestamps as seconds since epoch
    base_ts = np.array([
        int((START_DATE + timedelta(days=int(d), hours=int(h),
                                    minutes=int(mi), seconds=int(s))).timestamp())
        for d, h, mi, s in zip(day_offset, hour, minute, second)
    ])
    return base_ts


def is_peak_hour(hours_array):
    return ((hours_array >= 7) & (hours_array <= 9)) | ((hours_array >= 17) & (hours_array <= 20))


# ── Load events after they are generated (we generate events first) ───────────
def load_events():
    events = []
    path = os.path.join(OUT_DIR, "events.csv")
    if not os.path.exists(path):
        return events
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                "city": row["city"],
                "start": int(datetime.fromisoformat(row["start_datetime"]).timestamp()),
                "end":   int(datetime.fromisoformat(row["end_datetime"]).timestamp()),
            })
    return events


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  events.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_events():
    rng = np.random.default_rng(SEED)
    event_types = ["concert", "sports_game", "festival", "conference", "marathon"]
    event_names = {
        "concert":    ["Rock Night", "Jazz Fest", "Pop Extravaganza", "Symphony Gala"],
        "sports_game":["City Derby", "Championship Final", "League Match", "Playoffs Night"],
        "festival":   ["Street Food Fest", "Cultural Festival", "Night Market", "Beer Fest"],
        "conference": ["Tech Summit", "Business Forum", "Startup Expo", "Innovation Conf"],
        "marathon":   ["City Marathon", "Half Marathon", "Fun Run 5K", "Charity Run"],
    }
    attendance = {"concert": (5000, 40000), "sports_game": (8000, 60000),
                  "festival": (3000, 25000), "conference": (500, 8000),
                  "marathon": (1000, 12000)}

    rows = []
    n_events = 500
    event_id = 1
    total_days = (END_DATE.date() - START_DATE.date()).days

    for _ in range(n_events):
        city = CITIES[int(rng.integers(0, N_CITIES))]
        etype = event_types[int(rng.integers(0, len(event_types)))]
        enames = event_names[etype]
        ename = enames[int(rng.integers(0, len(enames)))]
        day_off = int(rng.integers(0, total_days + 1))
        start_h = int(rng.integers(10, 20))
        duration_h = int(rng.integers(2, 8))
        start_dt = START_DATE + timedelta(days=day_off, hours=start_h)
        end_dt   = start_dt + timedelta(hours=duration_h)
        lo, hi   = attendance[etype]
        att = int(rng.integers(lo, hi + 1))
        rows.append([event_id, city, ename, etype,
                     start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                     end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                     att])
        event_id += 1

    path = os.path.join(OUT_DIR, "events.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "city", "event_name", "event_type",
                    "start_datetime", "end_datetime", "expected_attendance"])
        w.writerows(rows)
    print(f"  events.csv → {len(rows)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  weather.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_weather():
    rng = np.random.default_rng(SEED + 1)
    conditions = ["clear", "cloudy", "rain", "heavy_rain", "fog", "storm"]
    cond_probs  = [0.45, 0.25, 0.15, 0.07, 0.05, 0.03]

    total_days = (END_DATE.date() - START_DATE.date()).days + 1
    rows = []

    for city in CITIES:
        city_lat_factor = rng.uniform(0.8, 1.2)          # temperature variation
        for day in range(total_days):
            cur_date = START_DATE + timedelta(days=day)
            month = cur_date.month
            base_temp = 10 + 5 * math.sin((month - 3) * math.pi / 6) * city_lat_factor
            for hour in range(24):
                temp = base_temp + rng.normal(0, 3) + 5 * math.sin((hour - 6) * math.pi / 12)
                precip = max(0.0, float(rng.exponential(0.5)))
                visibility = float(rng.uniform(2, 20))
                wind = float(rng.exponential(15))
                cond = conditions[int(rng.choice(len(conditions), p=cond_probs))]
                ts = (START_DATE + timedelta(days=day, hours=hour)).strftime("%Y-%m-%d %H:%M:%S")
                rows.append([ts, city, round(float(temp), 1), round(precip, 2),
                              round(visibility, 1), round(wind, 1), cond])

    path = os.path.join(OUT_DIR, "weather.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "city", "temperature_c", "precipitation_mm_hr",
                    "visibility_km", "wind_speed_kmph", "weather_condition"])
        w.writerows(rows)
    print(f"  weather.csv → {len(rows)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  rides.csv  (1 M rows, in chunks of 100 k)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_rides(events):
    """Build an event lookup: city -> list of (start_ts, end_ts)."""
    event_map = {}
    for ev in events:
        event_map.setdefault(ev["city"], []).append((ev["start"], ev["end"]))

    path = os.path.join(OUT_DIR, "rides.csv")
    header = ["ride_id", "timestamp", "city", "origin_zone", "dest_zone",
              "distance_km", "duration_min", "base_price_usd",
              "surge_multiplier", "final_price_usd",
              "driver_rating", "passenger_rating", "cancelled"]

    ride_id = 1
    written = 0

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)

        n_chunks = N_RIDES // CHUNK_SIZE
        for chunk_idx in range(n_chunks):
            rng = np.random.default_rng(SEED + chunk_idx)
            n = CHUNK_SIZE

            # ── timestamps ──
            dow      = rng.choice(7, size=n, p=DAY_WEIGHTS / DAY_WEIGHTS.sum())
            hour_arr = rng.choice(24, size=n, p=HOUR_WEIGHTS)
            total_days_range = (END_DATE.date() - START_DATE.date()).days
            day_off  = rng.integers(0, total_days_range + 1, size=n)
            minute   = rng.integers(0, 60, size=n)
            second   = rng.integers(0, 60, size=n)

            # ── cities & zones ──
            city_idx  = rng.integers(0, N_CITIES, size=n)
            o_zone_idx = rng.integers(0, 10, size=n)
            d_zone_idx = rng.integers(0, 10, size=n)

            # ── distance (log-normal, mean=8, std=5) ──
            mu_ln  = math.log(8**2 / math.sqrt(8**2 + 5**2))
            sig_ln = math.sqrt(math.log(1 + (5/8)**2))
            dist   = np.clip(rng.lognormal(mu_ln, sig_ln, n), 0.5, 50.0)

            # ── duration ──
            peak   = is_peak_hour(hour_arr)
            speed  = np.where(peak, 15.0, 25.0) + rng.normal(0, 3, n)
            speed  = np.clip(speed, 5.0, 60.0)
            dur    = (dist / speed) * 60.0  # minutes

            # ── base price ──
            base_p = 2.50 + 1.20 * dist + 0.30 * dur

            # ── surge multiplier ──
            surge  = np.ones(n)
            surge[peak] = rng.uniform(1.2, 2.0, peak.sum())
            # additional surge: 10 % of rides get extra spike
            extra_surge_mask = rng.random(n) < 0.10
            surge[extra_surge_mask] = np.maximum(surge[extra_surge_mask],
                                                  rng.uniform(1.5, 3.0, n)[extra_surge_mask])
            surge = np.round(surge, 2)

            final_p = np.round(base_p * surge, 2)

            # ── ratings ──
            drv_r = np.clip(rng.normal(4.5, 0.3, n), 1.0, 5.0)
            pax_r = np.clip(rng.normal(4.6, 0.4, n), 1.0, 5.0)

            # ── cancelled ──
            cancelled = (rng.random(n) < 0.05).astype(int)

            # ── write rows ──
            rows = []
            for i in range(n):
                d = int(day_off[i])
                h = int(hour_arr[i])
                mi = int(minute[i])
                sec = int(second[i])
                ts  = (START_DATE + timedelta(days=d, hours=h, minutes=mi, seconds=sec)
                       ).strftime("%Y-%m-%d %H:%M:%S")
                city = CITIES[int(city_idx[i])]
                oz   = f"zone_{ZONES[int(o_zone_idx[i])]}"
                dz   = f"zone_{ZONES[int(d_zone_idx[i])]}"
                rows.append([
                    ride_id + i, ts, city, oz, dz,
                    round(float(dist[i]), 2),
                    round(float(dur[i]),  1),
                    round(float(base_p[i]), 2),
                    float(surge[i]),
                    float(final_p[i]),
                    round(float(drv_r[i]), 1),
                    round(float(pax_r[i]), 1),
                    int(cancelled[i]),
                ])
            w.writerows(rows)
            ride_id += n
            written += n
            if (chunk_idx + 1) % 2 == 0:
                print(f"    rides: {written:,} / {N_RIDES:,}")

    print(f"  rides.csv → {written:,} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  competitor_prices.csv (30 % coverage = 300 k rows)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_competitor_prices():
    rng = np.random.default_rng(SEED + 99)
    competitors = ["RideX", "QuickCab"]
    n = 300_000

    path_rides = os.path.join(OUT_DIR, "rides.csv")
    # Sample 150k ride rows twice (once per competitor)
    # For speed: read ride file and sample ~150k rows
    sampled = []
    with open(path_rides, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for idx, row in enumerate(reader):
            if rng.random() < 0.155:   # ~15.5% chance ≈ 155k; we take 150k
                sampled.append(row)
            if len(sampled) >= 150_000:
                break

    path_out = os.path.join(OUT_DIR, "competitor_prices.csv")
    with open(path_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "city", "origin_zone", "dest_zone",
                    "competitor_name", "price_usd", "scraped_at"])
        for comp in competitors:
            for row in sampled:
                # row: ride_id, timestamp, city, origin_zone, dest_zone, ..., final_price_usd, ...
                ts        = row[1]
                city      = row[2]
                oz        = row[3]
                dz        = row[4]
                final_p   = float(row[9])
                factor    = rng.uniform(0.80, 1.20)
                comp_p    = round(final_p * factor, 2)
                offset_s  = int(rng.integers(-300, 301))
                scraped_ts = (datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") +
                               timedelta(seconds=offset_s)).strftime("%Y-%m-%d %H:%M:%S")
                w.writerow([ts, city, oz, dz, comp, comp_p, scraped_ts])

    # count
    with open(path_out, newline="", encoding="utf-8") as f:
        cnt = sum(1 for _ in f) - 1
    print(f"  competitor_prices.csv → {cnt:,} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  README.md
# ═══════════════════════════════════════════════════════════════════════════════
def write_readme():
    text = """# MBA-P2: PricingGenius — Ride-Hailing Dynamic Pricing Dataset

## Problem Statement
You are the Head of Pricing at GoRide, a ride-hailing company operating in 50 cities.
Design a dynamic pricing algorithm that maximises revenue while maintaining acceptable
cancellation rates and driver/passenger satisfaction.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| rides.csv | 1,000,000 | Historical ride records Jan–Jun 2024 |
| competitor_prices.csv | ~300,000 | Competitor price samples (RideX, QuickCab) |
| events.csv | 500 | City event calendar |
| weather.csv | 217,200 | Hourly weather per city |

## rides.csv Columns
- ride_id: Unique ride identifier
- timestamp: Ride request datetime (YYYY-MM-DD HH:MM:SS)
- city: city_1 … city_50
- origin_zone / dest_zone: zone_A … zone_J
- distance_km: Trip distance
- duration_min: Trip duration in minutes
- base_price_usd: Formula-based price (2.50 + 1.20*dist + 0.30*dur)
- surge_multiplier: 1.0–3.0 (higher during peaks/events)
- final_price_usd: base_price * surge_multiplier
- driver_rating / passenger_rating: 1–5 scale
- cancelled: 1 = cancelled, 0 = completed

## Key Challenges
1. Predict demand spikes (events, weather, time-of-day)
2. Balance surge pricing vs. cancellation risk
3. Competitor price benchmarking
4. Zone-level demand forecasting

## Suggested Approach
- Feature engineering: hour, dow, weather features, event proximity
- Model: XGBoost/LightGBM for demand prediction; RL for pricing policy
- Evaluation: Revenue lift vs. baseline, cancellation rate delta
"""
    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print("  README.md written")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating MBA-P2 files...")
    print("  [1/5] events.csv")
    generate_events()
    print("  [2/5] weather.csv")
    generate_weather()
    print("  [3/5] rides.csv")
    events = load_events()
    generate_rides(events)
    print("  [4/5] competitor_prices.csv")
    generate_competitor_prices()
    print("  [5/5] README.md")
    write_readme()
    print("MBA-P2 complete.")
