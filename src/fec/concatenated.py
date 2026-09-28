"""
SIGMA - Concatenated Coding Module
Implements standard satellite & deep-space concatenated FEC:
Outer Code: Reed-Solomon (e.g. RS(255, 223))
Interleaver: Convolutional / Block
Inner Code: Convolutional (Rate 1/2, K=7 or K=3)

Decoding Chain:
Rx Codeword -> Viterbi Decoder -> De-interleaver -> Reed-Solomon Decoder -> Information Bits
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Optional, Union

from .convolutional import encode_convolutional, decode_viterbi
from .reed_solomon import encode_reed_solomon, decode_reed_solomon
try:
    from deinterleaving.block import block_interleave, block_deinterleave
except ImportError:
    from ..deinterleaving.block import block_interleave, block_deinterleave


def encode_concatenated(
    info_bits: Union[List[int], np.ndarray],
    rs_nsym: int = 10,
    conv_k: int = 3,
    conv_polys: Tuple[int, ...] = (0o7, 0o5),
    interleave_block: bool = True
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Concatenated encoder: RS outer -> Interleaver -> Convolutional inner.
    """
    arr = np.asarray(info_bits, dtype=np.uint8)
    
    # 1. Outer RS encode
    rs_bits, _ = encode_reed_solomon(arr, n_sym=rs_nsym)

    # 2. Interleave
    if interleave_block:
        rows = 8
        cols = max(1, len(rs_bits) // rows)
        if rows * cols < len(rs_bits):
            cols += 1
        interleaved = block_interleave(rs_bits, rows=rows, cols=cols)
    else:
        interleaved = rs_bits

    # 3. Inner Convolutional encode
    coded_bits = encode_convolutional(interleaved, K=conv_k, polys=conv_polys)

    diag = {
        "info_bit_count": len(arr),
        "rs_bit_count": len(rs_bits),
        "interleaved_bit_count": len(interleaved),
        "coded_bit_count": len(coded_bits),
    }
    return coded_bits, diag


def decode_concatenated(
    rx_bits: Union[List[int], np.ndarray],
    rs_nsym: int = 10,
    conv_k: int = 3,
    conv_polys: Tuple[int, ...] = (0o7, 0o5),
    interleave_block: bool = True
) -> Tuple[np.ndarray, bool, int, Dict[str, Any]]:
    """
    Concatenated decoder: Viterbi inner -> De-interleaver -> RS outer.
    """
    arr = np.asarray(rx_bits, dtype=np.uint8)
    if len(arr) < 2 * conv_k:
        return np.array([], dtype=np.uint8), False, 0, {"reason": "Insufficient bits"}

    # 1. Viterbi inner decode
    vit_dec, res, viterbi_errors = decode_viterbi(arr, K=conv_k, polys=conv_polys)
    if res > 0.3:
        return np.array([], dtype=np.uint8), False, 0, {
            "reason": f"Viterbi inner decoding failed (residual {res:.3f} > 0.3)"
        }

    # 2. De-interleave
    if interleave_block:
        rows = 8
        cols = max(1, len(vit_dec) // rows)
        deint_bits = block_deinterleave(vit_dec, rows=rows, cols=cols)
    else:
        deint_bits = vit_dec

    # 3. Reed-Solomon outer decode
    rs_dec, rs_success, rs_errors, rs_diag = decode_reed_solomon(deint_bits, n_sym=rs_nsym)

    total_errors = viterbi_errors + rs_errors
    diag = {
        "viterbi_residual": res,
        "viterbi_errors": viterbi_errors,
        "rs_success": rs_success,
        "rs_errors": rs_errors,
        "total_corrected_errors": total_errors,
    }

    return rs_dec, rs_success, total_errors, diag
