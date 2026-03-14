# CryptoPuzzle — Hints

> Each tier costs score points. Only request a hint when you are genuinely stuck.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

Custom cryptographic protocols almost always fail for one of three reasons: the parameters are too small (making a theoretical attack practical), the algorithm is structurally flawed (missing properties that a standard primitive would provide), or it is implemented correctly but composed incorrectly (e.g., the MAC does not cover all ciphertext components). Start by reading the specification looking for *parameter choices* that deviate from known-good values, *structural shortcuts* in the cipher design (fewer rounds, smaller block, reused constants), and *API misuse* in how the components are combined. You do not need a novel attack — you need to find where FalconShield diverges from secure practice and exploit that deviation.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**LWE Key Exchange Weakness:**
With n=256, q=3329, σ=2.0, the noise-to-modulus ratio σ/q ≈ 0.0006. This is well below the threshold needed to resist lattice attacks. Use **BKZ (Block Korkine-Zolotarev)** lattice basis reduction — available via the `fpylll` or `sage` libraries — to recover the secret key `s` from public key `(A, b = A*s + e)`. With n=256 this is feasible in under an hour on a laptop. Once `s` is recovered, compute the shared secret `K = round(v - u*s, q/4)` for each ciphertext.

**Block Cipher Weakness:**
Inspect whether the S-box in the reference implementation is a permutation over all 256 byte values (bijective). A non-bijective S-box immediately breaks confusion. Check for linear approximations: if any S-box output bit is XOR-correlated with any subset of input bits with probability > 0.5 + 2^-4, **linear cryptanalysis** with ~2^8 known plaintexts is feasible. If the diffusion layer (P-box or MDS matrix) does not achieve full avalanche in 2–3 rounds, **differential cryptanalysis** on a reduced-round version will identify the last-round subkey.

**MAC Weakness:**
Check whether HMAC-SHA256 is applied to the ciphertext bytes *after* encryption (Encrypt-then-MAC is secure) or to the plaintext *before* encryption (MAC-then-Encrypt is malleable). If the MAC tag is truncated below 96 bits, a forgery attack via birthday bound may be feasible. Also check: is `u` included in the MAC input? If not, an attacker can swap `u` without invalidating the MAC (a key-recovery-enables decryption attack).

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Step 1 — Recover LWE secret key with fpylll:**
```python
# pip install fpylll  (or use SageMath)
from fpylll import IntegerMatrix, LLL, BKZ
# Build lattice basis from public key matrix A and vector b
# Embed: M = [[q*I | 0], [A^T | I], [b^T | s^T]]
# Run BKZ-20 on M; shortest vector reveals s
```
Alternatively, use SageMath's `sage.crypto.lwe` module or directly call `BKZ.reduction(M, BKZ.Param(block_size=20))`.

**Step 2 — Decrypt ciphertexts once s is known:**
Given LWE secret `s`, for each ciphertext `(u, v, c, mac)`:
1. Compute `w = v - dot(u, s) mod q`
2. Round `w` to the nearest multiple of `q//2` then divide by `q//2` to get the 1-bit (or k-bit) shared secret `K_bits`
3. Expand `K_bits` into a 128-bit AES key (or into the custom block cipher key schedule)
4. Decrypt `c` using the recovered key

**Step 3 — Attack the block cipher if LWE fails:**
```python
# Collect chosen plaintext pairs (P, P^delta) where delta = single-bit flip
# Encrypt both with the oracle; observe difference in ciphertext
# Track which delta values produce a predictable ciphertext difference
# This differential characteristic lets you peel the last round's subkey
# with only ~2^10 chosen-plaintext queries
```

**Step 4 — Write submission.json:**
```python
import json
results = []
for item in ciphertexts["items"]:
    pt_hex = attempt_decrypt(item, recovered_secret_key)
    results.append({"id": item["id"], "plaintext_hex": pt_hex, "key_hex": key_hex})
json.dump({"decryptions": results, "vulnerabilities": [...]}, open("submission.json","w"), indent=2)
```

**Step 5 — Security assessment report structure:**
- State the specific parameter or structural flaw (with line numbers in `reference_impl.py`)
- Classify severity: Critical (breaks all ciphertexts), High (breaks key exchange for some keys), Medium (theoretical attack requiring > 2^64 operations)
- For each component rate it 1–10 and explain the rating
- Propose a concrete fix (e.g., "increase n to 768, σ to 3.19 per CRYSTALS-Kyber-768")
