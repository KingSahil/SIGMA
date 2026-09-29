import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile


def _sidecar(path: Path) -> dict[str, Any]:
    for candidate in (path.with_name(path.name + "_telemetry.json"), path.with_suffix(path.suffix + "_meta.json"), path.with_suffix(".iq_meta.json")):
        if candidate.exists():
            try:
                value = json.loads(candidate.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}
    return {}


def read_wav(path: Path, max_samples: int) -> tuple[np.ndarray, dict[str, Any]]:
    rate, values = wavfile.read(path)
    values = np.asarray(values)
    channels = 1 if values.ndim == 1 else values.shape[1]
    values = values[:max_samples]
    scale = float(np.iinfo(values.dtype).max) if np.issubdtype(values.dtype, np.integer) else 1.0
    values = values.astype(np.float32) / max(scale, 1.0)
    samples = values.astype(np.complex64) if values.ndim == 1 else values[:, 0] + 1j * values[:, 1]
    return samples.astype(np.complex64), {"sample_rate": float(rate), "channels": channels, "duration": len(samples) / rate, "num_samples": len(samples), "iq_format": "wav"}


def read_iq(path: Path, metadata: dict[str, Any] | None, max_samples: int) -> tuple[np.ndarray, dict[str, Any]]:
    metadata = {**_sidecar(path), **(metadata or {})}
    fmt = str(metadata.get("iq_format") or metadata.get("sample_format") or metadata.get("dtype") or "").lower()
    if fmt in {"complex64", "fc32", "float32_complex"}:
        samples = np.fromfile(path, dtype=np.complex64, count=max_samples)
    elif fmt in {"complex128", "fc64"}:
        samples = np.fromfile(path, dtype=np.complex128, count=max_samples)
    elif fmt in {"float32", "sc32", "interleaved_float32"}:
        raw = np.fromfile(path, dtype=np.float32, count=max_samples * 2)
        samples = raw[0::2] + 1j * raw[1::2]
    elif fmt in {"int16", "sc16", "interleaved_int16"}:
        raw = np.fromfile(path, dtype=np.int16, count=max_samples * 2)
        samples = (raw[0::2] + 1j * raw[1::2]).astype(np.complex64) / 32768.0
    else:
        raise ValueError("IQ sample format is required (complex64, float32, or int16)")
    if len(samples) == 0:
        raise ValueError("IQ file contains no complete samples")
    info = {"sample_rate": metadata.get("sample_rate"), "center_frequency": metadata.get("center_frequency"), "iq_format": fmt, "channels": 2, "num_samples": len(samples)}
    if info["sample_rate"]:
        info["duration"] = len(samples) / float(info["sample_rate"])
    return np.asarray(samples, dtype=np.complex64), info


def read_signal(path: Path, file_type: str, metadata: dict[str, Any] | None, max_samples: int) -> tuple[np.ndarray, dict[str, Any]]:
    return read_wav(path, max_samples) if file_type == "WAV" else read_iq(path, metadata, max_samples)
