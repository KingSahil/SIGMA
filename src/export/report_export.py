"""
SIGMA - Signal Intelligence Report Generator
Generates comprehensive Markdown and plain-text reports for intelligence dossiers.
"""

try:
    from models.signal_result import SignalResult
except ImportError:
    from ..models.signal_result import SignalResult


def generate_markdown_report(result: Union[SignalResult, Dict[str, Any]]) -> str:
    """Generates structured Markdown signal intelligence report."""
    if isinstance(result, SignalResult):
        data = result.to_dict()
    else:
        data = dict(result)

    inp = data.get("input_metadata", {})
    metrics = data.get("signal_metrics", {})
    cls = data.get("classification", {})
    rec = data.get("recovery", {})
    deint = data.get("deinterleaving", {})
    fec = data.get("fec", {})
    corr = data.get("correlation", {})

    report = [
        f"# SIGMA RF Intelligence Report: {inp.get('filename', 'Unknown')}",
        "",
        "## 1. Physical & Container Parameters",
        f"- **File Path**: `{inp.get('filepath', '--')}`",
        f"- **Sample Rate**: `{inp.get('sample_rate', 0):,.0f} S/s`",
        f"- **Center Frequency**: `{inp.get('center_frequency', 0):,.0f} Hz`",
        f"- **Samples Captured**: `{inp.get('num_samples', 0):,}`",
        f"- **Estimated Duration**: `{inp.get('duration_seconds', 0.0):.3f} s`",
        "",
        "## 2. DSP & Signal Metrics",
        f"- **Signal SNR**: `{metrics.get('snr_str', '--')}`",
        f"- **Noise Floor**: `{metrics.get('noise_floor_dbfs', '--')} dBFS`",
        f"- **Signal Power**: `{metrics.get('signal_power_dbfs', '--')} dBFS`",
        f"- **Peak Frequency**: `{metrics.get('peak_frequency_hz', '--')} Hz`",
        f"- **Measured Symbol Rate**: `{metrics.get('symbol_rate_str', '--')}`",
        f"- **Samples per Symbol**: `{metrics.get('samples_per_symbol', '--')}`",
        f"- **Symbol Clock Lock**: `{metrics.get('symbol_rate_lock', '--')}`",
        "",
        "## 3. Modulation Classification",
        f"- **Identified Modulation**: `{cls.get('modulation', 'UNKNOWN')}`",
        f"- **Provenance / Source**: `{cls.get('confidence_evidence', 'indeterminate')}`",
        "",
        "## 4. Signal Recovery & Demodulation",
        f"- **Demodulation Status**: `{rec.get('demodulation_status', 'NOT RUN')}`",
        f"- **Recovered Symbols**: `{rec.get('n_symbols', 0):,}`",
        f"- **Recovered Bits**: `{len(rec.get('bits', [])):,}`",
        f"- **Constellation EVM**: `{rec.get('evm_percent', '--')}%`",
        f"- **Carrier Offset**: `{rec.get('carrier_offset_hz', '--')} Hz`",
        f"- **Recovered Bitstream (first bits)**: `{rec.get('bit_summary', '--')}`",
        "",
        "## 5. De-interleaving & Coding Analysis",
        f"- **De-interleaving Status**: `{deint.get('status', 'UNKNOWN')}`",
        f"- **Interleaving Mode**: `{deint.get('mode', 'NONE')}`",
        f"- **FEC Decoder Status**: `{fec.get('status', 'UNKNOWN')}`",
        f"- **FEC Scheme**: `{fec.get('fec_type', 'NONE')}`",
        f"- **Corrected Errors**: `{fec.get('corrected_errors', 0)}`",
        "",
        "## 6. Bitstream Correlation & Frame Boundaries",
        f"- **Correlation Status**: `{corr.get('status', 'UNKNOWN')}`",
        f"- **Candidate Headers Detected**: `{len(corr.get('candidate_headers', []))}`",
        f"- **Candidate Payloads Sliced**: `{len(corr.get('candidate_payload_regions', []))}`",
        "",
        "---",
        "*Report generated autonomously by SIGMA RF Intelligence Station.*",
    ]

    return "\n".join(report)


def export_to_report(result: Union[SignalResult, Dict[str, Any]], filepath: str) -> str:
    """Exports signal intelligence report to text file."""
    md_content = generate_markdown_report(result)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
    return filepath
