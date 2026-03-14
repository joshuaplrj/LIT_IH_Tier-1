#!/usr/bin/env python3
"""
CYBER-P3: CryptoPuzzle — FalconShield Protocol
Generates reference implementation, ciphertexts, public keys, and known pairs.
"""

import os
import struct
import random
import csv
import hashlib
import hmac

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CYBER-P3")

def ensure_dirs():
    for d in ["ciphertexts", "public_keys", "HIDDEN_secret_keys"]:
        os.makedirs(os.path.join(OUTPUT_DIR, d), exist_ok=True)

# ─── numpy import ─────────────────────────────────────────────────────────────
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("[CYBER-P3] WARNING: numpy not available, using pure-Python fallback for LWE")

# ─── LWE Parameters ──────────────────────────────────────────────────────────
N = 64       # dimension
Q = 3329     # modulus (same as CRYSTALS-Kyber for authenticity)
SIGMA = 0.5  # INTENTIONALLY small noise std — vulnerability!

# ─── FalconShield Cipher Parameters ───────────────────────────────────────────
BLOCK_SIZE = 32   # 256 bits
KEY_SIZE   = 16   # 128 bits
NUM_ROUNDS = 12

# ─── Affine S-box: F(x) = (3x + 7) mod 256 — INTENTIONALLY LINEAR ────────────
SBOX = [(3 * x + 7) % 256 for x in range(256)]
INV_SBOX = [0] * 256
for x in range(256):
    INV_SBOX[SBOX[x]] = x

# ─── Shift-rows table for 32-byte (4x8) block ────────────────────────────────
def shift_rows(block):
    """Treat 32 bytes as 4 rows x 8 columns, shift each row left by row index."""
    b = bytearray(block)
    rows = [b[i*8:(i+1)*8] for i in range(4)]
    shifted = bytearray(32)
    for r in range(4):
        for c in range(8):
            shifted[r*8 + c] = rows[r][(c + r) % 8]
    return bytes(shifted)

def inv_shift_rows(block):
    b = bytearray(block)
    rows = [b[i*8:(i+1)*8] for i in range(4)]
    shifted = bytearray(32)
    for r in range(4):
        for c in range(8):
            shifted[r*8 + c] = rows[r][(c - r) % 8]
    return bytes(shifted)

# ─── Key Schedule ─────────────────────────────────────────────────────────────
def rotate_left_8(b_array):
    """Rotate a bytearray left by 1 byte (8 bits)."""
    return b_array[1:] + b_array[:1]

def key_schedule(key_bytes):
    """Produce NUM_ROUNDS+1 round keys from 16-byte master key."""
    assert len(key_bytes) == KEY_SIZE
    rk = [bytearray(key_bytes)]
    for i in range(1, NUM_ROUNDS + 1):
        prev = rk[i-1]
        rotated = rotate_left_8(prev)
        new_rk = bytearray(KEY_SIZE)
        for j in range(KEY_SIZE):
            new_rk[j] = prev[j] ^ rotated[j]
        rk.append(new_rk)
    return rk

def expand_round_key(rk_16, block_size=BLOCK_SIZE):
    """Tile a 16-byte round key to fill block_size bytes."""
    result = bytearray(block_size)
    for i in range(block_size):
        result[i] = rk_16[i % KEY_SIZE]
    return bytes(result)

# ─── FalconCipher ─────────────────────────────────────────────────────────────
class FalconCipher:
    @staticmethod
    def encrypt(key: bytes, plaintext: bytes) -> bytes:
        """Encrypt arbitrary-length plaintext. Returns IV(16) + ciphertext."""
        assert len(key) == KEY_SIZE
        rnd = random.Random(int.from_bytes(key[:4], 'big') ^ random.randint(0, 2**32-1))
        iv = bytes(rnd.randint(0, 255) for _ in range(16))
        rk = key_schedule(key)

        # Pad plaintext to multiple of BLOCK_SIZE
        pad_len = BLOCK_SIZE - (len(plaintext) % BLOCK_SIZE)
        padded = plaintext + bytes([pad_len] * pad_len)

        ciphertext_blocks = []
        prev_block = iv + iv  # 32-byte CBC chaining block from 16-byte IV

        for i in range(0, len(padded), BLOCK_SIZE):
            block = padded[i:i+BLOCK_SIZE]
            # XOR with previous ciphertext (CBC mode)
            xored = bytes(block[j] ^ prev_block[j] for j in range(BLOCK_SIZE))
            # Apply rounds
            state = xored
            for r in range(NUM_ROUNDS):
                # SubBytes (affine sbox)
                state = bytes(SBOX[b] for b in state)
                # ShiftRows
                state = shift_rows(state)
                # AddRoundKey
                rk_expanded = expand_round_key(rk[r])
                state = bytes(state[j] ^ rk_expanded[j] for j in range(BLOCK_SIZE))
            ciphertext_blocks.append(state)
            prev_block = state

        return iv + b"".join(ciphertext_blocks)

    @staticmethod
    def decrypt(key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt. ciphertext = IV(16) + encrypted_blocks."""
        assert len(key) == KEY_SIZE
        iv = ciphertext[:16]
        rk = key_schedule(key)
        ct_blocks = ciphertext[16:]

        prev_block = iv + iv  # same expansion as encrypt

        plaintext_blocks = []
        for i in range(0, len(ct_blocks), BLOCK_SIZE):
            block = ct_blocks[i:i+BLOCK_SIZE]
            state = block
            # Inverse rounds (reverse order)
            for r in range(NUM_ROUNDS - 1, -1, -1):
                # Inverse AddRoundKey
                rk_expanded = expand_round_key(rk[r])
                state = bytes(state[j] ^ rk_expanded[j] for j in range(BLOCK_SIZE))
                # Inverse ShiftRows
                state = inv_shift_rows(state)
                # Inverse SubBytes
                state = bytes(INV_SBOX[b] for b in state)
            # XOR with previous ciphertext (CBC)
            plain = bytes(state[j] ^ prev_block[j] for j in range(BLOCK_SIZE))
            plaintext_blocks.append(plain)
            prev_block = block

        plaintext_padded = b"".join(plaintext_blocks)
        # Remove padding
        pad_len = plaintext_padded[-1]
        return plaintext_padded[:-pad_len]


# ─── LWE Key Exchange ─────────────────────────────────────────────────────────
class LWEKeyExchange:
    def __init__(self, n=N, q=Q, sigma=SIGMA, seed=None):
        self.n = n
        self.q = q
        self.sigma = sigma
        self._rng = random.Random(seed)

    def _random_matrix(self):
        """Generate n×n matrix mod q."""
        if HAS_NUMPY:
            return np.array([[self._rng.randint(0, self.q - 1)
                              for _ in range(self.n)] for _ in range(self.n)], dtype=np.int64)
        else:
            return [[self._rng.randint(0, self.q - 1) for _ in range(self.n)]
                    for _ in range(self.n)]

    def _random_secret(self):
        """Secret key: vector of n small integers in [-2, 2]."""
        return [self._rng.randint(-2, 2) for _ in range(self.n)]

    def _gaussian_noise(self):
        """Small Gaussian noise with sigma=0.5 — intentionally weak."""
        import math
        result = []
        for _ in range(self.n):
            # Box-Muller
            u1 = self._rng.random() + 1e-12
            u2 = self._rng.random()
            z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
            result.append(int(round(z * self.sigma)) % self.q)
        return result

    def _mat_vec_mod(self, A, v):
        """Compute A*v mod q."""
        if HAS_NUMPY:
            v_arr = np.array(v, dtype=np.int64)
            if isinstance(A, list):
                A = np.array(A, dtype=np.int64)
            res = A.dot(v_arr) % self.q
            return res.tolist()
        else:
            n = len(A)
            result = []
            for i in range(n):
                s = sum(A[i][j] * v[j] for j in range(n)) % self.q
                result.append(s)
            return result

    def _pack_vector(self, vec):
        """Pack a list of integers (mod q) as bytes using 2 bytes per element."""
        return struct.pack(f"<{len(vec)}H", *[v % self.q for v in vec])

    def _unpack_vector(self, data, length):
        return list(struct.unpack(f"<{length}H", data[:length * 2]))

    def _pack_matrix(self, mat):
        """Pack n×n matrix as bytes."""
        if HAS_NUMPY:
            flat = (np.array(mat, dtype=np.int64) % self.q).flatten().tolist()
        else:
            flat = [mat[i][j] % self.q for i in range(self.n) for j in range(self.n)]
        return struct.pack(f"<{self.n*self.n}H", *flat)

    def _unpack_matrix(self, data):
        flat = list(struct.unpack(f"<{self.n*self.n}H", data[:self.n*self.n*2]))
        if HAS_NUMPY:
            return np.array(flat, dtype=np.int64).reshape(self.n, self.n)
        else:
            return [[flat[i*self.n + j] for j in range(self.n)] for i in range(self.n)]

    def keygen(self):
        """Generate (pk, sk) pair. pk=(A,b), sk=s."""
        A = self._random_matrix()
        s = self._random_secret()
        e = self._gaussian_noise()

        # b = A*s + e mod q
        As = self._mat_vec_mod(A, s)
        b = [(As[i] + e[i]) % self.q for i in range(self.n)]

        pk_bytes = self._pack_matrix(A) + self._pack_vector(b)
        sk_bytes = self._pack_vector([v % self.q for v in s])
        return pk_bytes, sk_bytes

    def encapsulate(self, pk_bytes):
        """Encapsulate: generate shared secret and ciphertext from public key."""
        mat_size = self.n * self.n * 2
        A = self._unpack_matrix(pk_bytes[:mat_size])
        b = self._unpack_vector(pk_bytes[mat_size:], self.n)

        # Ephemeral random vector r
        r = self._random_secret()
        e1 = self._gaussian_noise()
        e2 = self._rng.randint(0, self.q // 4)

        # u = A^T * r + e1 mod q
        if HAS_NUMPY:
            A_arr = np.array(A, dtype=np.int64)
            r_arr = np.array(r, dtype=np.int64)
            u = (A_arr.T.dot(r_arr) + np.array(e1, dtype=np.int64)) % self.q
            u = u.tolist()
        else:
            u = []
            for j in range(self.n):
                val = sum(A[i][j] * r[i] for i in range(self.n))
                val = (val + e1[j]) % self.q
                u.append(val)

        # v = b^T * r + e2 + round(q/2) * m (m=1 for encapsulation)
        br = sum(b[i] * r[i] % self.q for i in range(self.n)) % self.q
        v = (br + e2 + self.q // 2) % self.q

        # Shared secret = hash of (u, v)
        raw = self._pack_vector(u) + struct.pack("<H", v)
        shared_secret = hashlib.sha256(raw).digest()

        ciphertext = self._pack_vector(u) + struct.pack("<H", v)
        return ciphertext, shared_secret

    def decapsulate(self, sk_bytes, ciphertext):
        """Decapsulate: recover shared secret from ciphertext using sk."""
        s = self._unpack_vector(sk_bytes, self.n)
        # Adjust s back to signed representation
        s_signed = [v if v < self.q // 2 else v - self.q for v in s]

        u = self._unpack_vector(ciphertext, self.n)
        v = struct.unpack("<H", ciphertext[self.n * 2: self.n * 2 + 2])[0]

        # m' = v - s^T * u mod q
        su = sum(s_signed[i] * u[i] for i in range(self.n)) % self.q
        m_noisy = (v - su) % self.q

        # Recover shared secret
        raw = self._pack_vector(u) + struct.pack("<H", v)
        shared_secret = hashlib.sha256(raw).digest()
        return shared_secret


# ─── FalconShield (full protocol) ────────────────────────────────────────────
class FalconShield:
    def __init__(self):
        self.lwe = LWEKeyExchange()

    def encrypt(self, pk_bytes, message_256bytes):
        """Encrypt 256-byte message under public key.
        Returns ct_file_bytes = lwe_ct || iv_cipher_ct || hmac_tag
        """
        assert len(message_256bytes) == 256
        # Key encapsulation
        lwe_ct, shared_secret = self.lwe.encapsulate(pk_bytes)
        # Derive cipher key and MAC key
        cipher_key = shared_secret[:KEY_SIZE]   # first 16 bytes
        mac_key    = shared_secret[KEY_SIZE:]   # remaining 16 bytes

        # Encrypt message
        encrypted = FalconCipher.encrypt(cipher_key, message_256bytes)

        # MAC over ciphertext
        tag = hmac.new(mac_key, encrypted, hashlib.sha256).digest()

        # Format: 2-byte LWE-ct-len, lwe_ct, encrypted, 32-byte HMAC
        ct_file = (struct.pack("<H", len(lwe_ct)) + lwe_ct + encrypted + tag)
        return ct_file, shared_secret

    def decrypt(self, sk_bytes, ct_file_bytes):
        """Decrypt. Returns 256-byte message."""
        lwe_ct_len = struct.unpack("<H", ct_file_bytes[:2])[0]
        lwe_ct = ct_file_bytes[2: 2 + lwe_ct_len]
        rest = ct_file_bytes[2 + lwe_ct_len:]
        encrypted = rest[:-32]
        tag = rest[-32:]

        # Recover shared secret
        shared_secret = self.lwe.decapsulate(sk_bytes, lwe_ct)
        cipher_key = shared_secret[:KEY_SIZE]
        mac_key    = shared_secret[KEY_SIZE:]

        # Verify MAC
        expected_tag = hmac.new(mac_key, encrypted, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("MAC verification failed")

        # Decrypt
        return FalconCipher.decrypt(cipher_key, encrypted)


# ─── Generation ───────────────────────────────────────────────────────────────
def generate():
    ensure_dirs()
    print("[CYBER-P3] Generating FalconShield keypairs and ciphertexts...")

    fs = FalconShield()
    lwe = LWEKeyExchange(seed=12345)

    plaintexts = []
    public_keys = []
    secret_keys = []
    ciphertexts = []
    shared_secrets = []

    rng = random.Random(99999)

    for i in range(100):
        # Seed deterministically per keypair
        lwe_i = LWEKeyExchange(seed=10000 + i)
        pk, sk = lwe_i.keygen()
        public_keys.append(pk)
        secret_keys.append(sk)

        # Random 256-byte plaintext
        pt = bytes(rng.randint(0, 255) for _ in range(256))
        plaintexts.append(pt)

        # Encrypt using FalconShield (but with per-keypair LWE)
        fs_i = FalconShield()
        fs_i.lwe = lwe_i
        ct_bytes, ss = fs_i.encrypt(pk, pt)
        ciphertexts.append(ct_bytes)
        shared_secrets.append(ss)

        # Save ciphertext
        ct_path = os.path.join(OUTPUT_DIR, "ciphertexts", f"ct_{i:03d}.bin")
        with open(ct_path, "wb") as f:
            f.write(ct_bytes)

        # Save public key
        pk_path = os.path.join(OUTPUT_DIR, "public_keys", f"pk_{i:03d}.bin")
        with open(pk_path, "wb") as f:
            f.write(pk)

        # Save secret key (hidden)
        sk_path = os.path.join(OUTPUT_DIR, "HIDDEN_secret_keys", f"sk_{i:03d}.bin")
        with open(sk_path, "wb") as f:
            f.write(sk)

        if (i + 1) % 20 == 0:
            print(f"[CYBER-P3] Generated {i+1}/100 keypairs")

    print("[CYBER-P3] All 100 keypairs and ciphertexts written.")

    # Write known_pairs.csv (first 10)
    kp_path = os.path.join(OUTPUT_DIR, "known_pairs.csv")
    with open(kp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "plaintext_hex", "ciphertext_hex", "public_key_index"])
        writer.writeheader()
        for i in range(10):
            writer.writerow({
                "index": i,
                "plaintext_hex": plaintexts[i].hex(),
                "ciphertext_hex": ciphertexts[i].hex(),
                "public_key_index": i,
            })
    print(f"[CYBER-P3] known_pairs.csv written: {kp_path}")

    # Write HIDDEN plaintexts CSV
    hp_path = os.path.join(OUTPUT_DIR, "HIDDEN_plaintexts.csv")
    with open(hp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "plaintext_hex"])
        writer.writeheader()
        for i in range(100):
            writer.writerow({"index": i, "plaintext_hex": plaintexts[i].hex()})
    print(f"[CYBER-P3] HIDDEN_plaintexts.csv written: {hp_path}")

    # Write falconshield.py implementation file
    _write_falconshield_impl()

    # Write spec
    _write_spec()

    # Write README
    _write_readme()


def _write_falconshield_impl():
    """Write the reference implementation file for participants."""
    impl_path = os.path.join(OUTPUT_DIR, "falconshield.py")
    code = '''#!/usr/bin/env python3
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
'''
    with open(impl_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[CYBER-P3] falconshield.py written: {impl_path}")


def _write_spec():
    spec_path = os.path.join(OUTPUT_DIR, "falconshield_spec.md")
    spec = """# FalconShield Protocol Specification v1.0

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
"""
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec)
    print(f"[CYBER-P3] falconshield_spec.md written: {spec_path}")


def _write_readme():
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    content = """# CYBER-P3: CryptoPuzzle — FalconShield Protocol

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
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[CYBER-P3] README.md written: {readme_path}")


if __name__ == "__main__":
    generate()
    print("[CYBER-P3] Done.")
