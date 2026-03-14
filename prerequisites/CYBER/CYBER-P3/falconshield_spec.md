# FalconShield Protocol Specification v1.0

## 1. Overview

FalconShield is a post-quantum-inspired authenticated encryption protocol designed
for secure message exchange in adversarial environments. It combines a Learning With
Errors (LWE) key encapsulation mechanism with a custom block cipher and
HMAC-based authentication.

### 1.1 Goals
- Provide IND-CCA2 security under the LWE hardness assumption
- Offer authenticated encryption with associated data (AEAD) semantics
- Support 256-byte messages with 128-bit equivalent symmetric security

### 1.2 Non-Goals
- Key management infrastructure
- Certificate handling
- Forward secrecy (not provided)

---

## 2. Components

### 2.1 LWE Key Encapsulation (FalconKEM)

#### 2.1.1 Parameters

| Parameter | Value | Notes                              |
|-----------|-------|------------------------------------|
| n         | 64    | LWE dimension                      |
| q         | 3329  | Modulus (prime)                    |
| σ         | 0.5   | Error distribution std dev         |
| Secret    | [-2,2]| Component range for secret key s   |

#### 2.1.2 Key Generation

1. Sample uniformly random matrix **A** ∈ ℤ_q^{n×n}
2. Sample secret **s** ∈ {-2,-1,0,1,2}^n
3. Sample error **e** ← D_{σ} (discrete Gaussian, σ=0.5)
4. Compute **b** = **A·s** + **e** mod q
5. Public key: pk = (**A**, **b**)
6. Secret key: sk = **s**

**Storage format**: A packed as n² little-endian uint16, b packed as n uint16.

#### 2.1.3 Encapsulation

1. Sample ephemeral **r** ∈ {-2,-1,0,1,2}^n
2. Sample errors e₁ ← D_{σ}, e₂ ← Uniform[0, q/4]
3. Compute **u** = **A**ᵀ·**r** + **e₁** mod q
4. Compute v = **b**ᵀ·**r** + e₂ + ⌊q/2⌋ mod q
5. Shared secret K = SHA-256(pack(**u**) ‖ pack(v))
6. Ciphertext: ct = pack(**u**) ‖ pack(v)

#### 2.1.4 Decapsulation

1. Compute m' = v − **s**ᵀ·**u** mod q
2. Recover K = SHA-256(ct)

#### 2.1.5 Security Analysis

The security of FalconKEM relies on the hardness of the Decision-LWE problem.
With q=3329 and σ=0.5, the noise-to-signal ratio is approximately 0.5/3329 ≈ 0.00015.
This is substantially below the recommended threshold (σ/q ≥ 0.01 for n=64),
making the scheme vulnerable to BKZ lattice reduction attacks.

An attacker can:
1. Recover **s** from (A, b) using BKZ-20 or higher
2. Compute the same shared secret K as the legitimate party
3. Decrypt all past and future messages

---

### 2.2 FalconCipher Block Cipher

#### 2.2.1 Parameters

| Parameter  | Value | Notes            |
|------------|-------|------------------|
| Block size | 256   | bits (32 bytes)  |
| Key size   | 128   | bits (16 bytes)  |
| Rounds     | 12    |                  |
| Mode       | CBC   | with random IV   |

#### 2.2.2 S-Box

FalconCipher uses an affine substitution:

    SBOX(x) = (3·x + 7) mod 256

**This is a linear operation.** Linear S-boxes eliminate the confusion property
required for security, enabling linear cryptanalysis with a single known
plaintext-ciphertext pair.

#### 2.2.3 Round Function

Each of the 12 rounds applies:

1. **SubBytes**: Apply SBOX to each byte independently
2. **ShiftRows**: Treat 32-byte block as 4×8 matrix; shift row i by i positions
3. **AddRoundKey**: XOR with expanded round key

#### 2.2.4 Key Schedule

    RK[0] = master_key
    RK[i] = RK[i-1] XOR RotLeft8(RK[i-1])   for i = 1..12

where RotLeft8 rotates the 16-byte array left by 1 byte.

**Weakness**: Round keys are derived from a single 16-byte state with a linear
recurrence. The key space collapses: given one round key, all others are determined.
Furthermore, with a linear S-box, the entire cipher is an affine function of the key.

#### 2.2.5 CBC Mode

- IV: 16 random bytes
- Chaining block (32 bytes): IV ‖ IV
- Standard CBC encryption/decryption

---

### 2.3 Authentication (HMAC-SHA256)

The MAC is computed as:

    tag = HMAC-SHA256(mac_key, ciphertext)

where mac_key = K[16:32] (second half of the 32-byte shared secret).

The HMAC is correct and not intentionally weakened.

---

## 3. Wire Format

### 3.1 Ciphertext File Format

    ┌──────────────────────────────────────────┐
    │  2 bytes  │  LWE ciphertext length (LE)  │
    ├──────────────────────────────────────────┤
    │  variable │  LWE ciphertext bytes         │
    │           │  (u packed + v packed)        │
    ├──────────────────────────────────────────┤
    │  variable │  FalconCipher ciphertext      │
    │           │  IV(16) + encrypted blocks    │
    ├──────────────────────────────────────────┤
    │  32 bytes │  HMAC-SHA256 tag              │
    └──────────────────────────────────────────┘

### 3.2 LWE Ciphertext Format

    u: n × 2 bytes (little-endian uint16, mod q)
    v: 2 bytes (little-endian uint16)
    Total: (n+1) × 2 = 130 bytes for n=64

### 3.3 Public Key Format

    A: n² × 2 bytes (row-major, little-endian uint16, mod q)
    b: n × 2 bytes (little-endian uint16, mod q)
    Total: (n²+n) × 2 = 8320 bytes for n=64

---

## 4. Known Vulnerabilities (for educational purposes)

### Vulnerability 1: Weak LWE Noise (Critical)
**Location**: LWEKeyExchange, σ=0.5
**Impact**: Secret key recovery
**Attack**: BKZ lattice reduction on the LWE instance (A, b=As+e)
**Complexity**: ~2^40 operations for n=64, σ=0.5

### Vulnerability 2: Linear S-Box (Critical)
**Location**: FalconCipher, SBOX(x) = (3x+7) mod 256
**Impact**: Known-plaintext attack recovers cipher key
**Attack**: Linear cryptanalysis; with 1 known plaintext the entire
            system of equations is linear in the key bits

### Vulnerability 3: Weak Key Schedule (Moderate)
**Location**: FalconCipher.key_schedule
**Impact**: Related-key attacks; key recovery from partial round-key knowledge
**Attack**: Given any round key RK[i], solve RK[i-1] XOR RotLeft8(RK[i-1]) = RK[i]

---

## 5. Test Vectors

See `known_pairs.csv` for 10 plaintext/ciphertext/key-index triples.

---

*FalconShield v1.0 — For CTF/Educational Use Only*
