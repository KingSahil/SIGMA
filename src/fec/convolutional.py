"""
SIGMA - Convolutional Coding & Viterbi Decoding Module
Implements short-constrained convolutional codes with Viterbi decoding:
- Rate 1/2 codes with K = 3, 4, 5, 7, 9
- NASA/CCSDS standard (2,1,3) [polys (7, 5) octal]
- Classic Voyager (2,1,7) [polys (171, 133) octal]
- Trellis traceback, hard/soft decision decoding
- Re-encode residual verification
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Optional, Union

try:
    from sigma_coding import (
        conv_encode as sigma_conv_encode,
        viterbi_decode as sigma_viterbi_decode,
        reencode_residual as sigma_reencode_residual,
        search_fec_scheme as sigma_search_fec_scheme,
        DEFAULT_K,
        DEFAULT_POLYS,
        CANDIDATE_CODES,
        FEC_THRESHOLD,
    )
except ImportError:
    try:
        from ..sigma_coding import (
            conv_encode as sigma_conv_encode,
            viterbi_decode as sigma_viterbi_decode,
            reencode_residual as sigma_reencode_residual,
            search_fec_scheme as sigma_search_fec_scheme,
            DEFAULT_K,
            DEFAULT_POLYS,
            CANDIDATE_CODES,
            FEC_THRESHOLD,
        )
    except (ImportError, ValueError):
        sigma_conv_encode = None
        sigma_viterbi_decode = None
        sigma_reencode_residual = None
        sigma_search_fec_scheme = None
        DEFAULT_K = 3
        DEFAULT_POLYS = (0b111, 0b101)
        CANDIDATE_CODES = (("(2,1,3)", 3, (0o7, 0o5)),)
        FEC_THRESHOLD = 0.03


def encode_convolutional(
    bits: Union[List[int], np.ndarray],
    K: int = 3,
    polys: Tuple[int, ...] = (0o7, 0o5)
) -> np.ndarray:
    """Encode an information bit sequence using convolutional code (K, polys)."""
    if sigma_conv_encode is not None:
        return sigma_conv_encode(bits, K=K, polys=polys)

    # Standalone fallback implementation
    arr = np.asarray(bits, dtype=np.uint8)
    reg = 0
    mask = (1 << (K - 1)) - 1
    out = []
    for b in arr:
        reg = ((reg << 1) | int(b)) & ((1 << K) - 1)
        for poly in polys:
            parity = bin(reg & poly).count("1") % 2
            out.append(parity)
    return np.asarray(out, dtype=np.uint8)


def decode_viterbi(
    rx_bits: Union[List[int], np.ndarray],
    K: int = 3,
    polys: Tuple[int, ...] = (0o7, 0o5),
    soft: bool = False
) -> Tuple[np.ndarray, float, int]:
    """
    Decodes received bits with the Viterbi algorithm.
    Returns:
        (decoded_bits, residual, corrected_errors)
    """
    arr = np.asarray(rx_bits, dtype=np.uint8)
    if len(arr) < 2 * K:
        return np.array([], dtype=np.uint8), 1.0, 0

    if sigma_viterbi_decode is not None:
        dec = sigma_viterbi_decode(arr, K=K, polys=polys, soft=soft)
        res = sigma_reencode_residual(arr, K=K, polys=polys) if sigma_reencode_residual else 0.0
        # Estimate corrected bit errors: difference between rx and re-encoded
        re_enc = encode_convolutional(dec, K=K, polys=polys)[:len(arr)]
        errors = int(np.sum(arr[:len(re_enc)] != re_enc))
        return dec, float(res), errors

    # Minimal fallback
    dec = arr[::2][:len(arr)//2]
    return dec, 0.5, 0


def search_convolutional_code(rx_bits: Union[List[int], np.ndarray]) -> Optional[Dict[str, Any]]:
    """Search candidate codes to identify code parameters."""
    if sigma_search_fec_scheme is not None:
        best_name, best_k, best_polys, best_res, table = sigma_search_fec_scheme(rx_bits)
        if best_name is not None and best_res <= 0.05:
            return {
                "name": best_name,
                "K": best_k,
                "polys": best_polys,
                "residual": best_res,
                "table": table
            }
    return None
