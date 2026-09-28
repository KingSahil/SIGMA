"""
SIGMA - Forward Error Correction (FEC) Package
"""

from .convolutional import (
    encode_convolutional,
    decode_viterbi,
    search_convolutional_code,
)
from .reed_solomon import (
    encode_reed_solomon,
    decode_reed_solomon,
    bits_to_bytes,
    bytes_to_bits,
)
from .concatenated import (
    encode_concatenated,
    decode_concatenated,
)
from .ldpc import (
    encode_ldpc,
    decode_ldpc,
    make_regular_ldpc_h,
    check_syndrome,
)
from .dispatcher import decode_fec

__all__ = [
    "encode_convolutional",
    "decode_viterbi",
    "search_convolutional_code",
    "encode_reed_solomon",
    "decode_reed_solomon",
    "bits_to_bytes",
    "bytes_to_bits",
    "encode_concatenated",
    "decode_concatenated",
    "encode_ldpc",
    "decode_ldpc",
    "make_regular_ldpc_h",
    "check_syndrome",
    "decode_fec",
]
