"""
SIGMA - Bitstream Alignment Module
Aligns two bitstreams by computing cross-correlation across all relative lags:
- Direct cross-correlation: r[k] = sum((2*a - 1) * (2*b - 1))
- Phase / polarity inversion detection (handles 180-degree BPSK ambiguity)
- Optimal lag alignment extraction
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union, Optional


def align_bitstreams(
    stream_a: Union[List[int], np.ndarray],
    stream_b: Union[List[int], np.ndarray],
    max_lag: Optional[int] = None
) -> Tuple[int, bool, float, np.ndarray, np.ndarray]:
    """
    Find best alignment offset between stream_a and stream_b.

    Returns:
        (best_lag, is_inverted, similarity_score, aligned_a, aligned_b)
        where best_lag is the shift applied to stream_b to match stream_a.
    """
    a = np.asarray(stream_a, dtype=np.int8)
    b = np.asarray(stream_b, dtype=np.int8)

    na = len(a)
    nb = len(b)
    if na == 0 or nb == 0:
        return 0, False, 0.0, np.array([], dtype=np.uint8), np.array([], dtype=np.uint8)

    # Convert 0/1 to bipolar -1/+1
    bip_a = 2 * a - 1
    bip_b = 2 * b - 1

    # Cross-correlation via FFT
    n_conv = na + nb - 1
    fft_size = 1 << (n_conv - 1).bit_length()
    A = np.fft.fft(bip_a, fft_size)
    B = np.fft.fft(bip_b[::-1], fft_size)
    corr = np.real(np.fft.ifft(A * B))[:n_conv]

    # Lags range from -(nb - 1) to (na - 1)
    lags = np.arange(-(nb - 1), na)

    if max_lag is not None and max_lag > 0:
        valid_mask = np.abs(lags) <= max_lag
        corr = corr[valid_mask]
        lags = lags[valid_mask]

    # Peak correlation
    idx_max = int(np.argmax(corr))
    idx_min = int(np.argmin(corr))

    val_max = corr[idx_max]
    val_min = corr[idx_min]

    if abs(val_min) > abs(val_max):
        best_lag = int(lags[idx_min])
        is_inverted = True
        peak_val = abs(val_min)
    else:
        best_lag = int(lags[idx_max])
        is_inverted = False
        peak_val = val_max

    # Slice aligned segments
    if best_lag >= 0:
        # stream_b is delayed relative to stream_a
        sub_a = a[best_lag : min(na, best_lag + nb)]
        sub_b = b[: len(sub_a)]
    else:
        # stream_a is delayed relative to stream_b
        shift = -best_lag
        sub_b = b[shift : min(nb, shift + na)]
        sub_a = a[: len(sub_b)]

    if is_inverted:
        sub_b = sub_b ^ 1

    overlap = len(sub_a)
    if overlap > 0:
        matches = int(np.sum(sub_a == sub_b))
        sim = float(matches / overlap)
    else:
        sim = 0.0

    return best_lag, is_inverted, sim, sub_a.astype(np.uint8), sub_b.astype(np.uint8)
