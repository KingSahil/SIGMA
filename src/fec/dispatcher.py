"""
SIGMA - Forward Error Correction (FEC) Dispatcher
Coordinates decoding across supported FEC families:
1. Convolutional Codes (Viterbi Decoding)
2. Reed-Solomon Block Codes
3. Concatenated Codes (RS + Convolutional)
4. LDPC (Low-Density Parity-Check Codes)

Strict Validation Rule:
Decoders must never fabricate results. The status must clearly report:
- "SUPPORTED"
- "NOT DETECTED"
- "UNKNOWN"
- "INSUFFICIENT DATA"
- "DECODING FAILED"
"""

import numpy as np
from typing import Dict, Any, Optional, Union, List

from .convolutional import decode_viterbi, search_convolutional_code, CANDIDATE_CODES, FEC_THRESHOLD
from .reed_solomon import decode_reed_solomon
from .concatenated import decode_concatenated
from .ldpc import decode_ldpc

try:
    from sigma_coding import analyse_coding_layer
except ImportError:
    try:
        from ..sigma_coding import analyse_coding_layer
    except (ImportError, ValueError):
        analyse_coding_layer = None


def decode_fec(
    bits: Union[List[int], np.ndarray],
    fec_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Unified FEC decoding dispatcher.
    """
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    params = dict(parameters or {})

    if n < 8:
        return {
            "fec_type": fec_type or "none",
            "decoded_bits": [],
            "status": "INSUFFICIENT DATA",
            "corrected_errors": 0,
            "residual": None,
            "diagnostics": {"reason": f"Bitstream length ({n}) is too short for FEC decoding"}
        }

    canon_type = (fec_type or "").lower().replace("-", "_").replace(" ", "")

    # 1. Convolutional / Viterbi decoding
    if "conv" in canon_type or "viterbi" in canon_type:
        k = params.get("K", 3)
        polys = params.get("polys", (0o7, 0o5))
        dec_bits, res, errs = decode_viterbi(arr, K=k, polys=polys)

        if res <= FEC_THRESHOLD:
            status = "SUPPORTED"
        elif res < 0.15:
            status = "DECODING FAILED"  # Trellis didn't close cleanly
        else:
            status = "NOT DETECTED"

        return {
            "fec_type": f"convolutional (K={k})",
            "decoded_bits": dec_bits.tolist() if status == "SUPPORTED" else [],
            "status": status,
            "corrected_errors": errs if status == "SUPPORTED" else 0,
            "residual": float(res),
            "diagnostics": {
                "residual": float(res),
                "threshold": FEC_THRESHOLD,
                "K": k,
                "polys": polys,
            }
        }

    # 2. Reed-Solomon block code
    elif "reed" in canon_type or "rs" in canon_type:
        nsym = params.get("n_sym", 10)
        dec_bits, ok, errs, diag = decode_reed_solomon(arr, n_sym=nsym)
        status = "SUPPORTED" if ok else "DECODING FAILED"
        return {
            "fec_type": f"reed_solomon (nsym={nsym})",
            "decoded_bits": dec_bits.tolist() if ok else [],
            "status": status,
            "corrected_errors": errs,
            "residual": 0.0 if ok else 1.0,
            "diagnostics": diag
        }

    # 3. Concatenated RS + Convolutional
    elif "concat" in canon_type:
        rs_nsym = params.get("rs_nsym", 10)
        conv_k = params.get("conv_k", 3)
        conv_polys = params.get("conv_polys", (0o7, 0o5))
        interleave = params.get("interleave_block", True)
        dec_bits, ok, errs, diag = decode_concatenated(
            arr, rs_nsym=rs_nsym, conv_k=conv_k, conv_polys=conv_polys, interleave_block=interleave
        )
        status = "SUPPORTED" if ok else "DECODING FAILED"
        return {
            "fec_type": "concatenated (RS + Conv)",
            "decoded_bits": dec_bits.tolist() if ok else [],
            "status": status,
            "corrected_errors": errs,
            "residual": diag.get("viterbi_residual"),
            "diagnostics": diag
        }

    # 4. LDPC
    elif "ldpc" in canon_type:
        h_matrix = params.get("H")
        dec_bits, ok, errs, diag = decode_ldpc(arr, H=h_matrix)
        status = "SUPPORTED" if ok else "DECODING FAILED"
        return {
            "fec_type": "ldpc",
            "decoded_bits": dec_bits.tolist() if ok else [],
            "status": status,
            "corrected_errors": errs,
            "residual": 0.0 if ok else float(diag.get("final_violations", 1.0)),
            "diagnostics": diag
        }

    # 5. Unknown / Automatic Discovery
    # Probe candidate convolutional codes using blind scheme search
    cand_hit = search_convolutional_code(arr)
    if cand_hit is not None:
        dec_bits, res, errs = decode_viterbi(arr, K=cand_hit["K"], polys=cand_hit["polys"])
        if res <= FEC_THRESHOLD:
            return {
                "fec_type": f"convolutional {cand_hit['name']}",
                "decoded_bits": dec_bits.tolist(),
                "status": "SUPPORTED",
                "corrected_errors": errs,
                "residual": float(res),
                "diagnostics": cand_hit
            }

    # No known FEC matched with low residual
    return {
        "fec_type": "unknown",
        "decoded_bits": [],
        "status": "NOT DETECTED",
        "corrected_errors": 0,
        "residual": None,
        "diagnostics": {
            "reason": "No FEC codeword parity verified among candidate schemes",
            "candidates_tested": [c[0] for c in CANDIDATE_CODES]
        }
    }
