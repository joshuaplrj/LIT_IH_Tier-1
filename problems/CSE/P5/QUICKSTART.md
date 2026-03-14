# Quantum-Safe Encrypted Database — Quick Start

## Objective
Build a database system that stores all records in encrypted form and answers SQL-like queries (equality search, range queries, aggregation) without ever decrypting data on the server. The encryption must be post-quantum secure — no RSA, ECC, or classical Diffie-Hellman.

## Inputs
- No pre-given data files. You generate and encrypt a test table of 100,000 records with 5 columns.
- The evaluation harness sends encrypted query requests; your server must return correct results without accessing plaintext.
- Reference test workload: `benchmark/queries.json` — a list of SELECT queries in JSON format.

## Expected Output
Four deliverables:
- `server.py` — The encrypted database server (query processor, never decrypts).
- `client.py` — The client that encrypts data before upload and decrypts query results.
- `architecture.md` — System architecture document explaining your crypto scheme, security model, and performance analysis.
- `benchmarks.json` — Performance results: latency (ms) per query type on 100k-record table.

Server API (HTTP or function-call interface — your choice):
- `POST /insert`  — Body: `{"encrypted_record": [...]}` — inserts one encrypted row.
- `POST /query`   — Body: `{"type": "equality"|"range"|"count", "column": N, "token": "..."}` — returns matching encrypted rows.
- `GET  /count`   — Returns total record count.

## Recommended First Steps
1. Choose your cryptographic building block: **Searchable Symmetric Encryption (SSE)** is the most practical option — the client generates a search token per query using a PRF (pseudo-random function) keyed with a secret key, and the server matches tokens against stored encrypted indexes without learning the plaintext.
2. Implement a simple SSE scheme (e.g., SSE-1 or SSE-2 from Curtmola et al. 2006) for equality search first, then extend to range queries using an order-preserving structure.
3. For post-quantum compliance, replace any HMAC/AES-based PRF with a lattice-based PRF or use **CRYSTALS-Kyber** (post-quantum KEM) for key exchange if your scheme requires it.

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Functionality: all three query types return correct results | 40% |
| Security model: documented leakage profile, mitigation strategies | 25% |
| Performance: point query < 2s on 100k records | 20% |
| Documentation: architecture clarity, crypto justification | 15% |

## Common Pitfalls
- Using AES-GCM alone for encryption and doing server-side decryption to answer queries — this violates the "no server-side decryption" requirement even if AES is quantum-resistant in practice.
- Ignoring access pattern leakage: even with encrypted data, the server can see which rows match a query. Your security model must acknowledge and address this (e.g., via ORAM or dummy queries).
- Implementing fully homomorphic encryption (FHE): theoretically correct but 1000× too slow for the < 2s performance target.
- Confusing IND-CPA security (standard encryption) with query privacy — a quantum-safe cipher like Kyber is not automatically searchable; you need a separate searchable scheme.
- Not testing correctness before benchmarking — a fast but incorrect query engine scores 0 on functionality.
