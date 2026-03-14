#!/usr/bin/env python3
"""
CYBER-P3: CryptoPuzzle — FalconShield Cryptanalysis Starter
Hackathon starter skeleton. Fill in all TODO sections.
Usage: python starter.py --ciphertexts ciphertexts.json --known known_pairs.json
                         --impl reference_impl.py --output submission.json
"""

import argparse
import json
import os
import sys
import hashlib
import hmac
import struct
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

# ---------------------------------------------------------------------------
# Optional dependency imports
# Install with: pip install fpylll numpy  OR use SageMath environment
# ---------------------------------------------------------------------------
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("[WARN] numpy not installed — LWE matrix operations will be slow.", file=sys.stderr)

try:
    from fpylll import IntegerMatrix, LLL, BKZ
    HAS_FPYLLL = True
except ImportError:
    HAS_FPYLLL = False
    print("[WARN] fpylll not installed. LWE lattice attack disabled. Run: pip install fpylll",
          file=sys.stderr)

# ---------------------------------------------------------------------------
# Constants — update to match reference_impl.py after reading the spec
# ---------------------------------------------------------------------------
LWE_N   = 256     # LWE dimension
LWE_Q   = 3329    # LWE modulus (matches Kyber-512 prime)
LWE_SIGMA = 2.0   # Noise standard deviation

ORACLE_URL       = "http://localhost:9000/encrypt"
ORACLE_MAX_QUERIES = 100

BLOCK_CIPHER_ROUNDS   = 12
BLOCK_CIPHER_KEY_BITS = 128
BLOCK_CIPHER_BLOCK_BITS = 256


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_ciphertexts(path: str) -> List[Dict]:
    """Load ciphertexts.json and return the list of items."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])


def load_known_pairs(path: str) -> List[Dict]:
    """Load known_pairs.json — list of {id, plaintext_hex, ciphertext, public_key}."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reference_impl(path: str) -> str:
    """Read reference_impl.py source code for manual analysis."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Encryption oracle
# ---------------------------------------------------------------------------

oracle_query_count = 0

def oracle_encrypt(plaintext_hex: str) -> Optional[Dict]:
    """
    Query the encryption oracle with a hex-encoded plaintext.
    Returns the ciphertext dict or None on error.
    Enforces the 100-query budget.
    """
    global oracle_query_count
    if oracle_query_count >= ORACLE_MAX_QUERIES:
        print("[WARN] Oracle query budget exhausted (100 queries).", file=sys.stderr)
        return None

    payload = json.dumps({"plaintext": plaintext_hex}).encode("utf-8")
    req = urllib.request.Request(
        ORACLE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            oracle_query_count += 1
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[ERROR] Oracle query failed: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# LWE Key Exchange Analysis
# ---------------------------------------------------------------------------

def lwe_matrix_from_pubkey(pubkey: Dict) -> Tuple[Any, Any]:
    """
    Extract LWE matrix A (n x n) and vector b (n,) from public key dict.
    Returns (A_list, b_list) as Python lists of ints.
    """
    # TODO: parse pubkey["A"] as n x n integer matrix
    # TODO: parse pubkey["b"] as n-element integer vector
    # TODO: return (A, b)
    pass


def attempt_lwe_lattice_attack(pubkey: Dict) -> Optional[List[int]]:
    """
    Attempt to recover LWE secret vector s from public key using BKZ lattice reduction.
    Returns s as a list of ints mod q, or None if fpylll is unavailable or attack fails.

    The LWE instance: b = A*s + e (mod q)
    where s, e are short vectors with entries from a discrete Gaussian N(0, sigma^2).

    Strategy: embed the LWE instance in a q-ary lattice and run BKZ-20.
    """
    if not HAS_FPYLLL:
        print("[WARN] fpylll not available — skipping lattice attack.", file=sys.stderr)
        return None

    A, b = lwe_matrix_from_pubkey(pubkey)
    n = LWE_N

    # TODO: build the embedding lattice basis matrix of dimension (2n+1) x (2n+1)
    #       Standard embedding: rows are [ q*e_i | 0 | 0 ] for i in 0..n-1
    #                                    [ A^T   | I | 0 ]
    #                                    [ b^T   | 0 | 1 ]
    #       where I is the n x n identity and e_i are standard basis vectors.
    # TODO: create IntegerMatrix from the basis
    # TODO: run BKZ.reduction(M, BKZ.Param(block_size=20))
    # TODO: search the reduced basis rows for a vector of the form (e | s | 1)
    #       by checking that the first n components have small absolute values (< 3*sigma)
    # TODO: extract and return s = row[n:2n] mod q if found
    pass


def recover_shared_secret(u: List[int], v: int, s: List[int]) -> bytes:
    """
    Given LWE ciphertext components u (n-vector) and v (scalar),
    and recovered secret s, compute the shared secret k.

    Decapsulation: w = v - dot(u, s) mod q
                   k = round(w / (q // 2)) mod 2  (for 1-bit key)
    For multi-bit keys, treat v as a vector and apply component-wise.
    """
    # TODO: compute w = (v - sum(u[i]*s[i] for i in range(n))) % LWE_Q
    # TODO: k_bit = 1 if w > LWE_Q // 4 and w < 3 * LWE_Q // 4 else 0
    # TODO: expand k_bit(s) to a 16-byte (128-bit) symmetric key via HKDF or SHA-256
    # TODO: return key bytes
    pass


# ---------------------------------------------------------------------------
# Block Cipher Analysis
# ---------------------------------------------------------------------------

def analyse_sbox(sbox: List[int]) -> Dict:
    """
    Analyse an 8-bit S-box (list of 256 ints) for cryptographic properties.
    Returns dict with keys: is_bijective, max_differential_prob, max_linear_bias.
    """
    result = {}

    # TODO: check bijectivity — sorted(sbox) == list(range(256))
    # TODO: compute difference distribution table (DDT):
    #       DDT[a][b] = count of x where sbox[x^a] ^ sbox[x] == b
    #       max_differential_prob = max(DDT[a][b] for a!=0) / 256
    # TODO: compute linear approximation table (LAT):
    #       LAT[a][b] = |count of x where popcount(x & a) ^ popcount(sbox[x] & b) == 0| - 128
    #       max_linear_bias = max(|LAT[a][b]|) / 256
    pass


def chosen_plaintext_attack_block_cipher(num_queries: int = 50) -> Optional[bytes]:
    """
    Use the encryption oracle to collect chosen-plaintext pairs for differential
    or linear cryptanalysis of the custom block cipher.
    Returns the recovered last-round subkey bytes, or None.
    """
    # TODO: craft pairs of plaintexts (P, P ^ delta) for various deltas
    # TODO: query oracle_encrypt for each
    # TODO: observe ciphertext differences and build difference distribution
    # TODO: use statistical analysis to recover last-round subkey
    # TODO: return recovered_subkey or None
    pass


# ---------------------------------------------------------------------------
# Decryption pipeline
# ---------------------------------------------------------------------------

def decrypt_with_key(ciphertext_hex: str, key: bytes) -> Optional[str]:
    """
    Decrypt a ciphertext (hex string) using the recovered symmetric key.
    Uses the FalconShield block cipher (from reference_impl.py — import or re-implement).
    Returns plaintext as hex string, or None on failure.
    """
    # TODO: import or re-implement the FalconShield block cipher decrypt function
    # TODO: apply key schedule to expand key
    # TODO: split ciphertext into blocks; decrypt each block
    # TODO: strip PKCS#7 padding
    # TODO: return plaintext.hex()
    pass


def try_decrypt_item(item: Dict, known_secrets: Dict[int, bytes]) -> Tuple[str, str]:
    """
    Attempt to decrypt a single ciphertext item.
    Returns (plaintext_hex, key_hex) — both empty string if decryption fails.
    """
    item_id = item["id"]
    pubkey  = item["public_key"]
    ct      = item["ciphertext"]

    # Strategy 1: check if we already have the shared secret from a prior key recovery
    if item_id in known_secrets:
        key = known_secrets[item_id]
    else:
        # Strategy 2: attempt LWE lattice attack to recover s, then shared secret
        s = attempt_lwe_lattice_attack(pubkey)
        if s is not None:
            key = recover_shared_secret(ct.get("u", []), ct.get("v", 0), s)
        else:
            return ("", "")

    # Decrypt the block cipher layer
    plaintext_hex = decrypt_with_key(ct.get("c", ""), key)
    if plaintext_hex is None:
        return ("", "")

    return (plaintext_hex, key.hex())


# ---------------------------------------------------------------------------
# Vulnerability catalogue
# ---------------------------------------------------------------------------

def build_vulnerability_report(sbox_analysis: Optional[Dict]) -> List[Dict]:
    """
    Construct the list of found vulnerabilities based on analysis results.
    Fill in after completing your cryptanalysis.
    """
    vulns = []

    # TODO: if LWE_N < 512 add LWE parameter weakness entry
    # TODO: if sbox_analysis and not sbox_analysis["is_bijective"] add S-box entry
    # TODO: if max_differential_prob > 1/64 add differential weakness entry
    # TODO: add MAC composition issue if observed (e.g. MAC not covering u)
    # TODO: Each entry: {"component": "...", "description": "...", "severity": "..."}

    return vulns


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CYBER-P3 CryptoPuzzle — FalconShield Cryptanalysis"
    )
    parser.add_argument("--ciphertexts", required=True,
                        help="Path to ciphertexts.json")
    parser.add_argument("--known",       required=True,
                        help="Path to known_pairs.json")
    parser.add_argument("--impl",        required=True,
                        help="Path to reference_impl.py")
    parser.add_argument("--output",      default="submission.json",
                        help="Path for output submission JSON")
    parser.add_argument("--report",      default="report.md",
                        help="Path for output security assessment report")
    args = parser.parse_args()

    for path in (args.ciphertexts, args.known, args.impl):
        if not os.path.isfile(path):
            print(f"[ERROR] File not found: {path}", file=sys.stderr)
            sys.exit(1)

    print("[*] Loading inputs...")
    ciphertexts  = load_ciphertexts(args.ciphertexts)
    known_pairs  = load_known_pairs(args.known)
    impl_source  = load_reference_impl(args.impl)
    print(f"    {len(ciphertexts)} ciphertexts, {len(known_pairs)} known-plaintext pairs loaded.")
    print(f"    Reference implementation: {len(impl_source)} characters.")

    # Step 1 — Analyse known pairs to build a picture of the key exchange
    print("[*] Analysing known plaintext-ciphertext pairs for LWE patterns...")
    known_secrets: Dict[int, bytes] = {}
    for pair in known_pairs:
        # TODO: use known plaintext to reverse-engineer shared secret from ciphertext
        pass

    # Step 2 — Attempt block cipher S-box analysis (read S-box from impl source or file)
    print("[*] Analysing block cipher S-box...")
    sbox: Optional[List[int]] = None
    # TODO: extract sbox list from impl_source via regex or exec() in sandbox
    sbox_analysis = analyse_sbox(sbox) if sbox else None

    # Step 3 — Attempt chosen-plaintext block cipher attack with oracle
    print("[*] Running chosen-plaintext block cipher analysis (oracle queries)...")
    last_round_key = chosen_plaintext_attack_block_cipher(num_queries=40)

    # Step 4 — Decrypt all 100 ciphertexts
    print("[*] Attempting decryption of all ciphertexts...")
    decryptions = []
    for item in ciphertexts:
        pt_hex, key_hex = try_decrypt_item(item, known_secrets)
        if pt_hex:
            print(f"    [+] Decrypted item {item['id']}: {pt_hex[:32]}...")
        decryptions.append({
            "id":            item["id"],
            "plaintext_hex": pt_hex,
            "key_hex":       key_hex,
        })

    # Step 5 — Build vulnerability list
    vulns = build_vulnerability_report(sbox_analysis)
    print(f"[*] Vulnerabilities identified: {len(vulns)}")

    # Step 6 — Write submission.json
    submission = {"decryptions": decryptions, "vulnerabilities": vulns}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2)
    print(f"[*] Submission written to: {args.output}")

    # Step 7 — Write security assessment report skeleton
    report_template = f"""# FalconShield Security Assessment Report

## Executive Summary

FalconShield was evaluated against {len(ciphertexts)} ciphertexts.
<!-- TODO: summarise key findings in 3-5 sentences -->

## Key Exchange Analysis (LWE n={LWE_N}, q={LWE_Q}, sigma={LWE_SIGMA})

**Security rating:** <!-- TODO: X / 10 -->

<!-- TODO: analyse parameter choices against NIST PQC benchmarks -->
<!-- TODO: describe the lattice attack result -->

## Block Cipher Analysis (12 rounds, 128-bit key, 256-bit block)

**Security rating:** <!-- TODO: X / 10 -->

<!-- TODO: describe S-box properties from analyse_sbox() output -->
<!-- TODO: describe differential/linear cryptanalysis findings -->

## MAC Analysis (HMAC-SHA256)

**Security rating:** <!-- TODO: X / 10 -->

<!-- TODO: describe MAC input coverage, truncation, composition order -->

## Vulnerabilities Found

<!-- TODO: paste from submission.json vulnerabilities list -->

## Proposed Fixes

<!-- TODO: one concrete fix per vulnerability with specific parameter values -->
"""
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report_template)
    print(f"[*] Report skeleton written to: {args.report}")

    decrypted_count = sum(1 for d in decryptions if d["plaintext_hex"])
    print(f"\n[*] Summary: {decrypted_count}/{len(ciphertexts)} ciphertexts decrypted, "
          f"{len(vulns)} vulnerabilities found, "
          f"{oracle_query_count} oracle queries used.")


if __name__ == "__main__":
    main()
