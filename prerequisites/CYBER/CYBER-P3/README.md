# CYBER-P3: CryptoPuzzle — FalconShield Protocol

## Overview
You have intercepted communications protected by the FalconShield v1.0 protocol,
a custom post-quantum-inspired authenticated encryption system. Your task is to
exploit weaknesses in the protocol to recover the plaintexts from 100 intercepted
ciphertext files.

## Objective
Decrypt as many of the 100 ciphertext files (`ct_000.bin` to `ct_099.bin`) as
possible. Each plaintext is 256 bytes. Submit plaintexts as hex strings.

## Files
| File/Directory              | Description                                   |
|-----------------------------|-----------------------------------------------|
| `falconshield_spec.md`      | 3-page protocol specification                 |
| `falconshield.py`           | Reference implementation                      |
| `ciphertexts/ct_NNN.bin`    | 100 ciphertext files (index 000–099)          |
| `public_keys/pk_NNN.bin`    | 100 public keys corresponding to ciphertexts  |
| `known_pairs.csv`           | 10 known plaintext/ciphertext pairs           |
| `HIDDEN_secret_keys/`       | **Hidden.** Secret keys for scoring.          |
| `HIDDEN_plaintexts.csv`     | **Hidden.** All plaintexts for scoring.       |
| `README.md`                 | This file                                     |

## Challenge Structure

### Phase 1 — Protocol Analysis (20 pts)
Read `falconshield_spec.md` and `falconshield.py`. Identify the intentional
vulnerabilities. Document each vulnerability with:
- Location in code/spec
- Attack vector
- Expected impact

### Phase 2 — Key Recovery (50 pts)
Exploit the identified vulnerabilities to recover secret keys from public keys.
Use `known_pairs.csv` to validate your attack before applying it to all 100 pairs.

### Phase 3 — Decryption (30 pts)
Decrypt all 100 ciphertexts using recovered keys. Submit as a CSV:
```
index,plaintext_hex
0,<256-byte plaintext as hex>
1,...
```

## Hints
- Examine the S-Box definition carefully. Is it truly non-linear?
- What does the key schedule's linearity imply about the cipher's security?
- For the LWE component, consider what happens when the error is very small
  relative to the modulus. What classical lattice algorithms might apply?
- `known_pairs.csv` gives you plaintext/ciphertext pairs — useful for validating attacks.

## Scoring
- Phase 1 (Analysis): up to 20 pts based on accuracy and completeness
- Phase 2 (Key recovery): 0.5 pts per recovered key (max 50 pts)
- Phase 3 (Decryption): 0.3 pts per correct plaintext (max 30 pts)
