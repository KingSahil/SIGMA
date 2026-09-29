"""
SIGMA - Block De-interleaving Module
Matrix-based block interleaving:
- Interleaver: Writes row-by-row, reads column-by-column.
- De-interleaver: Writes column-by-column, reads row-by-row.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union


def block_interleave(bits: Union[List[int], np.ndarray], rows: int, cols: int) -> np.ndarray:
    """
    Block interleave a bit sequence of length rows * cols (or truncates/pads).
    Writes row-by-row, reads column-by-column.
    """
    arr = np.asarray(bits, dtype=np.uint8)
    n = rows * cols
    if len(arr) < n:
        arr = np.pad(arr, (0, n - len(arr)), mode="constant")
    else:
        arr = arr[:n]

    matrix = arr.reshape((rows, cols))
    # Read column-by-column (Fortran order transpose)
    interleaved = matrix.T.reshape(-1)
    return interleaved


def block_deinterleave(bits: Union[List[int], np.ndarray], rows: int, cols: int) -> np.ndarray:
    """
    Block de-interleave a bit sequence of length rows * cols.
    Writes column-by-column, reads row-by-row.
    """
    arr = np.asarray(bits, dtype=np.uint8)
    n = rows * cols
    if len(arr) < n:
        arr = np.pad(arr, (0, n - len(arr)), mode="constant")
    else:
        arr = arr[:n]

    # De-interleaver is the inverse: reshape as cols x rows, then transpose back to rows x cols
    matrix = arr.reshape((cols, rows))
    deinterleaved = matrix.T.reshape(-1)
    return deinterleaved
