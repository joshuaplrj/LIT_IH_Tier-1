# CryptoPuzzle — Quick Start

## Objective
Cryptanalyze the "FalconShield" protocol — a hybrid scheme combining a custom LWE key exchange (n=256, q=3329, σ=2.0) with a custom 12-round block cipher — to find at least one exploitable vulnerability, decrypt as many of the 100 provided ciphertexts as possible, and produce a security assessment report.

## Inputs
- `falconshield_spec.pdf` — 15-page protocol specification
- `reference_impl.py` — FalconShield reference implementation in Python
- `ciphertexts.json` — 100 ciphertexts, each with the corresponding public key (format below)
- `known_pairs.json` — 10 plaintext/ciphertext/pubkey tuples (known-plaintext oracle)
- Encryption oracle available at: `http://localhost:9000/encrypt` (POST `{"plaintext": "<hex>"}`, max 100 queries)

```json
// ciphertexts.json format
{
  "items": [
    {
      "id": 0,
      "public_key": {"A": [[...]], "b": [...]},
      "ciphertext": {"u": [...], "v": [...], "c": "<hex>", "mac": "<hex>"}
    }
  ]
}
```

## Expected Output
Two files:

**`submission.json`** — decryption results:
```json
{
  "decryptions": [
    {"id": 0, "plaintext_hex": "...", "key_hex": "..."}
  ],
  "vulnerabilities": [
    {"component": "LWE | BlockCipher | MAC", "description": "...", "severity": "Critical | High | Medium"}
  ]
}
```

**`report.md`** — security assessment with sections:
```
## Executive Summary
## Key Exchange Analysis
## Block Cipher Analysis
## MAC Analysis
## Vulnerabilities Found
## Proposed Fixes
```

## Recommended First Steps
1. Read `reference_impl.py` top-to-bottom and annotate every cryptographic operation; identify which LWE parameters (n, q, σ) are used and compare against NIST PQC recommendations (n should be >= 512 for 128-bit security).
2. Check the 10 known-plaintext pairs for patterns in the key encapsulation output (`u`, `v`) — if the noise σ=2.0 is small relative to q/4, a simple rounding attack may recover the shared secret.
3. Examine the block cipher round structure in `reference_impl.py`: look for non-bijective S-boxes, reused subkeys, or a missing key schedule; small block size anomalies or ECB-like mode usage make differential/linear cryptanalysis feasible in 3 hours.

## Scoring Breakdown
| Metric                         | Weight |
|--------------------------------|--------|
| Vulnerability identification   | 40%    |
| Ciphertexts decrypted          | 40%    |
| Security assessment write-up   | 20%    |

## Common Pitfalls
- Do not spend all 3 hours on the block cipher if the LWE parameters are obviously weak — the noise σ=2.0 with q=3329 gives a very tight noise-to-modulus ratio that may be directly exploitable with BKZ lattice reduction.
- The 100-query oracle limit is easy to exhaust; plan queries strategically — chosen-ciphertext pairs that differ by one bit are more informative than random plaintexts.
- The MAC (HMAC-SHA256) is almost certainly sound unless it is being applied incorrectly (e.g., MAC-then-encrypt, truncation, or IV reuse); check the order of operations in the spec before spending time on it.
