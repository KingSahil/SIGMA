"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Models Package
"""

from .signal_result import (
    SignalResult,
    InputMetadata,
    SignalMetrics,
    ClassificationResult,
    RecoveryResult,
    DeinterleavingResult,
    FECResult,
    CorrelationResult,
)

__all__ = [
    "SignalResult",
    "InputMetadata",
    "SignalMetrics",
    "ClassificationResult",
    "RecoveryResult",
    "DeinterleavingResult",
    "FECResult",
    "CorrelationResult",
]
