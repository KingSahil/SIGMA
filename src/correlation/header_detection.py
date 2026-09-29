"""
SIGMA - Candidate Header & Preamble Detection Module
Implements sync-word matching and statistical preamble discovery:
- Standard Aerospace/Telemetry sync words (CCSDS 32-bit, Barker-7/11/13, HDLC 0x7E, Ethernet 0xAA)
- Statistical chance threshold: guarantees hits are rarer than false-alarm probability (e.g. p < 0.01)
- Repeated sync interval estimation (frame length hypothesis)

Rule:
Patterns without recognized protocol endorsement are strictly labeled:
"CANDIDATE HEADER"
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union, Optional
from scipy.stats import binom

# Common Standard Sync Words (bits)
KNOWN_SYNC_WORDS = {
    "CCSDS 32-bit (0x1ACFFC1D)": np.unpackbits(np.frombuffer(bytes.fromhex("1ACFFC1D"), dtype=np.uint8)),
    "Barker 13 (1111100110101)": np.array([1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8),
    "Barker 11 (11100010010)": np.array([1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0], dtype=np.uint8),
    "Barker 7 (1110010)": np.array([1, 1, 1, 0, 0, 1, 0], dtype=np.uint8),
    "HDLC / AX.25 Flag (0x7E)": np.unpackbits(np.frombuffer(bytes([0x7E]), dtype=np.uint8)),
    "Ethernet Preamble (0xAA)": np.unpackbits(np.frombuffer(bytes([0xAA]), dtype=np.uint8)),
}


def chance_threshold(n_bits: int, pattern_len: int, max_false_alarm: float = 0.01) -> int:
    """
    Maximum allowable bit errors in a pattern of length L across an n-bit stream
    such that the chance false-alarm probability is below max_false_alarm.
    """
    if n_bits < pattern_len:
        return 0
    num_tests = max(1, n_bits - pattern_len + 1)
    # Target p_single such that 1 - (1 - p_single)^num_tests <= max_false_alarm
    p_single = max_false_alarm / float(num_tests)
    # Binomial(pattern_len, 0.5)
    for k in range(pattern_len // 2):
        if binom.cdf(k, pattern_len, 0.5) <= p_single:
            best_k = k
        else:
            break
    return best_k


def search_sync_pattern(
    rx_bits: Union[List[int], np.ndarray],
    pattern: Union[List[int], np.ndarray],
    max_errors: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Sliding window cross-correlation searching for pattern in rx_bits.
    """
    rx = np.asarray(rx_bits, dtype=np.uint8)
    pat = np.asarray(pattern, dtype=np.uint8)
    L = len(pat)
    N = len(rx)
    if N < L:
        return []

    if max_errors is None:
        max_errors = chance_threshold(N, L, max_false_alarm=0.01)

    hits = []
    # Vectorized sliding Hamming distance using 2D rolling window if memory permits
    for i in range(N - L + 1):
        err = int(np.sum(rx[i : i + L] != pat))
        if err <= max_errors:
            hits.append({
                "bit_offset": i,
                "bit_errors": err,
                "pattern_length": L,
                "confidence": float(1.0 - (err / L)),
            })

    return hits


def detect_candidate_headers(
    rx_bits: Union[List[int], np.ndarray],
    custom_patterns: Optional[Dict[str, Union[List[int], np.ndarray]]] = None
) -> List[Dict[str, Any]]:
    """
    Scans bitstream for both known standard sync words and prominent repeated candidate headers.
    """
    rx = np.asarray(rx_bits, dtype=np.uint8)
    if len(rx) < 16:
        return []

    all_patterns = dict(KNOWN_SYNC_WORDS)
    if custom_patterns:
        all_patterns.update(custom_patterns)

    detected = []
    for name, pat in all_patterns.items():
        hits = search_sync_pattern(rx, pat)
        if hits:
            # Estimate frame periodicity if multiple hits exist
            offsets = [h["bit_offset"] for h in hits]
            period = int(np.diff(offsets)[0]) if len(offsets) > 1 else None

            detected.append({
                "label": f"CANDIDATE HEADER ({name})" if "CCSDS" not in name and "Barker" not in name else f"STANDARD HEADER ({name})",
                "pattern_name": name,
                "pattern_hex": "0x" + "".join(f"{b:02X}" for b in np.packbits(pat)),
                "pattern_bits": pat.tolist(),
                "occurrences": len(hits),
                "first_offset": hits[0]["bit_offset"],
                "estimated_frame_length": period,
                "hits": hits[:5],
                "confidence": hits[0]["confidence"],
            })

    # If no known patterns matched, search for auto-correlated repeated 16/32-bit preambles
    if not detected and len(rx) >= 64:
        for p_len in [16, 32]:
            # Sliding search for repeated identical or near-identical slices
            tested = set()
            for off in range(0, min(len(rx) - 2 * p_len, 256), 4):
                cand = rx[off : off + p_len]
                cand_key = cand.tobytes()
                if cand_key in tested:
                    continue
                tested.add(cand_key)

                # Search rest of stream for repetitions of cand
                hits = search_sync_pattern(rx[off + p_len :], cand, max_errors=1)
                if len(hits) >= 2:
                    detected.append({
                        "label": f"CANDIDATE HEADER (Repeated {p_len}-bit pattern)",
                        "pattern_name": f"Discovered candidate ({p_len} bits)",
                        "pattern_hex": "0x" + "".join(f"{b:02X}" for b in np.packbits(cand)),
                        "pattern_bits": cand.tolist(),
                        "occurrences": len(hits) + 1,
                        "first_offset": off,
                        "estimated_frame_length": hits[0]["bit_offset"] + p_len,
                        "hits": hits[:5],
                        "confidence": 0.70,
                    })
                    break

    return detected
