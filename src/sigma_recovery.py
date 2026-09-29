"""
SIGMA - Complete Signal Recovery & Intelligence Orchestrator
Coordinates the end-to-end signal pipeline:
RAW .IQ / .WAV
        ↓
PRE-PROCESSING (WAV-to-IQ conversion, sample loading)
        ↓
PARAMETER IDENTIFICATION (SNR, OBW, Noise Floor, Peak Freq, Symbol Rate)
        ↓
MODULATION CLASSIFICATION (BPSK, QPSK, 8PSK, 16QAM, FSK, AM/FM)
        ↓
SYNCHRONIZATION (Carrier offset, symbol timing phase)
        ↓
DEMODULATION (FSK / PSK / QAM decision slicing)
        ↓
DE-INTERLEAVING (Block, Convolutional, Diagonal, Pseudo-Random)
        ↓
FEC DECODING (Viterbi, Reed-Solomon, Concatenated, LDPC)
        ↓
RECOVERED BITSTREAM
        ↓
BITSTREAM CORRELATION & CANDIDATE HEADERS/PAYLOAD
        ↓
STRUCTURED SIGNAL INTELLIGENCE RESULT

Strict Gating Rules:
- If symbol rate has no lock, demodulation is declined rather than sampling on an untrusted clock.
- If modulation cannot be identified, report "UNKNOWN" rather than guessing a decoder.
- If FEC cannot be identified, report "NOT DETECTED" rather than inventing a payload.
"""

import os
import numpy as np
from typing import Dict, Any, Optional, Union

try:
    from sigma_analyzer_core import SignalMetadata, load_and_convert_wav
    from sigma_symbol_rate import estimate_symbol_rate
    from sigma_sample_rate import estimate_sample_rate
except ImportError:
    try:
        from .sigma_analyzer_core import SignalMetadata, load_and_convert_wav
        from .sigma_symbol_rate import estimate_symbol_rate
        from .sigma_sample_rate import estimate_sample_rate
    except (ImportError, ValueError):
        SignalMetadata = None
        load_and_convert_wav = None
        estimate_symbol_rate = None
        estimate_sample_rate = None

try:
    from models.signal_result import (
        SignalResult,
        InputMetadata,
        SignalMetrics,
        ClassificationResult,
        RecoveryResult,
        DeinterleavingResult,
        FECResult,
        CorrelationResult,
    )
    from recovery.recovery_pipeline import run_recovery_pipeline
    from recovery.demodulators import demodulate
    from deinterleaving.dispatcher import deinterleave
    from fec.dispatcher import decode_fec
    from correlation.scoring import correlate_bitstreams
except ImportError:
    from .models.signal_result import (
        SignalResult,
        InputMetadata,
        SignalMetrics,
        ClassificationResult,
        RecoveryResult,
        DeinterleavingResult,
        FECResult,
        CorrelationResult,
    )
    from .recovery.recovery_pipeline import run_recovery_pipeline
    from .recovery.demodulators import demodulate
    from .deinterleaving.dispatcher import deinterleave
    from .fec.dispatcher import decode_fec
    from .correlation.scoring import correlate_bitstreams


def orchestrate_signal_recovery(
    input_path: str,
    user_sample_rate: Optional[float] = None,
    user_center_freq: float = 0.0,
    forced_modulation: Optional[str] = None,
    interleave_mode: Optional[str] = None,
    interleave_params: Optional[Dict[str, Any]] = None,
    fec_type: Optional[str] = None,
    fec_params: Optional[Dict[str, Any]] = None,
    reference_bitstream: Optional[Union[list, np.ndarray]] = None,
    max_samples: int = 400_000,
) -> SignalResult:
    """
    Executes the complete, end-to-end intelligence recovery pipeline.
    """
    res = SignalResult()
    res.input_metadata.filepath = input_path
    res.input_metadata.filename = os.path.basename(input_path) if input_path else "--"
    res.input_metadata.center_frequency = user_center_freq

    if not input_path or not os.path.exists(input_path):
        res.overall_status = "FILE NOT FOUND"
        res.recovery.demodulation_status = "FAILED"
        res.recovery.diagnostics = {"reason": f"File does not exist: {input_path}"}
        return res

    # 1. INPUT & PREPROCESSING (WAV vs IQ)
    working_iq_path = input_path
    sample_rate = user_sample_rate or 1000000.0

    if input_path.lower().endswith(".wav"):
        res.input_metadata.file_type = "WAV Audio / Stereo IQ"
        if load_and_convert_wav is not None:
            conv_path, wav_sr, num_smp, is_stereo = load_and_convert_wav(input_path)
            working_iq_path = conv_path
            if user_sample_rate is None:
                sample_rate = float(wav_sr)
            res.input_metadata.format_name = "Stereo IQ (WAV)" if is_stereo else "Mono Audio (WAV)"
    else:
        res.input_metadata.file_type = "RAW IQ Binary"
        res.input_metadata.format_name = "Complex Float32 (fc32)"

    res.input_metadata.sample_rate = sample_rate

    # 2. PARAMETER IDENTIFICATION & METRICS
    meta = None
    if SignalMetadata is not None:
        try:
            meta = SignalMetadata(filepath=working_iq_path, samp_rate=sample_rate, center_freq=user_center_freq)
            res.input_metadata.num_samples = meta.num_samples
            res.input_metadata.duration_seconds = meta.duration_seconds
            res.signal_metrics.rms_amplitude = float(meta.rms_amplitude) if meta.rms_amplitude != "--" else None
            res.signal_metrics.peak_amplitude = float(meta.peak_amplitude) if meta.peak_amplitude != "--" else None
            res.signal_metrics.snr_str = meta.snr
            res.signal_metrics.symbol_rate_str = meta.symbol_rate
            res.signal_metrics.symbol_rate_lock = getattr(meta, "symbol_rate_confidence", "NO LOCK")
            res.classification.modulation = meta.modulation_class
            res.classification.confidence_evidence = meta.modulation_source
        except Exception as e:
            print(f"[SIGMA Recovery] Metadata extraction error: {e}")

    # Read samples
    samples = np.fromfile(working_iq_path, dtype=np.complex64, count=max_samples)
    if len(samples) == 0:
        res.overall_status = "EMPTY FILE"
        return res

    # 3. MODULATION CLASSIFICATION
    mod = forced_modulation or res.classification.modulation
    if mod in ["Not analyzed", "CW / Unmodulated", "AM / ASK", "Audio Baseband", "--"]:
        # If classification is ambiguous or analogue, test digital constellation fit
        pass

    # 4. SYNCHRONIZATION & DEMODULATION
    sr_res = getattr(meta, "symbol_rate_result", None) if meta else None
    if sr_res is None and estimate_symbol_rate is not None:
        sr_res = estimate_symbol_rate(samples, sample_rate)

    sps = None
    if sr_res and sr_res.get("locked"):
        sps = float(sr_res["samples_per_symbol"])
        res.signal_metrics.samples_per_symbol = sps
        res.signal_metrics.symbol_rate_hz = float(sr_res.get("symbol_rate_hz", 0.0))
        res.signal_metrics.symbol_rate_lock = sr_res.get("confidence_label", "LOCKED")
        res.signal_metrics.symbol_rate_prominence_db = float(sr_res.get("prominence_db", 0.0))

    # Gating: refuse demodulation if symbol rate lock is untrusted or missing
    if (sps is None or sr_res.get("confidence_label") == "LOW") and not forced_modulation:
        res.recovery.demodulation_status = "DECLINED"
        res.recovery.diagnostics = {
            "reason": "Declined: Symbol rate lock is insufficient or LOW. Demodulating would sample on an untrusted clock."
        }
        res.deinterleaving.status = "SKIPPED"
        res.fec.status = "SKIPPED"
        res.correlation.status = "SKIPPED"
        res.overall_status = "DSP ANALYSIS COMPLETE (DEMOD DECLINED)"
        return res

    # Run Recovery
    rec_out = run_recovery_pipeline(
        samples,
        modulation=mod,
        sample_rate=sample_rate,
        sps=sps,
    )
    res.recovery = rec_out

    if rec_out.demodulation_status != "LOCKED" or not rec_out.bits:
        res.deinterleaving.status = "INSUFFICIENT DATA"
        res.fec.status = "INSUFFICIENT DATA"
        res.correlation.status = "INSUFFICIENT DATA"
        res.overall_status = f"DEMODULATION {rec_out.demodulation_status}"
        return res

    demod_bits = np.asarray(rec_out.bits, dtype=np.uint8)

    # 5. DE-INTERLEAVING
    deint_out = deinterleave(
        demod_bits,
        mode=interleave_mode or "unknown",
        parameters=interleave_params
    )
    res.deinterleaving.mode = deint_out.get("mode", "NONE")
    res.deinterleaving.status = deint_out.get("status", "UNKNOWN").upper()
    res.deinterleaving.parameters = deint_out.get("parameters", {})
    res.deinterleaving.confidence = deint_out.get("confidence")
    res.deinterleaving.input_bit_count = len(demod_bits)
    res.deinterleaving.output_bits = deint_out.get("output_bits", [])
    res.deinterleaving.output_bit_count = len(res.deinterleaving.output_bits)
    res.deinterleaving.diagnostics = deint_out.get("diagnostics", {})

    bits_for_fec = np.asarray(res.deinterleaving.output_bits, dtype=np.uint8)

    # 6. FEC DECODING
    fec_out = decode_fec(
        bits_for_fec,
        fec_type=fec_type,
        parameters=fec_params
    )
    res.fec.fec_type = fec_out.get("fec_type", "NONE")
    res.fec.status = fec_out.get("status", "UNKNOWN")
    res.fec.corrected_errors = fec_out.get("corrected_errors", 0)
    res.fec.residual = fec_out.get("residual")
    res.fec.decoded_bits = fec_out.get("decoded_bits", [])
    res.fec.decoded_bit_count = len(res.fec.decoded_bits)
    res.fec.diagnostics = fec_out.get("diagnostics", {})

    # Final bitstream for correlation: decoded bits if FEC succeeded, otherwise deinterleaved/demod bits
    final_bits = np.asarray(res.fec.decoded_bits) if res.fec.status == "SUPPORTED" and len(res.fec.decoded_bits) > 0 else bits_for_fec

    # 7. BITSTREAM CORRELATION, HEADER & PAYLOAD
    corr_out = correlate_bitstreams(
        final_bits,
        stream_b=reference_bitstream
    )
    res.correlation.alignment_offset = corr_out.get("alignment")
    res.correlation.similarity_score = corr_out.get("similarity")
    res.correlation.candidate_headers = corr_out.get("candidate_headers", [])
    res.correlation.candidate_payload_regions = corr_out.get("candidate_payload_regions", [])
    res.correlation.status = corr_out.get("status", "UNKNOWN")
    res.correlation.diagnostics = corr_out.get("diagnostics", {})

    res.overall_status = "RECOVERY COMPLETE"
    return res
