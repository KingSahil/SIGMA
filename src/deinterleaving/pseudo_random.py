"""
SIGMA - Pseudo-Random De-interleaving Module
Permutes bits according to a deterministic pseudo-random sequence generated from a seed.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union


def pseudo_random_perm(n: int, seed: int = 12345) -> np.ndarray:
    """Generate deterministic permutation of length n using PRNG seed."""
    rng = np.random.default_rng(seed)
    return rng.permutation(n).astype(np.int64)


def pseudo_random_interleave(
    bits: Union[List[int], np.ndarray],
    seed: int = 12345
) -> np.ndarray:
    """Interleave bits according to pseudo-random permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    if n == 0:
        return arr
    p = pseudo_random_perm(n, seed=seed)
    return arr[p]


def pseudo_random_deinterleave(
    bits: Union[List[int], np.ndarray],
    seed: int = 12345
) -> np.ndarray:
    """De-interleave bits using the inverse pseudo-random permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    if n == 0:
        return arr
    p = pseudo_random_perm(n, seed=seed)
    inv = np.empty_like(p)
    inv[p] = np.arange(n)
    return arr[inv]
