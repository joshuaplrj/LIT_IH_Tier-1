# Quantum-Safe Encrypted Database — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

The core tension in this problem is the **functionality-security-performance triangle**:

- **Fully Homomorphic Encryption (FHE)**: supports arbitrary computation on encrypted data (full functionality, strong security) but is millions of times slower than plaintext — far too slow for the < 2s target.
- **Plaintext database with encryption at rest**: fast, but the server must decrypt to query — violates the "no server-side decryption" rule.
- **Searchable Symmetric Encryption (SSE)**: the client holds a secret key, encrypts records into a special structure that supports keyword search by issuing a search "token". The server matches tokens against the encrypted index without learning the plaintext. This is the right family of techniques.

For **range queries**, SSE alone is insufficient. You need either:
- **Order-Preserving Encryption (OPE)** or **Order-Revealing Encryption (ORE)**: preserves the ordering of plaintexts in ciphertext space, so the server can range-query ciphertexts directly. Security tradeoff: the server learns the order of values (but not their values).
- **Binary-tree SSE** with a per-level search token for each bit of the range.

For **post-quantum compliance**, replace HMAC-SHA256 (your PRF) with a hash-based PRF (e.g., BLAKE3, SHA3-512) — hash functions are already quantum-resistant (Grover's algorithm only gives a quadratic speedup, so SHA3-256 with 256-bit security gives 128-bit post-quantum security). For key encapsulation, use **CRYSTALS-Kyber** (NIST-standardised PQC KEM).

## Tier 2 — Technique Guidance (-10% score penalty)

**SSE for equality search (EDB scheme):**

1. Client setup:
   - Secret key `K`.
   - For each distinct value `v` in column `col`, compute a search token: `T(col, v) = PRF(K, "search" || col || v)`.
   - For each record `r` containing value `v` in column `col`, compute a label: `L = PRF(K, "label" || col || v || row_id)` and a value: `V = Encrypt(K, row_id)`.
   - Store `(L → V)` pairs in a hash table on the server.

2. Query: client sends token `T(col, v)`, server iterates through all labels derived from the token and returns matching encrypted row IDs. Client decrypts row IDs and fetches full encrypted records.

**For range queries:** Use an **interval tree** approach:
- Decompose range `[lo, hi]` into a set of canonical intervals using a complete binary tree over the value domain.
- Build an SSE index per canonical interval node.
- At query time, client sends one search token per canonical interval covering `[lo, hi]`.

**Post-quantum PRF:** Use Python's `hashlib.shake_256(key + message).digest(32)` as a PRF — SHA3/SHAKE is quantum-resistant. For the key, derive it from a Kyber KEM if key exchange with the server is needed.

**Performance optimisation:** For 100k records × 5 columns, the SSE index has at most 500k entries. A Python `dict` lookup is O(1) — a point query should be well under 2 seconds. Use `shelve` or `sqlite3` for persistence.

## Tier 3 — Implementation Guidance (-15% score penalty)

**Concrete implementation steps:**

1. **Key generation** (client side):
   ```python
   import os, hashlib
   MASTER_KEY = os.urandom(32)   # 256-bit secret key

   def prf(key: bytes, data: str) -> bytes:
       return hashlib.shake_256(key + data.encode()).digest(32)
   ```

2. **Record encryption** (client side):
   ```python
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   def encrypt_record(key: bytes, record: list, row_id: int) -> bytes:
       aes = AESGCM(key[:32])
       nonce = os.urandom(12)
       plaintext = json.dumps({"row_id": row_id, "data": record}).encode()
       return nonce + aes.encrypt(nonce, plaintext, None)
   ```

3. **SSE index construction** (client side, equality search):
   ```python
   sse_index = {}   # to be sent to server
   for row_id, record in enumerate(plaintext_table):
       for col_idx, value in enumerate(record):
           label = prf(MASTER_KEY, f"label|{col_idx}|{value}|{row_id}").hex()
           enc_row_id = prf(MASTER_KEY, f"enc_row|{row_id}").hex()
           sse_index[label] = enc_row_id
   ```

4. **Server storage** (server side — never sees plaintext):
   ```python
   # Server stores: sse_index (dict), encrypted_records (list of bytes)
   # Server receives a search token, derives labels, returns matching enc_row_ids
   def query_equality(token: bytes, n_results_hint: int) -> list:
       results = []
       for i in range(n_results_hint):
           label = prf_server(token, str(i)).hex()   # server-side label derivation
           if label in sse_index:
               results.append(sse_index[label])
       return results
   ```

5. **Range query extension:**
   - Encode numeric column values as fixed-width integers.
   - Build a binary search tree over the value domain; each internal node covers a range.
   - For each node, build an SSE index for all records whose value falls in that node's range.
   - Query: decompose `[lo, hi]` into O(log N) canonical tree nodes; send one token per node.

6. **COUNT aggregation:**
   - Server can count matching labels directly (returns an integer, no decryption needed).

7. **Security model documentation (for architecture.md):**
   - **What the server learns**: access pattern (which rows match a query), query pattern (whether two queries match the same rows), size of result sets. It does NOT learn plaintext values or key.
   - **Mitigations**: ORAM (Oblivious RAM) to hide access patterns; padding result sets to a fixed size to hide result size; query batching to hide query frequency.
   - **Post-quantum argument**: PRF based on SHA3-SHAKE256 has 128-bit post-quantum security (Grover attack halves effective key length). No RSA/ECC used.

8. **Benchmark harness**: generate 100k records, insert all, then time 1000 random point queries and report mean/p99 latency.
