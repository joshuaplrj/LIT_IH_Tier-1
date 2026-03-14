# CSE-P5: Quantum-Safe Encrypted Database

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
