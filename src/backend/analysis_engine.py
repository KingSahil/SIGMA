from typing import Any

import numpy as np
from scipy import signal


def _db(values: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(values, 1e-15))


def analyze(samples: np.ndarray, sample_rate: float, center_frequency: float | None = None) -> dict[str, Any]:
    if len(samples) < 16:
        raise ValueError("At least 16 samples are required for analysis")
    nfft = min(4096, len(samples))
    window = signal.windows.blackman(nfft)
    spectrum = np.fft.fftshift(np.fft.fft(samples[:nfft] * window))
    power = np.abs(spectrum) ** 2 / max(np.sum(window ** 2), 1.0)
    frequencies = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / sample_rate))
    noise_power = float(np.median(power))
    signal_power = float(np.mean(np.abs(samples) ** 2))
    peak_index = int(np.argmax(power))
    peak_offset = float(frequencies[peak_index])
    occupied = frequencies[power >= np.quantile(power, 0.5)]
    bandwidth = float(occupied[-1] - occupied[0]) if len(occupied) else None
    f, t, z = signal.stft(samples, fs=sample_rate, nperseg=min(256, len(samples)), noverlap=min(192, max(0, len(samples) // 4)), boundary=None)
    constellation = samples[::max(1, len(samples) // 5000)][:5000]
    return {
        "sampling_rate": float(sample_rate), "center_frequency": center_frequency,
        "carrier_frequency": float(center_frequency + peak_offset) if center_frequency is not None else None,
        "peak_frequency": peak_offset, "bandwidth": bandwidth, "occupied_bandwidth": bandwidth,
        "signal_power": float(10.0 * np.log10(max(signal_power, 1e-15))),
        "noise_power": float(10.0 * np.log10(max(noise_power, 1e-15))),
        "snr": float(10.0 * np.log10(max(signal_power, 1e-15) / max(noise_power, 1e-15))),
        "snr_method": "PSD-based median noise-floor estimation", "duration": len(samples) / sample_rate, "num_samples": int(len(samples)),
        "spectrum": {"frequencies": frequencies.tolist(), "power": _db(power).tolist(), "unit": "dB"},
        "spectrogram": {"time": t.tolist(), "frequencies": f.tolist(), "power": _db(np.abs(z) ** 2).tolist(), "unit": "dB"},
        "constellation": {"i": np.real(constellation).astype(float).tolist(), "q": np.imag(constellation).astype(float).tolist(), "samples": int(len(constellation))},
        "classification": {"modulation": None, "confidence": None, "alternatives": [], "mode": "measurement-only; trained model unavailable"},
        "processing_status": "COMPLETED",
    }
