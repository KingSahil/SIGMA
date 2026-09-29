"""
SIGMA - Signal Demodulators Module
Implements demodulation for:
1. FSK (2-FSK / BFSK) with frequency discrimination & symbol decisions
2. PSK (BPSK, QPSK, 8PSK)
3. QAM (16-QAM)

Returns standardized result dictionary:
{
    "modulation": str,
    "symbols": List[complex] | List[float],
    "bits": List[int],
    "confidence": float | None,
    "diagnostics": Dict[str, Any]
}
"""

import numpy as np
from typing import Dict, Any, Optional, Union, List

try:
    from sigma_demod import (
        demodulate as sigma_demod_func,
        rrc_filter,
        classify_constellation,
    )
except ImportError:
    try:
        from ..sigma_demod import (
            demodulate as sigma_demod_func,
            rrc_filter,
            classify_constellation,
        )
    except (ImportError, ValueError):
        sigma_demod_func = None
        rrc_filter = None
        classify_constellation = None

from .bit_mapper import symbols_to_bits, CONSTELLATIONS, get_constellation
from .synchronizer import estimate_frequency_offset, estimate_symbol_timing, phase_align


def demodulate_fsk(
    signal_iq: np.ndarray,
    samp_rate: float,
    symbol_rate: Optional[float] = None,
    sps: Optional[float] = None,
    deviation_hz: Optional[float] = None
) -> Dict[str, Any]:
    """
    Demodulate 2-FSK / BFSK using instantaneous frequency discrimination.
    """
    x = np.asarray(signal_iq, dtype=np.complex64)
    if len(x) < 32:
        return {
            "modulation": "BFSK",
            "symbols": [],
            "bits": [],
            "confidence": None,
            "diagnostics": {"reason": "insufficient samples", "locked": False}
        }

    # 1. Resolve SPS
    if sps is None or sps <= 1.0:
        if symbol_rate and symbol_rate > 0:
            sps = samp_rate / symbol_rate
        else:
            sps, _, _ = estimate_symbol_timing(x, samp_rate)
    
    sps_int = max(2, int(round(sps)))

    # 2. Instantaneous Frequency Discrimination via complex conjugate product
    # freq_inst[n] = (samp_rate / 2*pi) * angle(x[n] * conj(x[n-1]))
    prod = x[1:] * np.conj(x[:-1])
    inst_freq = np.angle(prod) * (samp_rate / (2.0 * np.pi))

    # 3. Low-pass / boxcar filter matching symbol period
    kernel = np.ones(sps_int, dtype=np.float32) / sps_int
    filtered = np.convolve(inst_freq, kernel, mode="valid")

    # 4. Symbol timing decimation
    # Pick optimal sampling offset by maximizing bimodal peak separation
    best_phase = 0
    max_kurt = -1.0
    for p in range(sps_int):
        sub = filtered[p::sps_int]
        if len(sub) > 16:
            m2 = np.mean((sub - np.mean(sub)) ** 2)
            m4 = np.mean((sub - np.mean(sub)) ** 4)
            kurt = m4 / (m2 ** 2 + 1e-12) if m2 > 1e-12 else 0.0
            if kurt > max_kurt:
                max_kurt = kurt
                best_phase = p

    decimated_symbols = filtered[best_phase::sps_int]

    # 5. Slicing
    center_freq = float(np.median(decimated_symbols))
    bits = (decimated_symbols > center_freq).astype(np.uint8)

    # 6. Confidence / SNR metric
    f0 = np.mean(decimated_symbols[bits == 0]) if np.any(bits == 0) else center_freq - 1.0
    f1 = np.mean(decimated_symbols[bits == 1]) if np.any(bits == 1) else center_freq + 1.0
    freq_separation = abs(float(f1 - f0))

    noise_var = float(np.var(decimated_symbols - np.where(bits == 1, f1, f0)))
    snr_fsk = freq_separation / (np.sqrt(noise_var) + 1e-6) if noise_var > 0 else 10.0
    
    # Confidence between 0.0 and 1.0
    conf = float(np.clip(1.0 - (1.0 / (1.0 + snr_fsk)), 0.0, 1.0))
    locked = bool(freq_separation > 0.01 * samp_rate and len(bits) > 0)

    return {
        "modulation": "BFSK",
        "symbols": decimated_symbols.tolist(),
        "bits": bits.tolist(),
        "confidence": conf if locked else None,
        "diagnostics": {
            "locked": locked,
            "center_freq_hz": center_freq,
            "mark_freq_hz": float(f1),
            "space_freq_hz": float(f0),
            "freq_separation_hz": freq_separation,
            "sps": sps,
            "snr_metric": snr_fsk,
        }
    }


def demodulate_psk(
    signal_iq: np.ndarray,
    samp_rate: float,
    modulation: str = "BPSK",
    sps: Optional[float] = None
) -> Dict[str, Any]:
    """
    Demodulate PSK family (BPSK, QPSK, 8PSK).
    Reuses sigma_demod when available, with fallback to synchronizer + bit_mapper.
    """
    mod_name = modulation.upper().replace(" ", "").replace("-", "")
    if "8PSK" in mod_name:
        canon_mod = "8PSK"
    elif "QPSK" in mod_name:
        canon_mod = "QPSK"
    else:
        canon_mod = "BPSK"

    # Attempt existing high-precision sigma_demod engine first
    if sigma_demod_func is not None:
        res = sigma_demod_func(signal_iq, samp_rate, modulation=canon_mod, sps=sps)
        if res.locked:
            conf = float(np.clip(1.0 - (res.evm_percent / 100.0), 0.0, 1.0))
            return {
                "modulation": canon_mod,
                "symbols": res.symbols.tolist() if res.symbols is not None else [],
                "bits": res.bits.tolist() if res.bits is not None else [],
                "confidence": conf,
                "diagnostics": {
                    "locked": True,
                    "evm_percent": res.evm_percent,
                    "carrier_offset_hz": res.carrier_offset_hz,
                    "residual_freq_hz": res.residual_freq_hz,
                    "sps_used": res.sps,
                    "n_symbols": res.n_symbols,
                }
            }

    # Fallback DSP pipeline
    x = np.asarray(signal_iq, dtype=np.complex128)
    if sps is None:
        sps, _, _ = estimate_symbol_timing(x, samp_rate)
    
    order = 2 if canon_mod == "BPSK" else (4 if canon_mod == "QPSK" else 8)
    f_off = estimate_frequency_offset(x, samp_rate, symmetry_order=order)
    
    # Correct carrier
    t = np.arange(len(x)) / samp_rate
    derotated = x * np.exp(-1j * 2.0 * np.pi * f_off * t)

    # RRC matched filtering
    sps_int = max(2, int(round(sps)))
    if rrc_filter is not None:
        h = rrc_filter(sps_int, alpha=0.35)
        filtered = np.convolve(derotated, h, mode="same")
    else:
        filtered = derotated

    _, best_phase, _ = estimate_symbol_timing(filtered, samp_rate, sps=sps)
    symbols = filtered[best_phase::sps_int]

    # Constellation alignment
    const = CONSTELLATIONS[canon_mod]
    aligned_symbols, phase_deg = phase_align(symbols, const, symmetry_order=order)

    bits, _, evm = symbols_to_bits(aligned_symbols, modulation=canon_mod)
    locked = bool(evm < 45.0 and len(bits) > 0)

    conf = float(np.clip(1.0 - (evm / 100.0), 0.0, 1.0)) if locked else None

    return {
        "modulation": canon_mod,
        "symbols": aligned_symbols.tolist(),
        "bits": bits.tolist(),
        "confidence": conf,
        "diagnostics": {
            "locked": locked,
            "evm_percent": evm,
            "carrier_offset_hz": f_off,
            "phase_deg": phase_deg,
            "sps_used": sps,
            "n_symbols": len(symbols),
        }
    }


def demodulate_qam(
    signal_iq: np.ndarray,
    samp_rate: float,
    modulation: str = "16QAM",
    sps: Optional[float] = None
) -> Dict[str, Any]:
    """
    Demodulate 16-QAM signals.
    """
    canon_mod = "16QAM"
    if sigma_demod_func is not None:
        res = sigma_demod_func(signal_iq, samp_rate, modulation=canon_mod, sps=sps)
        if res.locked:
            conf = float(np.clip(1.0 - (res.evm_percent / 100.0), 0.0, 1.0))
            return {
                "modulation": canon_mod,
                "symbols": res.symbols.tolist() if res.symbols is not None else [],
                "bits": res.bits.tolist() if res.bits is not None else [],
                "confidence": conf,
                "diagnostics": {
                    "locked": True,
                    "evm_percent": res.evm_percent,
                    "carrier_offset_hz": res.carrier_offset_hz,
                    "residual_freq_hz": res.residual_freq_hz,
                    "sps_used": res.sps,
                    "n_symbols": res.n_symbols,
                }
            }

    x = np.asarray(signal_iq, dtype=np.complex128)
    if sps is None:
        sps, _, _ = estimate_symbol_timing(x, samp_rate)
    
    f_off = estimate_frequency_offset(x, samp_rate, symmetry_order=4)
    t = np.arange(len(x)) / samp_rate
    derotated = x * np.exp(-1j * 2.0 * np.pi * f_off * t)

    sps_int = max(2, int(round(sps)))
    if rrc_filter is not None:
        h = rrc_filter(sps_int, alpha=0.35)
        filtered = np.convolve(derotated, h, mode="same")
    else:
        filtered = derotated

    _, best_phase, _ = estimate_symbol_timing(filtered, samp_rate, sps=sps)
    symbols = filtered[best_phase::sps_int]

    # Normalize symbol energy
    p_avg = np.mean(np.abs(symbols) ** 2)
    if p_avg > 1e-12:
        symbols /= np.sqrt(p_avg)

    const = CONSTELLATIONS["16QAM"]
    aligned_symbols, phase_deg = phase_align(symbols, const, symmetry_order=4)
    bits, _, evm = symbols_to_bits(aligned_symbols, modulation="16QAM")

    locked = bool(evm < 40.0 and len(bits) > 0)
    conf = float(np.clip(1.0 - (evm / 100.0), 0.0, 1.0)) if locked else None

    return {
        "modulation": canon_mod,
        "symbols": aligned_symbols.tolist(),
        "bits": bits.tolist(),
        "confidence": conf,
        "diagnostics": {
            "locked": locked,
            "evm_percent": evm,
            "carrier_offset_hz": f_off,
            "phase_deg": phase_deg,
            "sps_used": sps,
            "n_symbols": len(symbols),
        }
    }


def demodulate(
    signal: np.ndarray,
    modulation: str = "BPSK",
    sample_rate: float = 1000000.0,
    symbol_rate: Optional[float] = None,
    sps: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified demodulator entrypoint supporting FSK, PSK, and QAM.
    """
    mod_str = modulation.upper().replace(" ", "").replace("-", "")

    if "FSK" in mod_str:
        return demodulate_fsk(signal, samp_rate=sample_rate, symbol_rate=symbol_rate, sps=sps)
    elif "16QAM" in mod_str or "QAM" in mod_str:
        return demodulate_qam(signal, samp_rate=sample_rate, modulation="16QAM", sps=sps)
    elif "8PSK" in mod_str:
        return demodulate_psk(signal, samp_rate=sample_rate, modulation="8PSK", sps=sps)
    elif "QPSK" in mod_str:
        return demodulate_psk(signal, samp_rate=sample_rate, modulation="QPSK", sps=sps)
    elif "BPSK" in mod_str:
        return demodulate_psk(signal, samp_rate=sample_rate, modulation="BPSK", sps=sps)
    else:
        # Unknown or unspecified modulation: try BPSK then QPSK then BFSK
        res = demodulate_psk(signal, samp_rate=sample_rate, modulation="BPSK", sps=sps)
        if res.get("diagnostics", {}).get("locked"):
            return res
        res_fsk = demodulate_fsk(signal, samp_rate=sample_rate, symbol_rate=symbol_rate, sps=sps)
        if res_fsk.get("diagnostics", {}).get("locked"):
            return res_fsk
        return {
            "modulation": modulation,
            "symbols": [],
            "bits": [],
            "confidence": None,
            "diagnostics": {
                "reason": f"Modulation '{modulation}' not recognized or unable to lock",
                "locked": False
            }
        }
