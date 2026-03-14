"""
CSE-P5: Quantum-Safe Encrypted Database
Generates 100,000 patient records, schema.json, and README.md
"""

import numpy as np
import os
import csv
import json

BASE = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\CSE\CSE-P5"
os.makedirs(BASE, exist_ok=True)

np.random.seed(42)

N_RECORDS = 100_000

# ── Name generation (no faker) ─────────────────────────────────────────
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Kenneth", "Donna",
    "George", "Michelle", "Joshua", "Carol", "Kevin", "Amanda", "Brian", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory",
    "Debra", "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet", "Jack",
    "Catherine", "Dennis", "Maria", "Jerry", "Heather", "Tyler", "Diane",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Turner", "Phillips", "Evans", "Collins", "Edwards", "Stewart",
    "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
    "Cooper", "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox",
    "Ward", "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett",
    "Gray", "Mendoza", "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders",
    "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez", "Powell", "Jenkins",
    "Perry", "Russell", "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes",
]

ICD_PREFIXES = ["ICD-A", "ICD-B", "ICD-C", "ICD-D", "ICD-E", "ICD-F", "ICD-G",
                "ICD-H", "ICD-I", "ICD-J", "ICD-K", "ICD-L", "ICD-M", "ICD-N"]

# ── Vectorized generation ───────────────────────────────────────────────
ids = np.arange(1, N_RECORDS + 1)
ages = np.random.randint(18, 91, size=N_RECORDS)

# Treatment cost: log-normal-ish, clipped to [100, 50000]
raw_costs = np.random.exponential(scale=5000, size=N_RECORDS) + 100
costs = np.clip(raw_costs, 100.0, 50000.0)

# Names (sampled with replacement)
first_idx = np.random.randint(0, len(FIRST_NAMES), size=N_RECORDS)
last_idx  = np.random.randint(0, len(LAST_NAMES), size=N_RECORDS)

# ICD codes
prefix_idx = np.random.randint(0, len(ICD_PREFIXES), size=N_RECORDS)
icd_numbers = np.random.randint(10, 100, size=N_RECORDS)

print("Writing database.csv (100,000 records)...")
db_path = os.path.join(BASE, "database.csv")
with open(db_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "patient_name", "age", "diagnosis_code", "treatment_cost"])
    for i in range(N_RECORDS):
        name = f"{FIRST_NAMES[first_idx[i]]} {LAST_NAMES[last_idx[i]]}"
        icd = f"{ICD_PREFIXES[prefix_idx[i]]}{icd_numbers[i]}"
        writer.writerow([
            int(ids[i]),
            name,
            int(ages[i]),
            icd,
            round(float(costs[i]), 2),
        ])
print(f"Written: {db_path}")

# ── schema.json ─────────────────────────────────────────────────────────
schema = {
    "table_name": "patient_records",
    "num_records": N_RECORDS,
    "columns": [
        {"name": "id",             "type": "INTEGER",  "description": "Unique patient ID (1 to 100000)", "nullable": False},
        {"name": "patient_name",   "type": "VARCHAR",  "description": "Full name (First Last)",          "nullable": False},
        {"name": "age",            "type": "INTEGER",  "description": "Patient age (18–90)",             "nullable": False},
        {"name": "diagnosis_code", "type": "VARCHAR",  "description": "ICD code (e.g. ICD-A23)",         "nullable": False},
        {"name": "treatment_cost", "type": "FLOAT",    "description": "Treatment cost in USD (100–50000)","nullable": False},
    ],
    "seed": 42,
    "expected_queries": [
        "SELECT * FROM patient_records WHERE age > 65",
        "SELECT AVG(treatment_cost) FROM patient_records WHERE diagnosis_code LIKE 'ICD-C%'",
        "SELECT patient_name, treatment_cost FROM patient_records ORDER BY treatment_cost DESC LIMIT 10",
        "SELECT diagnosis_code, COUNT(*) FROM patient_records GROUP BY diagnosis_code",
    ]
}

schema_path = os.path.join(BASE, "schema.json")
with open(schema_path, "w") as f:
    json.dump(schema, f, indent=2)
print(f"Written: {schema_path}")

# ── README.md ────────────────────────────────────────────────────────────
readme = """# CSE-P5: Quantum-Safe Encrypted Database

## Overview
You are given a plaintext CSV database of 100,000 synthetic patient records.
Your task is to implement a **quantum-safe encrypted database** that supports
efficient encrypted queries without revealing individual record contents.

## Data
`database.csv` — 100,000 rows, columns:
- `id` — integer (1–100,000)
- `patient_name` — string (First Last)
- `age` — integer (18–90)
- `diagnosis_code` — string (ICD code, e.g. "ICD-A23")
- `treatment_cost` — float (100.00–50,000.00 USD)

Schema details in `schema.json`.

## Task
Design and implement an encrypted database system that:

1. **Encryption layer**: Encrypt each record using a post-quantum safe scheme
   (e.g., lattice-based encryption, or AES-256-GCM as a symmetric stand-in).

2. **Encrypted queries**: Support the following query types on encrypted data:
   - Range queries: `age > 65`
   - Equality queries: `diagnosis_code = 'ICD-C23'`
   - Aggregation: `AVG(treatment_cost)` grouped by diagnosis prefix
   - Top-K: `ORDER BY treatment_cost DESC LIMIT 10`

3. **Key management**: Implement a key hierarchy with:
   - Master key
   - Per-column encryption keys (derived from master)
   - Query tokens that allow specific queries without full decryption

## Deliverables
- Encrypted database file(s)
- Query interface (CLI or API)
- Decryption utility for result verification
- Security analysis document

## Scoring
- Correctness: query results match plaintext queries (40%)
- Security: encryption strength and key management (30%)
- Performance: query latency on encrypted data (20%)
- Documentation: design clarity (10%)

## Sample Queries to Support
```sql
SELECT * FROM patient_records WHERE age > 65;
SELECT AVG(treatment_cost) FROM patient_records WHERE diagnosis_code LIKE 'ICD-C%';
SELECT patient_name, treatment_cost FROM patient_records
    ORDER BY treatment_cost DESC LIMIT 10;
SELECT diagnosis_code, COUNT(*) FROM patient_records GROUP BY diagnosis_code;
```
"""

readme_path = os.path.join(BASE, "README.md")
with open(readme_path, "w") as f:
    f.write(readme)
print(f"Written: {readme_path}")
print("CSE-P5 generation complete.")
