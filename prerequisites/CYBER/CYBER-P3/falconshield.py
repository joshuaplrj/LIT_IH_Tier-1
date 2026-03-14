#!/usr/bin/env python3
"""
FalconShield Reference Implementation
=====================================
A custom post-quantum-inspired authenticated encryption protocol.

WARNING: This is a RESEARCH/EDUCATIONAL implementation with known weaknesses.
Do NOT use in production.

Protocol overview:
  1. Key Exchange: LWE-based key encapsulation (n=64, q=3329, sigma=0.5)
  2. Block Cipher: 12-round custom cipher (128-bit key, 256-bit block)
  3. MAC: HMAC-SHA256

Known Parameters:
  n     = 64     (LWE dimension)
  q     = 3329   (LWE modulus)
  sigma = 0.5    (error distribution std dev)
  block_size = 32 bytes (256 bits)
  key_size   = 16 bytes (128 bits)
  rounds     = 12
"""
import struct
import random
import hashlib
import hmac

# ── LWE Parameters ──────────────────────────────────────────────────────────
N     = 64
Q     = 3329
SIGMA = 0.5   # Intentionally small: makes lattice attacks feasible

# ── Cipher Parameters ────────────────────────────────────────────────────────
BLOCK_SIZE = 32   # 256-bit block
KEY_SIZE   = 16   # 128-bit key
NUM_ROUNDS = 12

# ── S-Box: F(x) = (3x + 7) mod 256 ─────────────────────────────────────────
# NOTE: This S-Box is AFFINE (linear). It provides NO confusion.
SBOX     = [(3 * x + 7) % 256 for x in range(256)]
INV_SBOX = [0] * 256
for _x in range(256):
    INV_SBOX[SBOX[_x]] = _x


def shift_rows(block: bytes) -> bytes:
    """Treat 32-byte block as 4x8 matrix; shift row i left by i positions."""
    b = bytearray(block)
    rows = [b[i*8:(i+1)*8] for i in range(4)]
    out = bytearray(32)
    for r in range(4):
        for c in range(8):
            out[r*8 + c] = rows[r][(c + r) % 8]
    return bytes(out)


def inv_shift_rows(block: bytes) -> bytes:
    b = bytearray(block)
    rows = [b[i*8:(i+1)*8] for i in range(4)]
    out = bytearray(32)
    for r in range(4):
        for c in range(8):
            out[r*8 + c] = rows[r][(c - r) % 8]
    return bytes(out)


def key_schedule(key: bytes):
    """Weak key schedule: round_key[i] = round_key[i-1] XOR rotate_left_8(round_key[i-1])"""
    rk = [bytearray(key)]
    for i in range(1, NUM_ROUNDS + 1):
        prev = rk[i-1]
        rot  = prev[1:] + prev[:1]
        rk.append(bytearray(p ^ r for p, r in zip(prev, rot)))
    return rk


def _expand_rk(rk16: bytes, size: int = BLOCK_SIZE) -> bytes:
    return bytes(rk16[i % KEY_SIZE] for i in range(size))


class FalconCipher:
    """12-round block cipher with 256-bit block and 128-bit key."""

    @staticmethod
    def encrypt(key: bytes, plaintext: bytes) -> bytes:
        """Encrypt plaintext (arbitrary length). Returns IV + ciphertext."""
        assert len(key) == KEY_SIZE, f"Key must be {KEY_SIZE} bytes"
        iv  = hashlib.sha256(key + plaintext[:8]).digest()[:16]
        rk  = key_schedule(key)
        pad = BLOCK_SIZE - len(plaintext) % BLOCK_SIZE
        pt  = plaintext + bytes([pad] * pad)
        ct_blocks = []
        prev = iv + iv   # 32-byte CBC state
        for i in range(0, len(pt), BLOCK_SIZE):
            blk   = bytes(pt[i+j] ^ prev[j] for j in range(BLOCK_SIZE))
            state = blk
            for r in range(NUM_ROUNDS):
                state = bytes(SBOX[b] for b in state)          # SubBytes
                state = shift_rows(state)                       # ShiftRows
                rke   = _expand_rk(rk[r])
                state = bytes(state[j] ^ rke[j] for j in range(BLOCK_SIZE))  # AddRoundKey
            ct_blocks.append(state)
            prev = state
        return iv + b"".join(ct_blocks)

    @staticmethod
    def decrypt(key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt. ciphertext = IV(16) + encrypted_blocks."""
        assert len(key) == KEY_SIZE
        iv  = ciphertext[:16]
        rk  = key_schedule(key)
        ct  = ciphertext[16:]
        prev = iv + iv
        pt_blocks = []
        for i in range(0, len(ct), BLOCK_SIZE):
            blk   = ct[i:i+BLOCK_SIZE]
            state = blk
            for r in range(NUM_ROUNDS - 1, -1, -1):
                rke   = _expand_rk(rk[r])
                state = bytes(state[j] ^ rke[j] for j in range(BLOCK_SIZE))
                state = inv_shift_rows(state)
                state = bytes(INV_SBOX[b] for b in state)
            pt_blocks.append(bytes(state[j] ^ prev[j] for j in range(BLOCK_SIZE)))
            prev = blk
        pt_padded = b"".join(pt_blocks)
        pad = pt_padded[-1]
        return pt_padded[:-pad]


class LWEKeyExchange:
    """
    LWE-based Key Encapsulation Mechanism.

    Security Note: sigma=0.5 is CRITICALLY WEAK.
    Real LWE schemes (Kyber, NTRU) use sigma >= 1.0.
    With sigma=0.5, the noise is so small that the secret can be recovered
    via lattice reduction (BKZ algorithm) with modest computational effort.
    """

    def __init__(self, n: int = N, q: int = Q, sigma: float = SIGMA, seed=None):
        self.n     = n
        self.q     = q
        self.sigma = sigma
        self._rng  = random.Random(seed)

    def _gaussian_noise(self):
        import math
        noise = []
        for _ in range(self.n):
            u1 = self._rng.random() + 1e-15
            u2 = self._rng.random()
            z  = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
            noise.append(int(round(z * self.sigma)) % self.q)
        return noise

    def _rand_vec(self):
        return [self._rng.randint(0, self.q - 1) for _ in range(self.n)]

    def _rand_matrix(self):
        return [[self._rng.randint(0, self.q - 1) for _ in range(self.n)]
                for _ in range(self.n)]

    @staticmethod
    def _mv_mod(A, v, q):
        n = len(A)
        return [sum(A[i][j] * v[j] for j in range(n)) % q for i in range(n)]

    def _pack(self, vec):
        return struct.pack(f"<{len(vec)}H", *[v % self.q for v in vec])

    def _unpack(self, data, length):
        return list(struct.unpack(f"<{length}H", data[:length*2]))

    def _pack_mat(self, mat):
        flat = [mat[i][j] % self.q for i in range(self.n) for j in range(self.n)]
        return struct.pack(f"<{self.n*self.n}H", *flat)

    def _unpack_mat(self, data):
        flat = list(struct.unpack(f"<{self.n*self.n}H", data[:self.n*self.n*2]))
        return [[flat[i*self.n+j] for j in range(self.n)] for i in range(self.n)]

    def keygen(self):
        """Returns (pk_bytes, sk_bytes).
        pk = (A matrix, b vector) packed as bytes
        sk = s vector packed as bytes
        Vulnerability: s entries in [-2,2] combined with small sigma makes
                       error too small relative to signal — easy to distinguish.
        """
        A = self._rand_matrix()
        s = [self._rng.randint(-2, 2) for _ in range(self.n)]
        e = self._gaussian_noise()
        b = [(sum(A[i][j]*s[j] for j in range(self.n)) + e[i]) % self.q
             for i in range(self.n)]
        pk = self._pack_mat(A) + self._pack(b)
        sk = self._pack([v % self.q for v in s])
        return pk, sk

    def encapsulate(self, pk_bytes):
        """Returns (ciphertext_bytes, shared_secret_bytes)."""
        mat_sz = self.n * self.n * 2
        A = self._unpack_mat(pk_bytes[:mat_sz])
        b = self._unpack(pk_bytes[mat_sz:], self.n)

        r  = [self._rng.randint(-2, 2) for _ in range(self.n)]
        e1 = self._gaussian_noise()
        e2 = self._rng.randint(0, self.q // 4)

        # u = A^T r + e1
        u = [(sum(A[j][i]*r[j] for j in range(self.n)) + e1[i]) % self.q
             for i in range(self.n)]
        # v = b^T r + e2 + floor(q/2)
        v = (sum(b[i]*r[i] for i in range(self.n)) + e2 + self.q // 2) % self.q

        raw    = self._pack(u) + struct.pack("<H", v)
        secret = hashlib.sha256(raw).digest()
        return raw, secret

    def decapsulate(self, sk_bytes, ciphertext):
        """Returns shared_secret_bytes."""
        s = self._unpack(sk_bytes, self.n)
        s = [v if v < self.q//2 else v - self.q for v in s]
        u = self._unpack(ciphertext, self.n)
        v = struct.unpack("<H", ciphertext[self.n*2:self.n*2+2])[0]
        secret = hashlib.sha256(ciphertext).digest()
        return secret


class FalconShield:
    """Full FalconShield protocol: LWE-KEM + FalconCipher + HMAC-SHA256."""

    def __init__(self, seed=None):
        self.lwe = LWEKeyExchange(seed=seed)

    def encrypt(self, pk_bytes: bytes, message_256bytes: bytes):
        """Encrypt 256-byte message. Returns (ct_file_bytes, shared_secret)."""
        assert len(message_256bytes) == 256
        lwe_ct, ss = self.lwe.encapsulate(pk_bytes)
        ck = ss[:KEY_SIZE]
        mk = ss[KEY_SIZE:]
        enc = FalconCipher.encrypt(ck, message_256bytes)
        tag = hmac.new(mk, enc, hashlib.sha256).digest()
        ct_file = struct.pack("<H", len(lwe_ct)) + lwe_ct + enc + tag
        return ct_file, ss

    def decrypt(self, sk_bytes: bytes, ct_file_bytes: bytes):
        """Decrypt. Returns 256-byte message."""
        llen    = struct.unpack("<H", ct_file_bytes[:2])[0]
        lwe_ct  = ct_file_bytes[2:2+llen]
        rest    = ct_file_bytes[2+llen:]
        enc, tag = rest[:-32], rest[-32:]
        ss = self.lwe.decapsulate(sk_bytes, lwe_ct)
        ck = ss[:KEY_SIZE]
        mk = ss[KEY_SIZE:]
        if not hmac.compare_digest(hmac.new(mk, enc, hashlib.sha256).digest(), tag):
            raise ValueError("Authentication failed")
        return FalconCipher.decrypt(ck, enc)


if __name__ == "__main__":
    print("FalconShield self-test...")
    lwe  = LWEKeyExchange(seed=42)
    pk, sk = lwe.keygen()
    print(f"  Public key size: {len(pk)} bytes")
    print(f"  Secret key size: {len(sk)} bytes")

    ct, ss1 = lwe.encapsulate(pk)
    ss2     = lwe.decapsulate(sk, ct)
    print(f"  Shared secrets match: {ss1 == ss2}")

    fs       = FalconShield(seed=42)
    fs.lwe   = lwe
    msg      = bytes(range(256))
    ct_file, _ = fs.encrypt(pk, msg)
    msg2    = fs.decrypt(sk, ct_file)
    print(f"  Plaintext round-trip: {msg == msg2}")
    print("Self-test complete.")
