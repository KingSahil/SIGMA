"""
SIGMA - Diagonal De-interleaving Module
Diagonal interleaving shifts each row by its row index modulo columns,
then reads column-by-column.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union


def diagonal_perm(n: int, rows: int, cols: int) -> np.ndarray:
    """
    Computes permutation indices for a length-n diagonal interleaver.
    """
    perm = np.empty((rows, cols), dtype=np.int64)
    for r in range(rows):
        for c in range(cols):
            perm[r, c] = r * cols + ((c + r) % cols)
    flat = perm.T.reshape(-1)
    return flat[:n]


def diagonal_interleave(
    bits: Union[List[int], np.ndarray],
    rows: int,
    cols: int
) -> np.ndarray:
    """Interleave bits using diagonal matrix permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = rows * cols
    if len(arr) < n:
        arr = np.pad(arr, (0, n - len(arr)), mode="constant")
    else:
        arr = arr[:n]

    p = diagonal_perm(n, rows, cols)
    return arr[p]


def diagonal_deinterleave(
    bits: Union[List[int], np.ndarray],
    rows: int,
    cols: int
) -> np.ndarray:
    """De-interleave bits using inverse diagonal matrix permutation."""
    arr = np.asarray(bits, dtype=np.uint8)
    n = rows * cols
    if len(arr) < n:
        arr = np.pad(arr, (0, n - len(arr)), mode="constant")
    else:
        arr = arr[:n]

    p = diagonal_perm(n, rows, cols)
    inv = np.empty_like(p)
    inv[p] = np.arange(n)
    return arr[inv]
