"""Versioned keyed PCG64/QR construction; no private key embedded in source."""
import hashlib
import numpy as np

DIMENSION = 16 * (8 * 14 - 1)
CODE_BITS = 592

def group_code(key: bytes, group: int, dimension=DIMENSION, bits=CODE_BITS):
    if len(key) != 32 or not 0 <= group < 2**32 or dimension < bits:
        raise ValueError("256-bit key, uint32 group and d>=bits are required")
    # Protocol v1 fixes endianness and the full SHA-256 digest-to-integer mapping.
    seed = int.from_bytes(hashlib.sha256(key + group.to_bytes(4, "big")).digest(), "big")
    a = np.random.Generator(np.random.PCG64(seed)).standard_normal((dimension, bits))
    q, r = np.linalg.qr(a, mode="reduced")
    q *= np.where(np.diag(r) < 0, -1.0, 1.0)[None, :]
    return np.ascontiguousarray(q.T, dtype=np.float32)

def codebook(key, groups=16):
    return np.stack([group_code(key, g) for g in range(groups)])
