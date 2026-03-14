"""
MBA-P3: SupplyZen — Supply Chain Data Generator
Generates supply_chain.csv, supplier_risk_matrix.csv,
disruption_events.csv, inventory_levels.csv, README.md
"""

import numpy as np
import csv
import os
import json
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)
rng = np.random.default_rng(SEED)

OUT_DIR = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\MBA\MBA-P3"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
N_COMPONENTS = 2000
N_SUPPLIERS  = 500

COMP_TYPES = ["semiconductor", "display", "battery_cell", "connector", "pcb",
              "housing", "camera_module", "sensor", "cable", "ic_chip"]

COUNTRY_POOL = (
    ["China"]       * 40 +
    ["Taiwan"]      * 20 +
    ["South Korea"] * 10 +
    ["Japan"]       * 10 +
    ["USA"]         *  8 +
    ["Germany"]     *  5 +
    ["Vietnam"]     *  2 +
    ["Malaysia"]    *  2 +
    ["Mexico"]      *  2 +
    ["India"]       *  1
)  # total = 100 items

COMP_NAME_PARTS = {
    "semiconductor": ["NAND Flash", "DRAM Module", "MCU Unit", "FPGA Chip", "Power IC"],
    "display":       ["LCD Panel", "OLED Display", "Touch Screen", "LED Array"],
    "battery_cell":  ["Li-Ion Cell", "LiPo Pack", "Battery Module", "Power Cell"],
    "connector":     ["USB-C Port", "HDMI Connector", "FPC Connector", "Board-to-Board"],
    "pcb":           ["Mainboard PCB", "Sub-PCB", "Flex PCB", "Rigid-Flex PCB"],
    "housing":       ["Aluminum Chassis", "Plastic Shell", "Back Cover", "Frame"],
    "camera_module": ["Main Camera", "Front Camera", "Telephoto Module", "Wide-Angle"],
    "sensor":        ["Accelerometer", "Gyroscope", "Proximity Sensor", "Light Sensor"],
    "cable":         ["RF Cable", "Data Cable", "Coaxial Cable", "Power Wire"],
    "ic_chip":       ["Wi-Fi IC", "Bluetooth IC", "NFC Chip", "Audio Codec"],
}

COST_RANGES = {
    "semiconductor": (1.0, 80.0),
    "display":       (5.0, 120.0),
    "battery_cell":  (3.0, 90.0),
    "connector":     (0.05, 3.0),
    "pcb":           (1.0, 25.0),
    "housing":       (0.5, 15.0),
    "camera_module": (10.0, 150.0),
    "sensor":        (0.5, 20.0),
    "cable":         (0.01, 2.0),
    "ic_chip":       (0.1, 10.0),
}

LEAD_RANGES = {
    "semiconductor": (45, 120),
    "display":       (30, 90),
    "battery_cell":  (21, 60),
    "connector":     (7, 30),
    "pcb":           (14, 45),
    "housing":       (14, 45),
    "camera_module": (30, 90),
    "sensor":        (14, 60),
    "cable":         (7, 21),
    "ic_chip":       (21, 90),
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Build supplier master list
# ═══════════════════════════════════════════════════════════════════════════════
def build_suppliers():
    suppliers = {}
    for i in range(1, N_SUPPLIERS + 1):
        sid  = f"supplier_{i:03d}"
        country = COUNTRY_POOL[int(rng.integers(0, len(COUNTRY_POOL)))]
        name_prefixes = ["TechMfg", "GlobalParts", "PrecisionCo", "UniComp",
                         "EliteMfg", "CoreTech", "PrimeParts", "NexGen",
                         "ApexManuf", "StarComp"]
        name = f"{name_prefixes[i % len(name_prefixes)]} {country[:3].upper()}-{i:03d}"
        suppliers[sid] = {"name": name, "country": country}
    return suppliers


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  supply_chain.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_supply_chain(suppliers):
    supplier_ids = list(suppliers.keys())

    # Decide which component IDs are single-source and critical
    single_source_ids = set(rng.choice(N_COMPONENTS, size=200, replace=False).tolist())
    critical_ids      = set(rng.choice(N_COMPONENTS, size=150, replace=False).tolist())

    tier_weights = [0.40, 0.40, 0.20]   # tiers 1, 2, 3

    path = os.path.join(OUT_DIR, "supply_chain.csv")
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["component_id", "component_name", "component_type",
                    "sku", "tier_level", "supplier_id", "supplier_name",
                    "supplier_country", "annual_volume", "unit_cost_usd",
                    "lead_time_days", "is_single_source", "critical_component"])

        for idx in range(N_COMPONENTS):
            ctype = COMP_TYPES[int(rng.integers(0, len(COMP_TYPES)))]
            names = COMP_NAME_PARTS[ctype]
            cname = names[int(rng.integers(0, len(names)))] + f" v{int(rng.integers(1,5))}"
            cid   = f"COMP-{idx+1:04d}"
            sku   = f"SKU-{ctype[:3].upper()}-{idx+1:05d}"
            tier  = int(rng.choice([1, 2, 3], p=tier_weights))
            sid   = supplier_ids[int(rng.integers(0, N_SUPPLIERS))]
            sname = suppliers[sid]["name"]
            scountry = suppliers[sid]["country"]
            vol   = int(rng.integers(500, 500_001))
            lo, hi = COST_RANGES[ctype]
            cost  = round(float(rng.uniform(lo, hi)), 2)
            lt_lo, lt_hi = LEAD_RANGES[ctype]
            lt    = int(rng.integers(lt_lo, lt_hi + 1))
            ss    = 1 if idx in single_source_ids else 0
            crit  = 1 if idx in critical_ids else 0
            w.writerow([cid, cname, ctype, sku, tier, sid, sname,
                        scountry, vol, cost, lt, ss, crit])
            rows_written += 1

    print(f"  supply_chain.csv → {rows_written} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  supplier_risk_matrix.csv
# ═══════════════════════════════════════════════════════════════════════════════
GEO_RISK = {
    "China": 75, "Taiwan": 80, "South Korea": 45,
    "Japan": 30, "USA": 20, "Germany": 15,
    "Vietnam": 55, "Malaysia": 40, "Mexico": 50, "India": 60,
}

DISASTER_RISK = {
    "China": 55, "Taiwan": 70, "South Korea": 40,
    "Japan": 75, "USA": 25, "Germany": 15,
    "Vietnam": 65, "Malaysia": 50, "Mexico": 60, "India": 55,
}


def risk_tier(fin, geo, dis, qual, otd):
    score = (100 - fin) * 0.25 + geo * 0.30 + dis * 0.15 + (100 - qual) * 0.15 + (100 - otd) * 0.15
    if score < 20:  return "Low"
    if score < 40:  return "Medium"
    if score < 60:  return "High"
    return "Critical"


def generate_risk_matrix(suppliers):
    path = os.path.join(OUT_DIR, "supplier_risk_matrix.csv")
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["supplier_id", "supplier_name", "country",
                    "financial_stability_score", "geopolitical_risk_score",
                    "natural_disaster_risk", "single_customer_dependency_pct",
                    "quality_score", "on_time_delivery_pct", "risk_tier"])
        for sid, info in suppliers.items():
            country = info["country"]
            fin  = int(np.clip(rng.normal(70, 15), 10, 100))
            geo  = int(np.clip(rng.normal(GEO_RISK.get(country, 50), 10), 0, 100))
            dis  = int(np.clip(rng.normal(DISASTER_RISK.get(country, 50), 10), 0, 100))
            dep  = round(float(rng.uniform(5, 60)), 1)
            qual = int(np.clip(rng.normal(80, 12), 30, 100))
            otd  = int(np.clip(rng.normal(85, 10), 40, 100))
            rt   = risk_tier(fin, geo, dis, qual, otd)
            w.writerow([sid, info["name"], country,
                        fin, geo, dis, dep, qual, otd, rt])
            rows_written += 1
    print(f"  supplier_risk_matrix.csv → {rows_written} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  disruption_events.csv
# ═══════════════════════════════════════════════════════════════════════════════
DISRUPTIONS = [
    # (date, type, regions, severity, dur_weeks, cost_m, recovery, description)
    ("2020-01-20", "pandemic",             ["China", "Global"],       "Critical", 104, 12000, "Ongoing",
     "COVID-19 pandemic factory shutdowns across China and global supply chains"),
    ("2020-03-15", "logistics_disruption", ["Global"],                "High",      12, 2500,  "Recovered",
     "Global air freight collapse — COVID travel restrictions"),
    ("2020-08-10", "factory_fire",         ["China"],                 "Medium",     6,  180,  "Recovered",
     "Major semiconductor fab fire — Nanjing facility"),
    ("2021-03-23", "logistics_disruption", ["Global", "Suez Canal"],  "High",       2,  9600, "Recovered",
     "Ever Given container ship blocks Suez Canal"),
    ("2021-06-01", "tariff_change",        ["USA", "China"],          "Medium",    52,  800,  "Ongoing",
     "US-China trade war tariff escalations on electronics"),
    ("2021-07-14", "flood",                ["Germany", "Europe"],     "Medium",     8,  650,  "Recovered",
     "Rhine Valley floods disrupt automotive and electronics supply"),
    ("2021-08-05", "semiconductor_shortage",["Global"],               "Critical",  78, 5000,  "Partially Recovered",
     "Global semiconductor shortage — auto and consumer electronics"),
    ("2021-10-01", "port_congestion",      ["USA"],                   "High",      16, 1200,  "Recovered",
     "Los Angeles/Long Beach port congestion — container backlog"),
    ("2022-02-24", "tariff_change",        ["Russia", "Europe"],      "High",      52, 3000,  "Ongoing",
     "Russia-Ukraine conflict — raw material and neon gas supply disruption"),
    ("2022-03-01", "logistics_disruption", ["Russia", "Global"],      "Medium",    26,  900,  "Recovered",
     "Airspace closures over Russia — rerouting adds 2-3 weeks"),
    ("2022-04-01", "pandemic",             ["China", "Shanghai"],     "High",      12, 4500,  "Recovered",
     "Shanghai COVID lockdown — major port and factory shutdowns"),
    ("2022-07-01", "earthquake",           ["Philippines"],           "Medium",     4,  150,  "Recovered",
     "Philippines earthquake damages PCB manufacturing facilities"),
    ("2022-09-15", "cyberattack",          ["Global"],                "Medium",     3,  450,  "Recovered",
     "Ransomware attack on major logistics provider — shipment delays"),
    ("2022-11-01", "quality_recall",       ["Global"],                "Medium",     8,  600,  "Recovered",
     "Battery cell quality recall — fire risk in consumer electronics"),
    ("2023-01-10", "tariff_change",        ["USA", "Taiwan"],         "Low",       52,  300,  "Ongoing",
     "CHIPS Act export controls on advanced semiconductors to China"),
    ("2023-03-20", "flood",                ["Malaysia"],              "Medium",     6,  280,  "Recovered",
     "Penang floods disrupt semiconductor assembly and packaging"),
    ("2023-05-01", "supplier_bankruptcy",  ["Global"],                "High",       4,  750,  "Recovered",
     "Tier-2 connector supplier files bankruptcy — 200+ OEMs affected"),
    ("2023-07-15", "earthquake",           ["Japan"],                 "Medium",     3,  420,  "Recovered",
     "Japan earthquake impacts automotive sensor production"),
    ("2023-09-01", "port_congestion",      ["China"],                 "Low",        8,  380,  "Recovered",
     "Typhoon season causes Shenzhen/Guangzhou port delays"),
    ("2023-10-01", "tariff_change",        ["USA", "China"],          "Medium",    52,  550,  "Ongoing",
     "Additional US tariffs on Chinese electronics components"),
    ("2023-12-01", "logistics_disruption", ["Red Sea", "Global"],     "High",      26, 1800,  "Ongoing",
     "Red Sea shipping disruptions — Houthi attacks on cargo vessels"),
    ("2024-01-15", "factory_fire",         ["South Korea"],           "Medium",     6,  320,  "Recovered",
     "OLED panel factory fire in Cheonan — display supply tightens"),
    ("2024-02-01", "cyberattack",          ["Taiwan"],                "High",       2,  900,  "Recovered",
     "Cyberattack on major TSMC supplier — production halted briefly"),
    ("2024-03-01", "tariff_change",        ["EU", "China"],           "Medium",    52,  420,  "Ongoing",
     "EU anti-subsidy tariffs on Chinese electric vehicle components"),
    ("2024-04-15", "earthquake",           ["Taiwan"],                "Critical",   8, 2100,  "Partially Recovered",
     "Taiwan 7.4 magnitude earthquake — TSMC and packaging fabs impacted"),
    ("2024-05-01", "flood",                ["UAE", "Global"],         "Low",        2,  180,  "Recovered",
     "Dubai flooding disrupts air cargo hub operations"),
    ("2020-06-01", "logistics_disruption", ["Brazil"],                "Low",        4,   90,  "Recovered",
     "Brazilian port strikes cause 3-week cargo delays"),
    ("2021-02-10", "factory_fire",         ["Japan"],                 "Medium",     5,  250,  "Recovered",
     "Renesas semiconductor plant fire — automotive chip shortage worsens"),
    ("2022-06-01", "port_congestion",      ["China", "Shanghai"],     "High",       8, 1100,  "Recovered",
     "Post-lockdown Shanghai port backlog — 300+ vessels waiting"),
    ("2023-06-01", "supplier_bankruptcy",  ["Vietnam"],               "Low",        3,  120,  "Recovered",
     "Vietnamese cable harness supplier files for restructuring"),
    ("2020-09-01", "quality_recall",       ["China", "Global"],       "Medium",     6,  380,  "Recovered",
     "DRAM module quality issues — data integrity concerns"),
    ("2021-04-01", "tariff_change",        ["USA", "EU"],             "Low",       26,  200,  "Recovered",
     "US-EU steel and aluminum tariff dispute impacts housing components"),
    ("2022-01-20", "cyberattack",          ["Global"],                "Medium",     2,  350,  "Recovered",
     "Log4j vulnerability exploitation hits supply chain software"),
    ("2023-02-06", "earthquake",           ["Turkey", "Syria"],       "High",       12,  800,  "Recovered",
     "Turkey-Syria earthquake disrupts cable and connector manufacturing"),
    ("2024-06-01", "logistics_disruption", ["Panama Canal"],          "Medium",    16,  950,  "Ongoing",
     "Panama Canal low water levels reduce transit capacity by 40%"),
    ("2020-05-01", "pandemic",             ["India"],                 "High",       16,  600,  "Recovered",
     "India COVID lockdown impacts pharmaceutical and PCB supply"),
    ("2021-09-15", "flood",                ["China", "Henan"],        "Medium",     6,  430,  "Recovered",
     "Zhengzhou floods disrupt Foxconn and automotive suppliers"),
    ("2022-08-01", "tariff_change",        ["USA"],                   "Medium",    52,  670,  "Ongoing",
     "Inflation Reduction Act — domestic content requirements for EVs"),
    ("2023-04-01", "factory_fire",         ["Mexico"],                "Low",        4,  140,  "Recovered",
     "Monterrey factory fire impacts nearshore manufacturing"),
    ("2024-02-20", "port_congestion",      ["USA", "East Coast"],     "Medium",     8,  520,  "Ongoing",
     "East Coast port congestion amid Panama Canal rerouting"),
    ("2020-11-01", "supplier_bankruptcy",  ["USA"],                   "Low",        4,  160,  "Recovered",
     "Small US sensor supplier enters Chapter 11 — 40 customers affected"),
    ("2021-12-01", "logistics_disruption", ["Global"],                "Medium",    12,  750,  "Recovered",
     "Holiday season container crunch — spot rates hit record $20k/FEU"),
    ("2022-04-15", "quality_recall",       ["Global"],                "Medium",     5,  290,  "Recovered",
     "Capacitor batch failure — affects consumer electronics PCBs globally"),
    ("2023-08-01", "cyberattack",          ["USA"],                   "Medium",     3,  410,  "Recovered",
     "MOVEit vulnerability exploited — supplier ERP data breached"),
    ("2024-01-01", "tariff_change",        ["USA", "Mexico"],         "Low",       52,  230,  "Ongoing",
     "USMCA review — rules-of-origin tightening for electronics"),
    ("2020-04-01", "logistics_disruption", ["Global"],                "High",       8, 1900,  "Recovered",
     "PPE demand surge causes container shortage for electronics"),
    ("2021-05-10", "earthquake",           ["Indonesia"],             "Low",        3,   95,  "Recovered",
     "Java earthquake disrupts nickel and cobalt mining supply"),
    ("2022-12-01", "flood",                ["Australia"],             "Low",        4,  110,  "Recovered",
     "Queensland floods impact rare earth mineral exports"),
    ("2023-11-01", "supplier_bankruptcy",  ["Europe"],                "Medium",     6,  340,  "Recovered",
     "European Tier-2 semiconductor substrate supplier files insolvency"),
    ("2024-03-15", "quality_recall",       ["Global"],                "Low",        4,  190,  "Recovered",
     "Lithium-ion battery swelling issue — 1.2M units recalled"),
]

def generate_disruptions():
    supplier_ids = [f"supplier_{i:03d}" for i in range(1, N_SUPPLIERS + 1)]
    path = os.path.join(OUT_DIR, "disruption_events.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "event_date", "event_type", "affected_supplier_ids",
                    "affected_regions", "impact_severity", "duration_weeks",
                    "cost_impact_usd_million", "recovery_status"])
        for idx, ev in enumerate(DISRUPTIONS):
            date, etype, regions, sev, dur, cost, recovery, desc = ev
            # pick 1-10 random affected suppliers
            n_aff = int(rng.integers(1, 11))
            aff_ids = ";".join(rng.choice(supplier_ids, size=n_aff, replace=False).tolist())
            reg_str = ";".join(regions)
            w.writerow([f"EVT-{idx+1:03d}", date, etype, aff_ids,
                        reg_str, sev, dur, cost, recovery])
    print(f"  disruption_events.csv → {len(DISRUPTIONS)} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  inventory_levels.csv
# ═══════════════════════════════════════════════════════════════════════════════
def generate_inventory():
    base_date = datetime(2024, 6, 30)
    path = os.path.join(OUT_DIR, "inventory_levels.csv")
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["component_id", "current_stock_units", "weeks_of_supply",
                    "reorder_point", "safety_stock_units", "last_replenishment_date"])
        for idx in range(N_COMPONENTS):
            cid   = f"COMP-{idx+1:04d}"
            stock = int(rng.integers(0, 50_001))
            wos   = round(float(rng.uniform(0.5, 26.0)), 1)
            rop   = int(rng.integers(100, 10_001))
            ss    = int(rng.integers(50, 5_001))
            days_back = int(rng.integers(1, 91))
            replen_date = (base_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
            w.writerow([cid, stock, wos, rop, ss, replen_date])
            rows_written += 1
    print(f"  inventory_levels.csv → {rows_written} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  README.md
# ═══════════════════════════════════════════════════════════════════════════════
def write_readme():
    text = """# MBA-P3: SupplyZen — Supply Chain Risk Intelligence Dataset

## Problem Statement
You are the Chief Supply Chain Officer at a global consumer electronics manufacturer.
Analyse the supply chain data to identify critical risks, recommend mitigation strategies,
and build a supply chain resilience score for each supplier.

## Dataset Overview

| File | Rows | Description |
|------|------|-------------|
| supply_chain.csv | 2,000 | Component-level supply chain data |
| supplier_risk_matrix.csv | 500 | Risk scores for each supplier |
| disruption_events.csv | 50 | Historical disruption events 2020-2024 |
| inventory_levels.csv | 2,000 | Current inventory per component |

## supply_chain.csv Columns
- component_id: Unique component identifier (COMP-XXXX)
- component_type: semiconductor / display / battery_cell / connector / pcb / housing / camera_module / sensor / cable / ic_chip
- tier_level: 1 (direct supplier), 2, 3
- is_single_source: 1 = only one supplier globally, 0 = multiple sources
- critical_component: 1 = production halts if unavailable

## Key Challenges
1. Identify single-source components with high geopolitical risk
2. Quantify financial exposure from top-10 disruption scenarios
3. Build a multi-tier supplier risk heatmap
4. Recommend dual-sourcing priorities given cost constraints

## Suggested Approach
- Graph analysis of multi-tier dependencies
- Monte Carlo simulation for disruption impact
- Risk scoring: financial × geopolitical × dependency
- Optimisation: cost vs. resilience trade-off model
"""
    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print("  README.md written")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating MBA-P3 files...")
    suppliers = build_suppliers()
    print("  [1/5] supply_chain.csv")
    generate_supply_chain(suppliers)
    print("  [2/5] supplier_risk_matrix.csv")
    generate_risk_matrix(suppliers)
    print("  [3/5] disruption_events.csv")
    generate_disruptions()
    print("  [4/5] inventory_levels.csv")
    generate_inventory()
    print("  [5/5] README.md")
    write_readme()
    print("MBA-P3 complete.")
