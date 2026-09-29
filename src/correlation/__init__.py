"""
SIGMA - Bitstream Correlation Package
"""

from .bitstream import (
    hamming_distance,
    compute_ber,
    bits_to_hex,
    format_spaced_bits,
)
from .alignment import align_bitstreams
from .header_detection import (
    chance_threshold,
    search_sync_pattern,
    detect_candidate_headers,
    KNOWN_SYNC_WORDS,
)
from .payload_detection import (
    compute_bit_entropy,
    extract_candidate_payloads,
)
from .scoring import correlate_bitstreams

__all__ = [
    "hamming_distance",
    "compute_ber",
    "bits_to_hex",
    "format_spaced_bits",
    "align_bitstreams",
    "chance_threshold",
    "search_sync_pattern",
    "detect_candidate_headers",
    "KNOWN_SYNC_WORDS",
    "compute_bit_entropy",
    "extract_candidate_payloads",
    "correlate_bitstreams",
]
