"""
SIGMA - Bitstream Utilities & Metric Calculations
Provides bitstream handling:
- Hamming distance
- Bit Error Rate (BER)
- Autocorrelation / Run-length statistics
- Bit packing/unpacking and hexadecimal formatting
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union


def hamming_distance(a: Union[List[int], np.ndarray], b: Union[List[int], np.ndarray]) -> int:
    """Compute Hamming distance (number of bit discrepancies)."""
    arr_a = np.asarray(a, dtype=np.uint8)
    arr_b = np.asarray(b, dtype=np.uint8)
    n = min(len(arr_a), len(arr_b))
    if n == 0:
        return 0
    return int(np.sum(arr_a[:n] != arr_b[:n]))


def compute_ber(rx: Union[List[int], np.ndarray], tx: Union[List[int], np.ndarray]) -> Tuple[float, int, int]:
    """
    Compute Bit Error Rate between received and reference bitstreams.
    Returns: (ber, error_count, total_evaluated_bits)
    """
    arr_rx = np.asarray(rx, dtype=np.uint8)
    arr_tx = np.asarray(tx, dtype=np.uint8)
    n = min(len(arr_rx), len(arr_tx))
    if n == 0:
        return 0.0, 0, 0
    errors = int(np.sum(arr_rx[:n] != arr_tx[:n]))
    ber = float(errors / n)
    return ber, errors, n


def bits_to_hex(bits: Union[List[int], np.ndarray], max_bytes: int = 16) -> str:
    """Formats leading bits into a clean hex string."""
    arr = np.asarray(bits, dtype=np.uint8)
    if len(arr) == 0:
        return "--"
    n_bytes = min(len(arr) // 8, max_bytes)
    if n_bytes == 0:
        return bin(int("".join(str(b) for b in arr[:8]), 2))
    packed = np.packbits(arr[: n_bytes * 8])
    return "0x" + "".join(f"{b:02X}" for b in packed)


def format_spaced_bits(bits: Union[List[int], np.ndarray], group_size: int = 4, max_bits: int = 48) -> str:
    """Formats bit array into spaced nibbles."""
    arr = np.asarray(bits, dtype=np.uint8)[:max_bits]
    if len(arr) == 0:
        return "--"
    s = "".join(str(int(b)) for b in arr)
    return " ".join(s[i : i + group_size] for i in range(0, len(s), group_size))
