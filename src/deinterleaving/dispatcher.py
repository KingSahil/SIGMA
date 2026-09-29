"""
SIGMA - De-interleaving Dispatcher & Blind Parameter Detection
Coordinates:
- Block de-interleaving
- Convolutional de-interleaving
- Diagonal de-interleaving
- Pseudo-random de-interleaving

Provides blind hypothesis scoring when parameters are unknown:
Evaluates re-encode residual after de-interleaving across candidate configurations.
"""

import numpy as np
from typing import Dict, Any, Optional, Union, List

from .block import block_deinterleave, block_interleave
from .convolutional import convolutional_deinterleave, convolutional_interleave
from .diagonal import diagonal_deinterleave, diagonal_interleave
from .pseudo_random import pseudo_random_deinterleave, pseudo_random_interleave

try:
    from sigma_coding import (
        detect_interleaver as sigma_detect_interleaver,
        _factorisations,
        reencode_residual,
        DEFAULT_K,
        DEFAULT_POLYS,
    )
except ImportError:
    try:
        from ..sigma_coding import (
            detect_interleaver as sigma_detect_interleaver,
            _factorisations,
            reencode_residual,
            DEFAULT_K,
            DEFAULT_POLYS,
        )
    except (ImportError, ValueError):
        sigma_detect_interleaver = None
        _factorisations = None
        reencode_residual = None
        DEFAULT_K = 3
        DEFAULT_POLYS = (0b111, 0b101)


def deinterleave(
    bits: Union[List[int], np.ndarray],
    mode: str = "block",
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Unified de-interleaving dispatcher with explicit and candidate search support.

    Returns:
    {
        "mode": str,
        "input_bits": int,
        "output_bits": List[int],
        "parameters": Dict[str, Any],
        "confidence": float | None,
        "status": "success" | "unknown" | "insufficient_data" | "not_detected"
    }
    """
    arr = np.asarray(bits, dtype=np.uint8)
    n = len(arr)
    params = dict(parameters or {})

    if n < 8:
        return {
            "mode": mode,
            "input_bits": n,
            "output_bits": arr.tolist(),
            "parameters": params,
            "confidence": None,
            "status": "insufficient_data",
            "diagnostics": {"reason": "Bitstream too short for de-interleaving"}
        }

    canon_mode = mode.lower().strip() if mode else "unknown"

    # Case 1: Mode is explicitly provided with parameters
    if canon_mode == "block":
        rows = params.get("rows")
        cols = params.get("cols")
        if rows is None or cols is None:
            # Pick rectangular factors near sqrt(n)
            side = int(np.floor(np.sqrt(n)))
            rows, cols = side, max(1, n // side)
            params["rows"] = rows
            params["cols"] = cols

        out = block_deinterleave(arr, rows, cols)
        return {
            "mode": "block",
            "input_bits": n,
            "output_bits": out.tolist(),
            "parameters": {"rows": rows, "cols": cols},
            "confidence": 0.85 if "rows" in (parameters or {}) else 0.5,
            "status": "success",
            "diagnostics": {"rows": rows, "cols": cols}
        }

    elif canon_mode == "convolutional":
        S = params.get("S", 8)
        j = params.get("j", 2)
        out = convolutional_deinterleave(arr, S=S, j=j)
        return {
            "mode": "convolutional",
            "input_bits": n,
            "output_bits": out.tolist(),
            "parameters": {"S": S, "j": j},
            "confidence": 0.85 if "S" in (parameters or {}) else 0.5,
            "status": "success",
            "diagnostics": {"S": S, "j": j}
        }

    elif canon_mode == "diagonal":
        rows = params.get("rows")
        cols = params.get("cols")
        if rows is None or cols is None:
            side = int(np.floor(np.sqrt(n)))
            rows, cols = side, max(1, n // side)
            params["rows"] = rows
            params["cols"] = cols

        out = diagonal_deinterleave(arr, rows, cols)
        return {
            "mode": "diagonal",
            "input_bits": n,
            "output_bits": out.tolist(),
            "parameters": {"rows": rows, "cols": cols},
            "confidence": 0.85 if "rows" in (parameters or {}) else 0.5,
            "status": "success",
            "diagnostics": {"rows": rows, "cols": cols}
        }

    elif canon_mode in ["pseudo_random", "pseudorandom", "pr"]:
        seed = params.get("seed", 12345)
        out = pseudo_random_deinterleave(arr, seed=seed)
        return {
            "mode": "pseudo_random",
            "input_bits": n,
            "output_bits": out.tolist(),
            "parameters": {"seed": seed},
            "confidence": 0.85 if "seed" in (parameters or {}) else 0.5,
            "status": "success",
            "diagnostics": {"seed": seed}
        }

    # Case 2: Mode is unknown -> blind candidate search
    if sigma_detect_interleaver is not None and reencode_residual is not None:
        # ``detect_interleaver`` returns a winning mode, residual scores, and
        # the geometry that produced each score.  Older versions returned a
        # five-value FEC-scoring tuple, so adapt the current detector contract
        # here rather than allowing a custom capture to abort recovery.
        best_mode, scores, geometry = sigma_detect_interleaver(
            arr, K=DEFAULT_K, polys=DEFAULT_POLYS, return_geometry=True
        )
        if best_mode is not None:
            best_res = scores.get(best_mode)
            ordered_scores = sorted(scores.values())
            margin = (
                ordered_scores[1] - ordered_scores[0]
                if len(ordered_scores) > 1 else None
            )
            best_params = {}
            if best_mode in {"block", "diagonal"}:
                rows, cols = geometry.get(best_mode, (None, None))
                if rows is not None and cols is not None:
                    best_params = {"rows": rows, "cols": cols}
            # We found an interleaving mode that unlocks FEC decoding (residual drops)
            detected_out = deinterleave(arr, mode=best_mode, parameters=best_params)["output_bits"]
            conf = float(np.clip(1.0 - (best_res if best_res is not None else 1.0) * 10.0, 0.0, 1.0))
            return {
                "mode": best_mode,
                "input_bits": n,
                "output_bits": detected_out,
                "parameters": best_params,
                "confidence": conf,
                "status": "success",
                "diagnostics": {
                    "method": "blind_fec_residual_scoring",
                    "residual": best_res,
                    "margin": margin,
                    "candidates_tested": len(scores),
                }
            }

    # Cannot definitively discover interleaver
    return {
        "mode": "unknown",
        "input_bits": n,
        "output_bits": arr.tolist(),
        "parameters": {},
        "confidence": None,
        "status": "unknown",
        "diagnostics": {
            "reason": "Unknown interleaver pattern and no coded parity structure found",
            "candidate_modes": ["block", "convolutional", "diagonal", "pseudo_random"]
        }
    }
