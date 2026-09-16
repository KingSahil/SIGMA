"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Core Analysis & Signal Metadata Extraction Module
Truth-in-metrics: Computes actual physical properties and leaves uncalculated parameters as '--'.
"""

import os
import numpy as np


class SignalMetadata:
    """Holds metadata and physical measurements of an IQ signal file."""

    def __init__(self, filepath="signal.iq", samp_rate=1000000, center_freq=0.0):
        self.filepath = filepath
        self.samp_rate = samp_rate
        self.center_freq = center_freq

        # File & container attributes
        self.filename = os.path.basename(filepath) if filepath else "--"
        self.file_exists = os.path.exists(filepath) if filepath else False
        self.filesize_bytes = os.path.getsize(filepath) if self.file_exists else 0
        self.filesize_str = self._format_filesize(self.filesize_bytes)
        self.format_name = "Raw IQ Binary"
        self.datatype = "Complex Float32 (fc32)"

        # Sample calculations (each complex float32 = 8 bytes: 4 real + 4 imag)
        self.bytes_per_sample = 8
        self.num_samples = self.filesize_bytes // self.bytes_per_sample if self.file_exists else 0
        self.duration_seconds = self.num_samples / self.samp_rate if (self.samp_rate > 0 and self.num_samples > 0) else 0.0
        self.duration_str = self._format_duration(self.duration_seconds)

        # Real calculated metrics
        self.rms_amplitude = "--"
        self.peak_amplitude = "--"
        self.signal_power_dbfs = "--"
        self.peak_frequency = "--"

        # Parameters not yet calculated by current DSP stage
        self.occupied_bandwidth = "--"
        self.noise_floor = "--"
        self.snr = "--"

        # Modulation classification status
        self.modulation_class = "Not analyzed"
        self.modulation_confidence = "--"
        self.candidate_modulations = [
            "AM", "FM", "ASK", "FSK", "BPSK", "QPSK", "8PSK", "QAM"
        ]

        # Analyze if file exists
        if self.file_exists and self.num_samples > 0:
            self._analyze_file()

    def _format_filesize(self, num_bytes):
        if num_bytes <= 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:3.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"

    def _format_duration(self, seconds):
        if seconds <= 0:
            return "--"
        if seconds < 0.001:
            return f"{seconds * 1e6:.1f} µs"
        elif seconds < 1.0:
            return f"{seconds * 1e3:.2f} ms"
        else:
            return f"{seconds:.3f} s"

    def _analyze_file(self):
        """Reads real samples and calculates verifiable physical properties."""
        try:
            # Read up to 65,536 samples for accurate initial physical analysis
            read_count = min(self.num_samples, 65536)
            data = np.fromfile(self.filepath, dtype=np.complex64, count=read_count)
            if len(data) == 0:
                return

            magnitudes = np.abs(data)
            # RMS Amplitude
            mean_sq = np.mean(magnitudes ** 2)
            rms = np.sqrt(mean_sq)
            self.rms_amplitude = f"{rms:.4f}"

            # Peak Amplitude
            peak = np.max(magnitudes)
            self.peak_amplitude = f"{peak:.4f}"

            # Signal Power (relative to full scale dBFS)
            if mean_sq > 1e-12:
                p_db = 10.0 * np.log10(mean_sq)
                self.signal_power_dbfs = f"{p_db:+.2f} dBFS"
            else:
                self.signal_power_dbfs = "-inf dBFS"

            # Peak Frequency estimation using FFT
            fft_size = min(len(data), 4096)
            if fft_size >= 256:
                fft_win = data[:fft_size] * np.blackman(fft_size)
                fft_mag = np.abs(np.fft.fftshift(np.fft.fft(fft_win)))
                freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1.0 / self.samp_rate))
                peak_idx = np.argmax(fft_mag)
                peak_f = freqs[peak_idx] + self.center_freq

                if abs(peak_f) >= 1e6:
                    self.peak_frequency = f"{peak_f / 1e6:+.3f} MHz"
                elif abs(peak_f) >= 1e3:
                    self.peak_frequency = f"{peak_f / 1e3:+.2f} kHz"
                else:
                    self.peak_frequency = f"{peak_f:+.1f} Hz"

        except Exception as e:
            print(f"[SIGMA] Error analyzing samples: {e}")
