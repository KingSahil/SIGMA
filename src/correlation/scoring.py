"""
SIGMA - Bitstream Correlation & Intelligence Scoring Module
Coordinates:
- Bitstream A vs Bitstream B cross-correlation
- Frame alignment and lag calculation
- Header and payload candidate identification
- Unified similarity score calculation
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union, Optional

from .alignment import align_bitstreams
from .header_detection import detect_candidate_headers
from .payload_detection import extract_candidate_payloads
try:
    from models.signal_result import CorrelationResult
except ImportError:
    from ..models.signal_result import CorrelationResult


def correlate_bitstreams(
    stream_a: Union[List[int], np.ndarray],
    stream_b: Optional[Union[List[int], np.ndarray]] = None,
    sync_patterns: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entrypoint for bitstream correlation.
    Supports either two bitstreams (A vs B) or single bitstream analysis (searching internal structure).

    Returns:
    {
        "alignment": int,
        "similarity": float,
        "candidate_headers": List[Dict[str, Any]],
        "candidate_payload_regions": List[Dict[str, Any]],
        "score": float,
        "status": str
    }
    """
    arr_a = np.asarray(stream_a, dtype=np.uint8) if stream_a is not None else np.array([], dtype=np.uint8)

    if len(arr_a) < 8:
        return {
            "alignment": 0,
            "similarity": 0.0,
            "candidate_headers": [],
            "candidate_payload_regions": [],
            "score": 0.0,
            "status": "INSUFFICIENT DATA",
            "diagnostics": {"reason": "Bitstream too short"}
        }

    # 1. Candidate Header & Sync Pattern Search
    candidate_headers = detect_candidate_headers(arr_a, custom_patterns=sync_patterns)

    # 2. Candidate Payload Boundary Detection
    candidate_payloads = extract_candidate_payloads(arr_a, candidate_headers)

    # 3. Two-stream correlation if stream_b is provided
    if stream_b is not None and len(stream_b) > 0:
        arr_b = np.asarray(stream_b, dtype=np.uint8)
        best_lag, is_inv, sim, _, _ = align_bitstreams(arr_a, arr_b)
        status = "MATCH FOUND" if sim >= 0.85 else ("PARTIAL MATCH" if sim >= 0.65 else "NO MATCH")
        score = sim
        alignment = best_lag
    else:
        # Single-stream autocorrelation / self-consistency
        alignment = candidate_headers[0]["first_offset"] if candidate_headers else 0
        score = candidate_headers[0]["confidence"] if candidate_headers else 0.5
        status = "HEADER IDENTIFIED" if candidate_headers else "UNFRAMED / NO MATCH"
        sim = score

    return {
        "alignment": alignment,
        "similarity": float(sim),
        "candidate_headers": candidate_headers,
        "candidate_payload_regions": candidate_payloads,
        "score": float(score),
        "status": status,
        "diagnostics": {
            "header_count": len(candidate_headers),
            "payload_regions_count": len(candidate_payloads),
            "stream_a_length": len(arr_a),
        }
    }
