"""
SIGMA - Signal Recovery Pipeline
Orchestrates:
Signal -> Synchronization -> Demodulation -> Symbol-to-Bit Mapping -> Quality Diagnostics
"""

import numpy as np
from typing import Dict, Any, Optional, Union

from .synchronizer import estimate_symbol_timing, estimate_frequency_offset
from .demodulators import demodulate
try:
    from models.signal_result import RecoveryResult
except ImportError:
    from ..models.signal_result import RecoveryResult


def run_recovery_pipeline(
    signal_iq: np.ndarray,
    modulation: Optional[str] = None,
    sample_rate: float = 1000000.0,
    symbol_rate: Optional[float] = None,
    sps: Optional[float] = None
) -> RecoveryResult:
    """
    Run the end-to-end recovery pipeline on complex IQ samples.
    """
    rec_res = RecoveryResult()

    if signal_iq is None or len(signal_iq) == 0:
        rec_res.demodulation_status = "FAILED"
        rec_res.synchronization_status = "FAILED"
        rec_res.diagnostics = {"reason": "Empty signal input"}
        return rec_res

    # 1. Synchronization & Symbol Timing
    detected_sps, best_phase, timing_diag = estimate_symbol_timing(
        signal_iq, sample_rate, sps=sps
    )
    rec_res.sps_used = detected_sps
    rec_res.synchronization_status = "LOCKED" if timing_diag.get("confidence") in ["MEDIUM", "HIGH", "USER_PROVIDED"] else "COARSE"

    target_mod = modulation or "BPSK"

    # 2. Demodulation & Bit Decision
    demod_out = demodulate(
        signal_iq,
        modulation=target_mod,
        sample_rate=sample_rate,
        symbol_rate=symbol_rate,
        sps=detected_sps
    )

    rec_res.modulation = demod_out.get("modulation", target_mod)
    diag = demod_out.get("diagnostics", {})
    rec_res.diagnostics = diag

    if diag.get("locked", False):
        rec_res.demodulation_status = "LOCKED"
        symbols = demod_out.get("symbols", [])
        bits = demod_out.get("bits", [])

        rec_res.symbols = symbols[:1000] if isinstance(symbols, list) else list(symbols[:1000])
        rec_res.bits = bits if isinstance(bits, list) else list(bits)
        rec_res.n_symbols = len(symbols)

        rec_res.evm_percent = diag.get("evm_percent")
        rec_res.carrier_offset_hz = diag.get("carrier_offset_hz")
        rec_res.residual_freq_hz = diag.get("residual_freq_hz")

        # Format summary of first 48 bits in nibbles
        if bits:
            first_bits = "".join(str(b) for b in bits[:48])
            rec_res.bit_summary = " ".join(first_bits[i:i+4] for i in range(0, len(first_bits), 4))
    else:
        rec_res.demodulation_status = "DECLINED" if "declined" in str(diag.get("reason", "")).lower() else "FAILED"
        rec_res.symbols = []
        rec_res.bits = []
        rec_res.bit_summary = "--"

    return rec_res
