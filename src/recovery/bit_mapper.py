"""
SIGMA - Symbol-to-Bit and Bit-to-Symbol Mapping Module
Implements standard Gray and natural mappings for:
- BPSK (1 bit/sym)
- QPSK (2 bits/sym)
- 8PSK (3 bits/sym)
- 16QAM (4 bits/sym)
- BFSK / 2-FSK (1 bit/sym)
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Union

# Standard Constellations (normalized unit average power)
CONSTELLATIONS = {
    "BPSK": np.array([1.0 + 0.0j, -1.0 + 0.0j], dtype=np.complex128),
    "QPSK": np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128) / np.sqrt(2.0),
    "8PSK": np.array([np.exp(1j * 2.0 * np.pi * k / 8.0) for k in range(8)], dtype=np.complex128),
    "16QAM": np.array([
        (i + 1j * q) for i in [-3.0, -1.0, 1.0, 3.0] for q in [-3.0, -1.0, 1.0, 3.0]
    ], dtype=np.complex128) / np.sqrt(10.0),
}

# Gray Bit Mappings: Map constellation index -> bit tuple
BIT_MAPPINGS = {
    "BPSK": {
        0: (0,),
        1: (1,),
    },
    "QPSK": {
        0: (0, 0),  # Quadrant 1 (+, +)
        1: (0, 1),  # Quadrant 2 (-, +)
        2: (1, 1),  # Quadrant 3 (-, -)
        3: (1, 0),  # Quadrant 4 (+, -)
    },
    "8PSK": {
        0: (0, 0, 0),
        1: (0, 0, 1),
        2: (0, 1, 1),
        3: (0, 1, 0),
        4: (1, 1, 0),
        5: (1, 1, 1),
        6: (1, 0, 1),
        7: (1, 0, 0),
    },
    # 16QAM Gray mapping (2 bits In-phase, 2 bits Quadrature)
    "16QAM": {
        idx: (
            (1 if (idx // 4) in [0, 1] else 0),
            (1 if (idx // 4) in [1, 2] else 0),
            (1 if (idx % 4) in [0, 1] else 0),
            (1 if (idx % 4) in [1, 2] else 0),
        )
        for idx in range(16)
    },
    "BFSK": {
        0: (0,),
        1: (1,),
    }
}


def get_constellation(modulation: str) -> Optional[np.ndarray]:
    """Retrieve constellation points array for modulation scheme."""
    mod = modulation.upper().replace(" ", "").replace("-", "")
    if "BPSK" in mod:
        return CONSTELLATIONS["BPSK"]
    elif "QPSK" in mod:
        return CONSTELLATIONS["QPSK"]
    elif "8PSK" in mod:
        return CONSTELLATIONS["8PSK"]
    elif "16QAM" in mod or "QAM" in mod:
        return CONSTELLATIONS["16QAM"]
    return None


def symbols_to_bits(
    symbols: np.ndarray,
    modulation: str = "BPSK"
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Slices complex received symbols to hard-decision bits using minimum Euclidean distance.

    Returns:
        (bits, symbol_indices, evm_percent)
    """
    mod_key = modulation.upper().replace(" ", "").replace("-", "")
    if "BFSK" in mod_key or "FSK" in mod_key:
        # FSK symbol slicing: symbols are expected as 1D decision variables (e.g. instantaneous frequency or discriminator output)
        real_syms = np.real(symbols)
        thresh = float(np.mean(real_syms))
        bits = (real_syms > thresh).astype(np.uint8)
        # Compute EVM-like metric from distance to cluster means
        c0 = float(np.mean(real_syms[bits == 0])) if np.any(bits == 0) else -1.0
        c1 = float(np.mean(real_syms[bits == 1])) if np.any(bits == 1) else 1.0
        target = np.where(bits == 1, c1, c0)
        evm = float(np.sqrt(np.mean((real_syms - target) ** 2)) / (abs(c1 - c0) + 1e-6) * 100.0)
        return bits, bits, evm

    const = get_constellation(modulation)
    if const is None:
        const = CONSTELLATIONS["BPSK"]
        mod_key = "BPSK"
    else:
        if "BPSK" in mod_key:
            mod_key = "BPSK"
        elif "QPSK" in mod_key:
            mod_key = "QPSK"
        elif "8PSK" in mod_key:
            mod_key = "8PSK"
        elif "16QAM" in mod_key or "QAM" in mod_key:
            mod_key = "16QAM"

    if len(symbols) == 0:
        return np.array([], dtype=np.uint8), np.array([], dtype=np.int32), 0.0

    # Euclidean distance to nearest constellation point
    diffs = symbols[:, np.newaxis] - const[np.newaxis, :]
    dists_sq = np.abs(diffs) ** 2
    best_indices = np.argmin(dists_sq, axis=1)

    # Compute EVM %: RMS error normalized by RMS reference constellation magnitude
    min_dists = np.min(dists_sq, axis=1)
    p_ref = np.mean(np.abs(const) ** 2)
    evm_percent = float(np.sqrt(np.mean(min_dists) / (p_ref + 1e-12)) * 100.0)

    # Map indices to bits
    mapping = BIT_MAPPINGS.get(mod_key, BIT_MAPPINGS["BPSK"])
    bit_chunks = [mapping.get(int(idx), (0,)) for idx in best_indices]
    bits = np.concatenate(bit_chunks).astype(np.uint8)

    return bits, best_indices, evm_percent


def bits_to_symbols(
    bits: Union[List[int], np.ndarray],
    modulation: str = "BPSK"
) -> np.ndarray:
    """
    Map bit array to ideal constellation symbols.
    """
    bits_arr = np.asarray(bits, dtype=np.uint8)
    mod_key = modulation.upper().replace(" ", "").replace("-", "")
    
    if "BFSK" in mod_key or "FSK" in mod_key:
        return (bits_arr * 2.0 - 1.0).astype(np.float64)

    const = get_constellation(modulation)
    if const is None:
        const = CONSTELLATIONS["BPSK"]
        mod_key = "BPSK"
    else:
        if "BPSK" in mod_key:
            mod_key = "BPSK"
        elif "QPSK" in mod_key:
            mod_key = "QPSK"
        elif "8PSK" in mod_key:
            mod_key = "8PSK"
        elif "16QAM" in mod_key or "QAM" in mod_key:
            mod_key = "16QAM"

    mapping = BIT_MAPPINGS.get(mod_key, BIT_MAPPINGS["BPSK"])
    # Invert mapping: bit tuple -> constellation index
    inv_map = {v: k for k, v in mapping.items()}
    bits_per_sym = len(next(iter(mapping.values())))

    # Pad with zeros if bits are not integer multiple of bits_per_sym
    rem = len(bits_arr) % bits_per_sym
    if rem != 0:
        bits_arr = np.pad(bits_arr, (0, bits_per_sym - rem), mode="constant")

    chunks = bits_arr.reshape(-1, bits_per_sym)
    indices = [inv_map.get(tuple(c), 0) for c in chunks]
    return const[indices]
