"""
SIGMA - Candidate Payload Boundary Detection Module
Slices bitstream into structured frames:
- Candidate Header -> Candidate Payload -> Parity / Trailing boundary
- Entropy calculation: distinguishes random/compressed payload from structured headers
- Packet region slicing
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union, Optional
from .bitstream import bits_to_hex


def compute_bit_entropy(bits: np.ndarray) -> float:
    """Computes Shannon entropy (bits per symbol) of a bit sequence."""
    if len(bits) == 0:
        return 0.0
    p1 = np.mean(bits)
    p0 = 1.0 - p1
    if p0 <= 0 or p1 <= 0:
        return 0.0
    return float(-p0 * np.log2(p0) - p1 * np.log2(p1))


def extract_candidate_payloads(
    rx_bits: Union[List[int], np.ndarray],
    candidate_headers: List[Dict[str, Any]],
    default_payload_bits: int = 256
) -> List[Dict[str, Any]]:
    """
    Extracts candidate payload regions based on detected sync words / headers.
    """
    rx = np.asarray(rx_bits, dtype=np.uint8)
    n = len(rx)
    if n == 0 or not candidate_headers:
        # Default payload candidate slice when no header was identified
        if n >= 64:
            payload_len = min(n, default_payload_bits)
            sub = rx[:payload_len]
            return [{
                "region_id": 1,
                "label": "CANDIDATE PAYLOAD (Unframed)",
                "start_bit": 0,
                "end_bit": payload_len,
                "length_bits": payload_len,
                "entropy": compute_bit_entropy(sub),
                "hex_preview": bits_to_hex(sub, max_bytes=8),
                "bits": sub.tolist(),
            }]
        return []

    # Use first prominent header candidate
    top_header = candidate_headers[0]
    hits = top_header.get("hits", [])
    p_len = top_header.get("pattern_length", 32)
    frame_len = top_header.get("estimated_frame_length")

    payloads = []
    for idx, hit in enumerate(hits):
        start = hit["bit_offset"] + p_len
        if frame_len and frame_len > p_len:
            end = min(n, hit["bit_offset"] + frame_len)
        else:
            end = min(n, start + default_payload_bits)

        if end <= start:
            continue

        region_bits = rx[start:end]
        payloads.append({
            "region_id": idx + 1,
            "label": f"CANDIDATE PAYLOAD (Frame {idx + 1})",
            "associated_header": top_header.get("pattern_name", "Sync"),
            "start_bit": start,
            "end_bit": end,
            "length_bits": len(region_bits),
            "entropy": compute_bit_entropy(region_bits),
            "hex_preview": bits_to_hex(region_bits, max_bytes=8),
            "bits": region_bits.tolist(),
        })

    return payloads
