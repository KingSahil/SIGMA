"""
SIGMA - CSV Export Module
Exports signal metrics, bitstream, decoded payload, and correlation scores to CSV tables.
"""

import csv
try:
    from models.signal_result import SignalResult
except ImportError:
    from ..models.signal_result import SignalResult


def export_to_csv(result: Union[SignalResult, Dict[str, Any]], filepath: str) -> str:
    """Exports signal parameters and recovered bitstream data to CSV."""
    if isinstance(result, SignalResult):
        data = result.to_dict()
    else:
        data = dict(result)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(["Section", "Parameter", "Value"])

        # Input metadata
        inp = data.get("input_metadata", {})
        for k, v in inp.items():
            writer.writerow(["Input", k, v])

        # Signal metrics
        metrics = data.get("signal_metrics", {})
        for k, v in metrics.items():
            writer.writerow(["Metrics", k, v])

        # Classification
        cls = data.get("classification", {})
        for k, v in cls.items():
            if k != "details":
                writer.writerow(["Classification", k, v])

        # Recovery
        rec = data.get("recovery", {})
        for k, v in rec.items():
            if k not in ["symbols", "bits", "diagnostics"]:
                writer.writerow(["Recovery", k, v])

        # De-interleaving
        deint = data.get("deinterleaving", {})
        for k, v in deint.items():
            if k not in ["output_bits", "candidate_hypotheses", "diagnostics"]:
                writer.writerow(["Deinterleaving", k, v])

        # FEC
        fec = data.get("fec", {})
        for k, v in fec.items():
            if k not in ["decoded_bits", "diagnostics"]:
                writer.writerow(["FEC", k, v])

        # Correlation
        corr = data.get("correlation", {})
        for k, v in corr.items():
            if k not in ["candidate_headers", "candidate_payload_regions", "repeated_patterns", "diagnostics"]:
                writer.writerow(["Correlation", k, v])

    return filepath
