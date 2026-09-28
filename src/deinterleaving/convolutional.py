"""
SIGMA - Convolutional De-interleaving Module
Ramsey / Forney shift-register convolutional interleaver:
- Interleaver distributes symbols across S branches with delay step j (delay i * j on branch i).
- De-interleaver compensates with complementary delay (S - 1 - i) * j.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union


def convolutional_perm(n: int, S: int = 8, j: int = 2) -> np.ndarray:
    """
    Computes permutation indices for a length-n convolutional interleaver.
    """
    perm = np.empty(n, dtype=np.int64)
    for i in range(n):
        branch = i % S
        perm[i] = i + branch * j * S
    order = np.argsort(perm)
    return order.astype(np.int64)


def convolutional_interleave(
    bits: Union[List[int], np.ndarray],
    S: int = 8,
    j: int = 2
) -> np.ndarray:
    """Interleave bits using convolutional permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    if n == 0:
        return arr
    perm = convolutional_perm(n, S=S, j=j)
    return arr[perm]


def convolutional_deinterleave(
    bits: Union[List[int], np.ndarray],
    S: int = 8,
    j: int = 2
) -> np.ndarray:
    """De-interleave bits using the inverse permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    if n == 0:
        return arr
    perm = convolutional_perm(n, S=S, j=j)
    inv = np.empty_like(perm)
    inv[perm] = np.arange(n)
    return arr[inv]
