"""
SIGMA - Signal Synchronization Module
Provides reusable synchronization routines:
- Symbol timing estimation & clock recovery (max eye-opening / Gardner / Mueller-Muller)
- Carrier frequency offset estimation (M-th power / Doppler estimation)
- Phase alignment & constellation rotation correction

Works directly in coordination with sigma_symbol_rate.py and sigma_demod.py.
"""

import numpy as np
from typing import Tuple, Dict, Any, Optional

try:
    from sigma_symbol_rate import estimate_symbol_rate
except ImportError:
    try:
        from ..sigma_symbol_rate import estimate_symbol_rate
    except (ImportError, ValueError):
        estimate_symbol_rate = None


def estimate_frequency_offset(
    x: np.ndarray,
    samp_rate: float,
    symmetry_order: int = 4,
    refine: bool = True
) -> float:
    """
    Estimate residual carrier frequency offset using M-th power non-linear method.
    Raising complex baseband x[n] to power M collapses M-fold rotationally
    symmetric constellations (BPSK: 2, QPSK: 4, 8PSK: 8, 16QAM: 4) into a pure tone.
    """
    if len(x) < 256:
        return 0.0

    n = min(len(x), 16384)
    seg = np.asarray(x[:n], dtype=np.complex128)
    
    # Repeated multiplication to avoid numerical issues
    powered = seg.copy()
    for _ in range(symmetry_order - 1):
        powered = powered * seg

    # Apply Hanning window to reduce spectral leakage
    win = np.hanning(n)
    spec = np.abs(np.fft.fftshift(np.fft.fft(powered * win))) ** 2
    freqs = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / samp_rate))

    peak_idx = int(np.argmax(spec))
    f_peak = float(freqs[peak_idx])

    # Parabolic sub-bin interpolation
    if refine and 0 < peak_idx < len(spec) - 1:
        y0 = float(np.log(spec[peak_idx - 1] + 1e-30))
        y1 = float(np.log(spec[peak_idx] + 1e-30))
        y2 = float(np.log(spec[peak_idx + 1] + 1e-30))
        denom = y0 - 2.0 * y1 + y2
        if abs(denom) > 1e-30:
            delta = 0.5 * (y0 - y2) / denom
            if abs(delta) < 1.0:
                bin_width = samp_rate / float(n)
                f_peak += float(delta * bin_width)

    # Carrier offset is f_peak divided by symmetry order M
    offset = float(f_peak / symmetry_order)
    return offset


def estimate_symbol_timing(
    x: np.ndarray,
    samp_rate: float,
    sps: Optional[float] = None
) -> Tuple[float, int, Dict[str, Any]]:
    """
    Estimate symbol timing:
    1. If sps is not provided, estimate symbol rate via cyclostationary envelope.
    2. Find the optimal sampling phase offset (0 <= phase < sps) that maximizes eye opening / signal variance.

    Returns:
        (sps, best_phase, diagnostics)
    """
    diag = {}
    if sps is None or sps <= 1.0:
        if estimate_symbol_rate is not None:
            sr_res = estimate_symbol_rate(x, samp_rate)
            if sr_res.get("locked"):
                sps = float(sr_res["samples_per_symbol"])
                diag["symbol_rate"] = sr_res["symbol_rate_hz"]
                diag["confidence"] = sr_res.get("confidence_label", "MEDIUM")
            else:
                sps = 4.0  # safe default fallback
                diag["confidence"] = "NO LOCK"
        else:
            sps = 4.0
            diag["confidence"] = "DEFAULT"
    else:
        diag["confidence"] = "USER_PROVIDED"

    sps_int = max(1, int(round(sps)))
    if sps_int <= 1 or len(x) < sps_int * 8:
        return sps, 0, diag

    # Find sampling phase by maximizing variance of sample magnitudes across decimation phases
    best_phase = 0
    max_dispersion = -1.0

    n_test = min(len(x), 8192)
    test_seg = x[:n_test]

    for p in range(sps_int):
        sub = np.abs(test_seg[p::sps_int])
        if len(sub) > 8:
            # Dispersion / kurtosis peak at optimum symbol decision point
            disp = float(np.var(sub) / (np.mean(sub) ** 2 + 1e-12))
            if disp > max_dispersion:
                max_dispersion = disp
                best_phase = p

    diag["best_phase"] = best_phase
    diag["dispersion_metric"] = max_dispersion
    diag["sps"] = sps

    return sps, best_phase, diag


def phase_align(
    symbols: np.ndarray,
    constellation_points: np.ndarray,
    symmetry_order: int = 4
) -> Tuple[np.ndarray, float]:
    """
    Align the constellation phase by evaluating residual rotations
    (0, 2*pi/M, 4*pi/M, ... (M-1)*2*pi/M) and minimizing mean distance to closest points.

    Returns:
        (aligned_symbols, phase_correction_deg)
    """
    if len(symbols) == 0 or len(constellation_points) == 0:
        return symbols, 0.0

    # First find average angle offset
    angles = np.angle(symbols)
    m_angles = np.mod(angles * symmetry_order, 2.0 * np.pi)
    # Circular mean
    mean_angle = np.arctan2(np.mean(np.sin(m_angles)), np.mean(np.cos(m_angles))) / symmetry_order

    derotated = symbols * np.exp(-1j * mean_angle)

    # Now test the discrete ambiguity rotations
    best_rot = 0.0
    min_dist = float("inf")
    rot_step = 2.0 * np.pi / symmetry_order

    for k in range(symmetry_order):
        rot = k * rot_step
        candidate = derotated * np.exp(-1j * rot)

        # Vectorized Euclidean distance to nearest constellation symbol
        diffs = candidate[:, np.newaxis] - constellation_points[np.newaxis, :]
        dists = np.min(np.abs(diffs), axis=1)
        mean_d = float(np.mean(dists))

        if mean_d < min_dist:
            min_dist = mean_d
            best_rot = rot

    total_correction = float(mean_angle + best_rot)
    aligned = symbols * np.exp(-1j * total_correction)
    deg = float(np.degrees(total_correction) % 360.0)

    return aligned, deg
