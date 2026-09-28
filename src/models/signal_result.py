"""
SIGMA - Unified Signal Result Model
Common data structure representing the full end-to-end Signal Intelligence pipeline:
Input -> Preprocessing -> Signal Metrics -> Modulation Classification ->
Synchronization & Demodulation -> De-interleaving -> FEC -> Correlation
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
import numpy as np


def _to_serializable(val: Any) -> Any:
    """Helper to convert NumPy and custom objects into JSON-serializable primitives."""
    if isinstance(val, (np.integer, int)):
        return int(val)
    elif isinstance(val, (np.floating, float)):
        return float(val) if not np.isnan(val) and not np.isinf(val) else None
    elif isinstance(val, np.ndarray):
        if np.issubdtype(val.dtype, np.complexfloating):
            return [{"r": float(x.real), "i": float(x.imag)} for x in val[:500]]
        return val[:1000].tolist()
    elif isinstance(val, (list, tuple)):
        return [_to_serializable(x) for x in val]
    elif isinstance(val, dict):
        return {k: _to_serializable(v) for k, v in val.items()}
    return val


@dataclass
class InputMetadata:
    file_type: str = "RAW IQ"
    filename: str = "--"
    filepath: Optional[str] = None
    sample_rate: float = 1000000.0
    center_frequency: float = 0.0
    bandwidth: Optional[float] = None
    num_samples: int = 0
    duration_seconds: float = 0.0
    format_name: str = "Complex Float32 (fc32)"


@dataclass
class SignalMetrics:
    snr_db: Optional[float] = None
    snr_str: str = "--"
    noise_floor_dbfs: Optional[float] = None
    signal_power_dbfs: Optional[float] = None
    rms_amplitude: Optional[float] = None
    peak_amplitude: Optional[float] = None
    peak_frequency_hz: Optional[float] = None
    symbol_rate_hz: Optional[float] = None
    symbol_rate_str: str = "--"
    samples_per_symbol: Optional[float] = None
    symbol_rate_lock: str = "NO LOCK"
    symbol_rate_prominence_db: float = 0.0


@dataclass
class ClassificationResult:
    modulation: str = "UNKNOWN"
    modulation_candidates: List[str] = field(default_factory=list)
    confidence_evidence: str = "indeterminate"  # provenance or confidence
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    demodulation_status: str = "NOT RUN"  # "LOCKED", "UNSUPPORTED", "DECLINED", "FAILED"
    synchronization_status: str = "NOT RUN"  # "LOCKED", "COARSE", "FAILED"
    modulation: str = "UNKNOWN"
    sps_used: Optional[float] = None
    evm_percent: Optional[float] = None
    carrier_offset_hz: Optional[float] = None
    residual_freq_hz: Optional[float] = None
    phase_offset_deg: Optional[float] = None
    n_symbols: int = 0
    symbols: List[complex] = field(default_factory=list)
    bits: List[int] = field(default_factory=list)
    bit_summary: str = "--"
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeinterleavingResult:
    status: str = "UNKNOWN"  # "SUCCESS", "UNKNOWN", "INSUFFICIENT DATA", "NOT DETECTED", "SKIPPED"
    mode: str = "NONE"  # "block", "convolutional", "diagonal", "pseudo_random", "none"
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    candidate_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    input_bit_count: int = 0
    output_bit_count: int = 0
    output_bits: List[int] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FECResult:
    status: str = "UNKNOWN"  # "SUPPORTED", "NOT DETECTED", "UNKNOWN", "INSUFFICIENT DATA", "DECODING FAILED"
    fec_type: str = "NONE"  # "convolutional", "reed_solomon", "concatenated", "ldpc", "none"
    candidate_codes: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    corrected_errors: int = 0
    residual: Optional[float] = None
    decoded_bits: List[int] = field(default_factory=list)
    decoded_bit_count: int = 0
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationResult:
    status: str = "UNKNOWN"  # "MATCH FOUND", "NO MATCH", "INSUFFICIENT DATA", "UNKNOWN"
    alignment_offset: Optional[int] = None
    similarity_score: Optional[float] = None
    candidate_headers: List[Dict[str, Any]] = field(default_factory=list)
    candidate_payload_regions: List[Dict[str, Any]] = field(default_factory=list)
    repeated_patterns: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalResult:
    """Master structured result for the SIGMA pipeline."""
    input_metadata: InputMetadata = field(default_factory=InputMetadata)
    signal_metrics: SignalMetrics = field(default_factory=SignalMetrics)
    classification: ClassificationResult = field(default_factory=ClassificationResult)
    recovery: RecoveryResult = field(default_factory=RecoveryResult)
    deinterleaving: DeinterleavingResult = field(default_factory=DeinterleavingResult)
    fec: FECResult = field(default_factory=FECResult)
    correlation: CorrelationResult = field(default_factory=CorrelationResult)
    overall_status: str = "INITIALIZED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire hierarchy to standard dictionary with serializable values."""
        raw = asdict(self)
        return _to_serializable(raw)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """Generate human-readable multi-line summary string."""
        lines = [
            f"=== SIGMA Intelligence Summary for {self.input_metadata.filename} ===",
            f"Format: {self.input_metadata.file_type} | Rate: {self.input_metadata.sample_rate:,.0f} S/s",
            f"SNR: {self.signal_metrics.snr_str} | Symbol Rate: {self.signal_metrics.symbol_rate_str} ({self.signal_metrics.symbol_rate_lock})",
            f"Modulation: {self.classification.modulation} ({self.classification.confidence_evidence})",
            f"Demodulation: {self.recovery.demodulation_status} ({self.recovery.n_symbols} sym, {len(self.recovery.bits)} bits)",
            f"De-interleaving: {self.deinterleaving.status} (Mode: {self.deinterleaving.mode})",
            f"FEC Decoding: {self.fec.status} (Type: {self.fec.fec_type}, Errors: {self.fec.corrected_errors})",
            f"Correlation: {self.correlation.status} (Candidate Headers: {len(self.correlation.candidate_headers)})",
        ]
        return "\n".join(lines)
