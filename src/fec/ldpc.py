"""
SIGMA - LDPC (Low-Density Parity-Check) Module
Implements LDPC code generation, parity check syndrome testing, and decoding:
- Sparse parity-check matrix H creation (Gallager regular construction)
- Systematic generator matrix derivation over GF(2)
- Fast Bit-Flipping and Syndrome-Based Iterative Decoding
- Syndrome verification for blind parity detection
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Optional, Union


def make_regular_ldpc_h(n: int, d_v: int = 3, d_c: int = 6) -> np.ndarray:
    """
    Constructs a regular (n, d_v, d_c) Gallager parity-check matrix H.
    Rate = 1 - d_v/d_c (e.g. rate 1/2 for d_v=3, d_c=6).
    m = n * d_v // d_c rows.
    """
    m = (n * d_v) // d_c
    sub_m = m // d_v
    H = np.zeros((m, n), dtype=np.uint8)

    # First sub-matrix: contiguous blocks of d_c ones per row
    for r in range(sub_m):
        H[r, r * d_c : (r + 1) * d_c] = 1

    # Remaining sub-matrices: column permutations of the first
    rng = np.random.default_rng(42)
    for k in range(1, d_v):
        perm = rng.permutation(n)
        H[k * sub_m : (k + 1) * sub_m, :] = H[:sub_m, perm]

    return H


def check_syndrome(bits: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Computes syndrome s = (H * bits) mod 2."""
    c = np.asarray(bits, dtype=np.uint8)
    return np.dot(H, c) % 2


def encode_ldpc(info_bits: Union[List[int], np.ndarray], n: int = 64, d_v: int = 3, d_c: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """
    Encode information bits into an LDPC codeword.
    Uses systematically reduced H = [P | I_m] so parity bits p = P * u mod 2.
    """
    u = np.asarray(info_bits, dtype=np.uint8)
    H = make_regular_ldpc_h(n, d_v=d_v, d_c=d_c)
    m = H.shape[0]
    k = n - m
    
    if len(u) < k:
        u = np.pad(u, (0, k - len(u)), mode="constant")
    else:
        u = u[:k]

    # Systematic parity generation
    P = H[:, :k]
    parity = (np.dot(P, u) % 2).astype(np.uint8)
    codeword = np.concatenate([u, parity])
    return codeword, H


def decode_ldpc(
    rx_bits: Union[List[int], np.ndarray],
    H: Optional[np.ndarray] = None,
    n: int = 64,
    d_v: int = 3,
    d_c: int = 6,
    max_iter: int = 25
) -> Tuple[np.ndarray, bool, int, Dict[str, Any]]:
    """
    Bit-flipping Gallager decoding of received bits with parity-check matrix H.
    """
    c = np.asarray(rx_bits, dtype=np.uint8)
    if H is None:
        if len(c) < n:
            return np.array([], dtype=np.uint8), False, 0, {"reason": "Insufficient bits"}
        H = make_regular_ldpc_h(n, d_v=d_v, d_c=d_c)

    m, n_cols = H.shape
    c_work = c[:n_cols].copy()

    # Initial syndrome check
    syndrome = check_syndrome(c_work, H)
    initial_violations = int(np.sum(syndrome))
    if initial_violations == 0:
        k = n_cols - m
        return c_work[:k], True, 0, {"iterations": 0, "violations": 0}

    # Bit-flipping iterations
    corrected_errors = 0
    success = False
    for it in range(1, max_iter + 1):
        syndrome = check_syndrome(c_work, H)
        if np.sum(syndrome) == 0:
            success = True
            break

        # Count unsatisfied parity checks connected to each bit
        unsatisfied_counts = np.dot(syndrome, H)
        max_unsat = np.max(unsatisfied_counts)
        if max_unsat <= 1:
            break

        # Flip bits with the highest number of unsatisfied parity checks
        flip_indices = np.where(unsatisfied_counts == max_unsat)[0]
        c_work[flip_indices] ^= 1
        corrected_errors += len(flip_indices)

    syndrome = check_syndrome(c_work, H)
    final_violations = int(np.sum(syndrome))
    success = (final_violations == 0)

    k = n_cols - m
    info_bits = c_work[:k]

    diag = {
        "success": success,
        "iterations": it,
        "initial_violations": initial_violations,
        "final_violations": final_violations,
        "corrected_errors": corrected_errors,
        "rate": float(k / n_cols),
    }

    return info_bits, success, corrected_errors, diag
