"""
Quantum-Safe Encrypted Database — Starter Skeleton
CSE Problem 5: Encrypted SQL-like query processing without server-side decryption.

Components:
  - crypto_utils.py-level helpers in this file
  - SimpleSSEClient  — builds the encrypted index (equality + range)
  - SimpleSSEServer  — answers queries without seeing plaintext
  - Benchmark harness

Usage:
    python starter.py --mode setup   --records 100000 --db_path db.json
    python starter.py --mode query   --db_path db.json --type equality --col 0 --val 42
    python starter.py --mode range   --db_path db.json --col 1 --lo 10 --hi 500
    python starter.py --mode count   --db_path db.json --col 0 --val 42
    python starter.py --mode bench   --db_path db.json --n_queries 1000
"""

import argparse
import hashlib
import json
import os
import random
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Crypto Utilities
# ---------------------------------------------------------------------------

# Post-quantum note: SHAKE-256 (SHA3 family) is quantum-resistant.
# Grover's attack gives sqrt(2^256) = 2^128 quantum queries — acceptable.
# For full Kyber KEM integration, install: pip install pqcrypto or liboqs-python
# TODO: replace the following with liboqs Kyber KEM for key encapsulation
#       once the library is available in your environment.

def prf(key: bytes, data: str) -> bytes:
    """Pseudo-random function: SHAKE256(key || data) -> 32 bytes. Quantum-resistant."""
    h = hashlib.shake_256()
    h.update(key)
    h.update(data.encode("utf-8"))
    return h.digest(32)


def derive_subkey(master_key: bytes, purpose: str) -> bytes:
    """Derive a domain-separated subkey for each purpose."""
    return prf(master_key, f"subkey:{purpose}")


try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


def encrypt_bytes(key: bytes, plaintext: bytes) -> bytes:
    """AES-256-GCM authenticated encryption. Returns nonce || ciphertext."""
    if _HAS_CRYPTOGRAPHY:
        aes = AESGCM(key[:32])
        nonce = os.urandom(12)
        return nonce + aes.encrypt(nonce, plaintext, None)
    else:
        # Fallback: XOR with SHAKE256 keystream (insecure — for skeleton only)
        keystream = hashlib.shake_256(key + b"xor").digest(len(plaintext))
        ct = bytes(a ^ b for a, b in zip(plaintext, keystream))
        nonce = os.urandom(12)
        return nonce + ct


def decrypt_bytes(key: bytes, ciphertext: bytes) -> bytes:
    """AES-256-GCM decryption. Input: nonce(12) || ciphertext."""
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    if _HAS_CRYPTOGRAPHY:
        aes = AESGCM(key[:32])
        return aes.decrypt(nonce, ct, None)
    else:
        keystream = hashlib.shake_256(key + b"xor").digest(len(ct))
        return bytes(a ^ b for a, b in zip(ct, keystream))


# ---------------------------------------------------------------------------
# SSE Client
# ---------------------------------------------------------------------------

class SSEClient:
    """
    Client that holds the master secret key, encrypts records, and
    builds the SSE index (server never sees plaintext).
    """

    NUM_COLUMNS = 5
    VALUE_DOMAIN = 65536    # values are integers in [0, VALUE_DOMAIN)

    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or os.urandom(32)
        self._enc_key   = derive_subkey(self.master_key, "record_encryption")
        self._idx_key   = derive_subkey(self.master_key, "sse_index")
        self._rng_key   = derive_subkey(self.master_key, "range_index")

    # ------------------------------------------------------------------
    # Record Encryption
    # ------------------------------------------------------------------

    def encrypt_record(self, row_id: int, record: List[int]) -> bytes:
        """Encrypt a plaintext record to bytes. Client holds the key."""
        payload = json.dumps({"row_id": row_id, "data": record}).encode()
        return encrypt_bytes(self._enc_key, payload)

    def decrypt_record(self, ciphertext: bytes) -> dict:
        """Decrypt a record ciphertext. Only the client can do this."""
        return json.loads(decrypt_bytes(self._enc_key, ciphertext).decode())

    # ------------------------------------------------------------------
    # SSE Index (Equality Search)
    # ------------------------------------------------------------------

    def build_equality_index(self, plaintext_table: List[List[int]]) -> Dict[str, str]:
        """
        Build SSE index for equality search.
        index[label] = encrypted_row_id
        Server stores this dict. Never contains plaintext.

        TODO: For better security, use a more sophisticated SSE scheme
              (e.g., SSE-2, Diana, or TROCADOR) that hides the number of
              results per keyword.
        """
        index: Dict[str, str] = {}
        for row_id, record in enumerate(plaintext_table):
            for col_idx, value in enumerate(record):
                label = self._equality_label(col_idx, value, row_id)
                enc_rid = prf(self._idx_key, f"enc_row:{row_id}").hex()
                index[label] = enc_rid
        return index

    def _equality_label(self, col: int, value: int, row_id: int) -> str:
        return prf(self._idx_key, f"eq:{col}:{value}:{row_id}").hex()

    def equality_token(self, col: int, value: int) -> bytes:
        """
        Generate a search token for equality query on col=value.
        Server uses this to find all labels without learning col or value.
        """
        return prf(self._idx_key, f"token:{col}:{value}")

    def derive_label_from_token(self, token: bytes, row_id: int) -> str:
        """Server-side: derive label from token + row_id."""
        return prf(token, f"row:{row_id}").hex()

    # ------------------------------------------------------------------
    # Range Index (Order-Preserving approach — simplified)
    # ------------------------------------------------------------------

    def build_range_index(self, plaintext_table: List[List[int]],
                          col: int) -> Dict[str, str]:
        """
        Build a range-queryable index for column `col`.
        Uses a binary tree over VALUE_DOMAIN: each leaf covers one value,
        each internal node covers a range. Client computes one SSE entry
        per (node, row_id) pair for nodes that contain the row's value.

        TODO: Replace with a proper range-SSE scheme such as Demertzis et al.
              or RANGE-SSE for sub-linear query complexity.
        """
        index: Dict[str, str] = {}
        for row_id, record in enumerate(plaintext_table):
            value = record[col]
            # For each ancestor of the value in the binary tree, add an entry
            for node_id in self._ancestor_nodes(value):
                label = prf(self._rng_key,
                            f"range:{col}:{node_id}:{row_id}").hex()
                enc_rid = prf(self._idx_key, f"enc_row:{row_id}").hex()
                index[label] = enc_rid
        return index

    def range_tokens(self, col: int, lo: int, hi: int) -> List[bytes]:
        """
        Return list of search tokens for range query [lo, hi] on column col.
        Uses O(log(VALUE_DOMAIN)) canonical tree node tokens.
        """
        tokens = []
        for node_id in self._canonical_nodes(lo, hi):
            token = prf(self._rng_key, f"range_token:{col}:{node_id}")
            tokens.append(token)
        return tokens

    def _ancestor_nodes(self, value: int) -> List[int]:
        """Return IDs of all binary tree nodes covering 'value'."""
        nodes = []
        lo, hi = 0, self.VALUE_DOMAIN - 1
        node_id = 1
        while lo <= hi:
            nodes.append(node_id)
            mid = (lo + hi) // 2
            if value <= mid:
                hi = mid; node_id = 2 * node_id
            else:
                lo = mid + 1; node_id = 2 * node_id + 1
        return nodes

    def _canonical_nodes(self, lo: int, hi: int) -> List[int]:
        """
        Return the minimal set of binary tree nodes covering exactly [lo, hi].
        TODO: Implement proper canonical node decomposition.
        """
        # Simplified: return root node (covers all) — replace with proper decomposition
        return [1]

    # ------------------------------------------------------------------
    # COUNT token
    # ------------------------------------------------------------------

    def count_token(self, col: int, value: int) -> bytes:
        return self.equality_token(col, value)


# ---------------------------------------------------------------------------
# SSE Server
# ---------------------------------------------------------------------------

class SSEServer:
    """
    Database server that NEVER decrypts data.
    Stores encrypted records and SSE indexes.
    Answers queries by matching search tokens against index labels.
    """

    def __init__(self):
        self.encrypted_records: List[bytes] = []
        self.equality_index: Dict[str, str] = {}
        self.range_index: Dict[str, str] = {}
        self.total_rows = 0

    def load(self, db_path: str):
        with open(db_path) as f:
            data = json.load(f)
        self.encrypted_records = [bytes.fromhex(r) for r in data["records"]]
        self.equality_index    = data["equality_index"]
        self.range_index       = data.get("range_index", {})
        self.total_rows        = len(self.encrypted_records)

    def save(self, db_path: str):
        data = {
            "records":        [r.hex() for r in self.encrypted_records],
            "equality_index": self.equality_index,
            "range_index":    self.range_index,
        }
        with open(db_path, "w") as f:
            json.dump(data, f)

    def insert(self, enc_record: bytes):
        self.encrypted_records.append(enc_record)
        self.total_rows += 1

    def query_equality(self, token: bytes, client: SSEClient) -> List[bytes]:
        """
        Return list of encrypted records matching the equality token.
        Server derives labels from the token and looks them up in the index.
        Does NOT decrypt anything.
        """
        matching_enc_row_ids = []
        for row_id in range(self.total_rows):
            label = client.derive_label_from_token(token, row_id)
            if label in self.equality_index:
                matching_enc_row_ids.append(self.equality_index[label])

        # Return encrypted records for matching row IDs
        # (Server looks up row IDs without decrypting them)
        # TODO: In a real scheme the server should not learn row IDs.
        #       Use an encrypted pointer structure instead.
        results = []
        for enc_rid in matching_enc_row_ids:
            # Decode row ID from encrypted form (requires client cooperation in full scheme)
            # For starter: use direct lookup with dummy decryption
            results.extend(self.encrypted_records[:1])  # placeholder
        return results

    def query_range(self, tokens: List[bytes], client: SSEClient) -> List[bytes]:
        """
        Return encrypted records matching any of the range tokens.
        TODO: implement proper set union / deduplication across tokens.
        """
        matching = set()
        for token in tokens:
            for row_id in range(self.total_rows):
                label = client.derive_label_from_token(token, row_id)
                if label in self.range_index:
                    matching.add(row_id)
        return [self.encrypted_records[rid] for rid in matching
                if rid < len(self.encrypted_records)]

    def count_matching(self, token: bytes, client: SSEClient) -> int:
        """Return COUNT(*) for an equality query. No decryption needed."""
        count = 0
        for row_id in range(self.total_rows):
            label = client.derive_label_from_token(token, row_id)
            if label in self.equality_index:
                count += 1
        return count


# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------

def generate_table(n_rows: int, n_cols: int = 5) -> List[List[int]]:
    """Generate a random plaintext table with integer values."""
    return [
        [random.randint(0, SSEClient.VALUE_DOMAIN - 1) for _ in range(n_cols)]
        for _ in range(n_rows)
    ]


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_benchmark(db_path: str, n_queries: int = 1000):
    """Benchmark query latency on the encrypted database."""
    client = SSEClient()   # NOTE: key is regenerated — use saved key in real scenario
    server = SSEServer()
    server.load(db_path)

    latencies = []
    for _ in range(n_queries):
        col = random.randint(0, SSEClient.NUM_COLUMNS - 1)
        val = random.randint(0, SSEClient.VALUE_DOMAIN - 1)
        token = client.equality_token(col, val)
        t0 = time.time()
        _ = server.query_equality(token, client)
        latencies.append((time.time() - t0) * 1000)   # ms

    mean_ms = sum(latencies) / len(latencies)
    p99_ms  = sorted(latencies)[int(0.99 * len(latencies))]
    p50_ms  = sorted(latencies)[int(0.50 * len(latencies))]

    result = {
        "n_queries":     n_queries,
        "mean_latency_ms": round(mean_ms, 3),
        "p50_latency_ms":  round(p50_ms, 3),
        "p99_latency_ms":  round(p99_ms, 3),
        "target_ms":       2000,
        "target_met":      (p99_ms < 2000),
    }
    print(json.dumps(result, indent=2))
    with open("benchmarks.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Benchmarks saved to benchmarks.json")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Quantum-Safe Encrypted Database starter."
    )
    parser.add_argument("--mode",      type=str, required=True,
                        choices=["setup", "query", "range", "count", "bench"],
                        help="Operation mode.")
    parser.add_argument("--records",   type=int, default=100_000,
                        help="Number of records to generate (setup mode).")
    parser.add_argument("--db_path",   type=str, default="db.json",
                        help="Path to encrypted database file.")
    parser.add_argument("--col",       type=int, default=0,
                        help="Column index for query.")
    parser.add_argument("--val",       type=int, default=0,
                        help="Query value (equality/count).")
    parser.add_argument("--lo",        type=int, default=0,
                        help="Range query lower bound.")
    parser.add_argument("--hi",        type=int, default=100,
                        help="Range query upper bound.")
    parser.add_argument("--n_queries", type=int, default=1000,
                        help="Number of benchmark queries.")
    args = parser.parse_args()

    if args.mode == "setup":
        print(f"Generating {args.records} plaintext records ...")
        table = generate_table(args.records)

        print("Building SSE indexes ...")
        client = SSEClient()
        eq_index  = client.build_equality_index(table)
        rng_index = client.build_range_index(table, col=0)

        print("Encrypting records ...")
        server = SSEServer()
        server.equality_index = eq_index
        server.range_index    = rng_index
        for row_id, record in enumerate(table):
            enc = client.encrypt_record(row_id, record)
            server.insert(enc)

        print(f"Saving database to {args.db_path} ...")
        server.save(args.db_path)

        # Save master key (in practice, keep this secure on the client only)
        with open("client_key.hex", "w") as f:
            f.write(client.master_key.hex())
        print(f"Setup complete. Master key saved to client_key.hex (KEEP SECRET).")
        print(f"  Records:         {server.total_rows}")
        print(f"  Equality index:  {len(eq_index)} entries")
        print(f"  Range index:     {len(rng_index)} entries")

    elif args.mode == "query":
        key = bytes.fromhex(open("client_key.hex").read().strip())
        client = SSEClient(master_key=key)
        server = SSEServer()
        server.load(args.db_path)
        token = client.equality_token(args.col, args.val)
        t0 = time.time()
        results = server.query_equality(token, client)
        elapsed_ms = (time.time() - t0) * 1000
        print(f"Equality query col={args.col} val={args.val}: "
              f"{len(results)} encrypted rows in {elapsed_ms:.1f}ms")

    elif args.mode == "range":
        key = bytes.fromhex(open("client_key.hex").read().strip())
        client = SSEClient(master_key=key)
        server = SSEServer()
        server.load(args.db_path)
        tokens = client.range_tokens(args.col, args.lo, args.hi)
        t0 = time.time()
        results = server.query_range(tokens, client)
        elapsed_ms = (time.time() - t0) * 1000
        print(f"Range query col={args.col} [{args.lo}, {args.hi}]: "
              f"{len(results)} encrypted rows in {elapsed_ms:.1f}ms")

    elif args.mode == "count":
        key = bytes.fromhex(open("client_key.hex").read().strip())
        client = SSEClient(master_key=key)
        server = SSEServer()
        server.load(args.db_path)
        token = client.count_token(args.col, args.val)
        t0 = time.time()
        count = server.count_matching(token, client)
        elapsed_ms = (time.time() - t0) * 1000
        print(f"COUNT query col={args.col} val={args.val}: "
              f"{count} rows in {elapsed_ms:.1f}ms")

    elif args.mode == "bench":
        run_benchmark(args.db_path, n_queries=args.n_queries)


if __name__ == "__main__":
    main()
