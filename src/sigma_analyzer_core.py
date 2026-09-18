"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Core Analysis & Signal Metadata Extraction Module
Truth-in-metrics: Computes actual physical properties and leaves uncalculated parameters as '--'.
"""

import os
import numpy as np

# The app runs as a script: run.py puts src/ on sys.path and imports modules
# flat (`from sigma_analyzer_core import ...`), so a plain relative import
# fails at startup. Support both that layout and a package import, so the
# verification scripts under scratch/ can import src.* as a package.
try:
    from .sigma_symbol_rate import (
        estimate_symbol_rate, format_symbol_rate, format_sps,
    )
    from .sigma_sample_rate import (
        estimate_sample_rate, format_sample_rate, format_sample_rate_source,
        check_inconsistency, parse_rate_from_filename,
    )
except ImportError:  # running as a flat script, as run.py does
    from sigma_symbol_rate import (
        estimate_symbol_rate, format_symbol_rate, format_sps,
    )
    from sigma_sample_rate import (
        estimate_sample_rate, format_sample_rate, format_sample_rate_source,
        check_inconsistency, parse_rate_from_filename,
    )


class SignalMetadata:
    """Holds metadata and physical measurements of an IQ signal file."""

    def __init__(self, filepath="signal.iq", samp_rate=1000000, center_freq=0.0):
        # Resolve filepath against data/iq if relative
        if filepath and not os.path.exists(filepath):
            candidates = [
                os.path.join("data", "iq", filepath),
                os.path.join("data", filepath),
                os.path.join(os.path.dirname(__file__), "..", "data", "iq", filepath),
                os.path.join(os.path.dirname(__file__), "..", "data", filepath),
            ]
            for c in candidates:
                if os.path.exists(c):
                    filepath = os.path.abspath(c)
                    break

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

        # Filename-derived rate, resolved up front so this object is
        # self-consistent: previously `samp_rate` stayed at whatever the caller
        # passed while `sample_rate_result` reported a filename token, so the
        # header could show 1 MSps next to the provenance line for a 250 kSps
        # token. A caller that knows better (WAV header, operator input) can
        # still overwrite it afterwards.
        _parsed = parse_rate_from_filename(filepath)
        if _parsed is not None:
            self.samp_rate = _parsed[0]

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

        # Symbol rate estimation (Stage 4 prerequisite)
        self.symbol_rate = "--"
        self.samples_per_symbol = "--"
        self.symbol_rate_confidence = "--"
        self.symbol_rate_result = None

        # Sample rate provenance.
        #
        # `samp_rate` is a label, not a measurement: it cannot be recovered
        # from the samples (see sigma_sample_rate.py). These fields record
        # where the number came from so the GUI can show a filename guess as
        # a guess instead of presenting it with the same authority as an
        # operator-set value.
        self.sample_rate_result = None
        self.sample_rate_source = "--"
        self.sample_rate_confidence = "--"
        self.sample_rate_warning = ""

        # Modulation classification status
        self.modulation_class = "Not analyzed"
        # NOTE -- despite the historical field name, this is NOT a confidence.
        # It records WHERE the classification came from: "measured" (derived
        # from the signal), "indeterminate" (no class fit), or "filename hint,
        # unverified". Do not treat it as a probability; there is no
        # probability to report here. The four-way candidate distribution does
        # not exist -- runner-up classes are discarded, not ranked. The real
        # physical confidence figure is EVM, in the demodulation stage.
        # `modulation_source` is the honest name; the old one is kept as a
        # property alias so existing callers keep working.
        self.modulation_source = "--"
        self.candidate_modulations = [
            "AM", "FM", "ASK", "FSK", "BPSK", "QPSK", "8PSK", "QAM"
        ]

        # Analyze if file exists
        if self.file_exists and self.num_samples > 0:
            self._analyze_file()

    @property
    def modulation_confidence(self):
        """Deprecated alias for `modulation_source`.

        Kept because the old name is referenced elsewhere in the tree. It was
        misleading: the value is a provenance label ("measured",
        "indeterminate", "filename hint, unverified"), never a probability.
        New code should read `modulation_source`.
        """
        return self.modulation_source

    @modulation_confidence.setter
    def modulation_confidence(self, value):
        self.modulation_source = value

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

    def _psk_line_scores(self, data, nfft=8192, orders=(2, 4, 8)):
        """Line-to-floor ratio in dB of the M-th power spectrum, for each M.

        Raising a PSK signal to the M-th power removes the modulation and
        concentrates energy at M times the carrier offset. The M that produces
        the sharpest line is the modulation order.

        Exposed separately from `_detect_psk_order` so the decision rule can be
        scored against known signals without duplicating this measurement.

        MEASURED WARNING -- these scores do NOT separate 2 from 4 from 8.
        On known-good generated signals (100 ksps, alpha 0.35):

            BPSK    x^2 = 50.1   x^4 = 42.1   x^8 = 37.1
            QPSK    x^2 = 29.5   x^4 = 35.7   x^8 = 31.4
            8PSK    x^2 = 29.2   x^4 = 17.9   x^8 = 28.8
            16QAM   x^2 = 29.9   x^4 = 29.1   x^8 = 26.3

        8PSK's strongest line is at x^2, not x^8, so "smallest M with a line as
        strong as the best" reports 2 for an 8PSK capture. Worse, pure noise
        scores 11.3 dB and an unmodulated carrier scores 220 dB, so that rule
        labels noise "BPSK" and CW "8PSK". Do not reintroduce it. Identifying
        8PSK and 16QAM from the signal remains an OPEN problem.

        Returns {} when the capture is too short or the floor is degenerate.
        """
        n = min(len(data), nfft)
        if n < 512:
            return {}
        seg = np.asarray(data[:n], dtype=np.complex128)
        win = np.hanning(n)
        scores = {}
        for m in orders:
            # Raise to the m-th power by repeated multiplication. The
            # ** operator can drop the complex dtype on some numpy builds,
            # and np.fft.rfft rejects complex input entirely on the
            # Radioconda numpy (2.2.x) this app ships against, so use
            # np.fft.fft and take the first half of the spectrum.
            powered = seg.copy()
            for _ in range(m - 1):
                powered = powered * seg
            spec_full = np.abs(np.fft.fft(powered * win)) ** 2
            spec = np.asarray(spec_full[:spec_full.size // 2],
                              dtype=np.float64)
            if spec.size < 8:
                return {}
            # Exclude the DC neighbourhood, where the collapsed carrier
            # sits when there is no residual offset.
            body = spec[2:spec.size - 2]
            if body.size == 0:
                return {}
            peak = float(np.max(body))
            floor = float(np.median(body))
            if floor <= 0:
                return {}
            scores[m] = 10.0 * np.log10(peak / floor)
        return scores

    def _detect_psk_order(self, data, nfft=8192):
        """Estimate PSK order from the M-th power carrier line.

        Returns 2, 4, or 0 when no order is distinguishable. This is a
        measurement, not a guess -- but it is a weak one on short or noisy
        captures, hence the 0 case.

        Only BPSK and QPSK are attempted, deliberately. An attempt to extend
        this to 8PSK by picking the SMALLEST M whose line is as strong as the
        best one was measured and REJECTED -- see the note on
        `_psk_line_scores`. In short, it called pure noise "BPSK" and an
        unmodulated carrier "8PSK", which is the confident-wrong-answer
        failure this module exists to avoid. The conservative 2-vs-4
        comparison below abstains on both.
        """
        try:
            scores = self._psk_line_scores(data, nfft=nfft, orders=(2, 4))
            if 2 not in scores or 4 not in scores:
                return 0
            # Require a clear margin, otherwise report no decision.
            if scores[4] - scores[2] > self.PSK_LINE_MARGIN_DB:
                return 4
            if scores[2] - scores[4] > self.PSK_LINE_MARGIN_DB:
                return 2
            return 0
        except Exception:
            return 0

    PSK_LINE_MARGIN_DB = 3.0  # "clearly stronger", in dB

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

                # 99% Occupied Bandwidth (OBW)
                total_pwr = np.sum(fft_mag**2)
                if total_pwr > 1e-12:
                    cum_pwr = np.cumsum(fft_mag**2) / total_pwr
                    idx_low = np.searchsorted(cum_pwr, 0.005)
                    idx_high = min(len(freqs) - 1, np.searchsorted(cum_pwr, 0.995))
                    obw = abs(freqs[idx_high] - freqs[idx_low])
                    if obw >= 1e6:
                        self.occupied_bandwidth = f"{obw / 1e6:.2f} MHz"
                    elif obw >= 1e3:
                        self.occupied_bandwidth = f"{obw / 1e3:.1f} kHz"
                    else:
                        self.occupied_bandwidth = f"{obw:.0f} Hz"

                # Noise Floor & SNR estimation
                sorted_pwr = np.sort(fft_mag**2)
                q25 = max(1, len(sorted_pwr) // 4)
                noise_pwr = np.mean(sorted_pwr[:q25])
                sig_pwr = np.mean(sorted_pwr[q25:])
                if noise_pwr > 1e-18:
                    snr_val = 10.0 * np.log10(max(sig_pwr / noise_pwr, 1.0))
                    self.snr = f"{snr_val:.1f} dB"
                    noise_val = 10.0 * np.log10(max(noise_pwr / (np.max(fft_mag**2) + 1e-12), 1e-12))
                    self.noise_floor = f"{noise_val:.1f} dBFS"

                # Symbol Rate Estimation (Stage 4 prerequisite)
                # Uses the envelope periodicity of the pulse-shaped signal.
                # Reported alongside a confidence label because a symbol
                # clock that is not present in the data must be surfaced as
                # such rather than returning a plausible-looking number.
                try:
                    sr_res = estimate_symbol_rate(data, self.samp_rate)
                    self.symbol_rate_result = sr_res
                    if sr_res.get("locked"):
                        self.symbol_rate = format_symbol_rate(sr_res)
                        self.samples_per_symbol = format_sps(sr_res)
                        self.symbol_rate_confidence = (
                            f"{sr_res['confidence_label']} "
                            f"({sr_res['prominence_db']:.1f} dB)"
                        )
                    else:
                        self.symbol_rate = "--"
                        self.samples_per_symbol = "--"
                        self.symbol_rate_confidence = (
                            f"no lock ({sr_res['prominence_db']:.1f} dB)"
                        )
                except Exception as e:
                    print(f"[SIGMA] Symbol rate estimation error: {e}")

                # Sample Rate Provenance
                #
                # We do not "detect" f_s here -- that is impossible from
                # samples alone. We resolve it from the most trustworthy
                # available source (operator > recognised protocol > filename
                # token > default) and label it. A protocol match is the only
                # case where the value can be called MEASURED, because it is
                # the only case derived from data rather than from a string.
                try:
                    sr_res = estimate_sample_rate(
                        None,
                        symbol_rate_result=self.symbol_rate_result,
                        filepath=self.filename,
                        user_rate=self.samp_rate,
                        user_is_explicit=False,
                    )
                    self.sample_rate_result = sr_res
                    self.sample_rate_source = format_sample_rate_source(sr_res)
                    self.sample_rate_confidence = sr_res.confidence

                    # A protocol match yields a rate that differs from the
                    # assumed one; adopt it so R_s = f_s / SPS is self-
                    # consistent. Only do this when we actually matched a
                    # standard -- never for a filename token, which is a hint
                    # about the file rather than a measurement of the signal.
                    if (sr_res.source == sr_res.PROTOCOL
                            and abs(sr_res.samp_rate - self.samp_rate) > 1.0):
                        print(f"[SIGMA] Sample rate corrected "
                              f"{self.samp_rate:,.0f} -> {sr_res.samp_rate:,.0f} S/s "
                              f"via {sr_res.matched_protocol}")
                        self.samp_rate = sr_res.samp_rate
                        self.duration_seconds = (self.num_samples / self.samp_rate
                                                 if self.samp_rate > 0 else 0.0)
                        self.duration_str = self._format_duration(self.duration_seconds)

                    # An implausible SPS is the classic symptom of a renamed
                    # file (an off-by-2x or off-by-10x sample rate).
                    ok, why = check_inconsistency(sr_res, self.symbol_rate_result)
                    if not ok:
                        self.sample_rate_warning = why
                except Exception as e:
                    print(f"[SIGMA] Sample rate resolution error: {e}")

                # Modulation Classification
                #
                # This is measurement-driven: the statistics below decide the
                # class. The filename is NOT used to select the answer -- an
                # earlier version returned hardcoded confidences whenever the
                # filename happened to contain "bpsk"/"qpsk"/etc, which meant
                # renaming a file changed the reported modulation. Any hint
                # taken from the name is applied afterwards as a weak
                # tiebreak, and is reported separately so it is visible.
                fname_lower = self.filename.lower()
                d_phase = np.angle(data[1:] * np.conj(data[:-1]))
                f_std = np.std(d_phase)
                amp_std = np.std(magnitudes) / (np.mean(magnitudes) + 1e-12)

                # Fourth-power detection: for PSK of order >= 2 the modulation
                # is removed by raising to the M-th power, leaving a carrier
                # line for the order that matches. A strong line after x^4
                # indicates QPSK; after x^2 indicates BPSK.
                order = self._detect_psk_order(data)

                if order == 4:
                    self.modulation_class = "QPSK"
                    self.modulation_source = "measured"
                elif order == 2:
                    self.modulation_class = "BPSK"
                    self.modulation_source = "measured"
                elif amp_std < 0.05 and f_std < 0.1:
                    self.modulation_class = "CW / Unmodulated"
                    self.modulation_source = "measured"
                elif amp_std > 0.3:
                    self.modulation_class = "AM / ASK"
                    self.modulation_source = "measured"
                elif amp_std < 0.12 and f_std > 0.4:
                    self.modulation_class = "BPSK / 2-FSK"
                    self.modulation_source = "measured"
                else:
                    self.modulation_class = "Digital PSK/FSK"
                    self.modulation_source = "indeterminate"

                # Filename hint: weak, and never overrides a confident
                # measurement. Only recorded when the measurement above was
                # indeterminate.
                if self.modulation_source == "indeterminate":
                    hint = None
                    for token, name in (("bpsk", "BPSK"), ("qpsk", "QPSK"),
                                        ("rds", "FM / RDS"), ("fm", "FM / RDS"),
                                        ("stereo", "Audio Baseband"),
                                        ("audio", "Audio Baseband"),
                                        ("thunder", "Audio Baseband")):
                        if token in fname_lower:
                            hint = name
                            break
                    if hint:
                        self.modulation_class = f"{hint} (filename hint)"
                        self.modulation_source = "filename hint, unverified"

        except Exception as e:
            print(f"[SIGMA] Error analyzing samples: {e}")


def load_and_convert_wav(wav_path):
    """
    Converts a WAV recording (mono audio or stereo IQ) into a complex64 IQ binary file.
    Returns: (output_iq_path, sample_rate, num_samples, is_stereo_iq)
    """
    import scipy.io.wavfile as wav
    sr, data = wav.read(wav_path)

    if data.ndim == 2 and data.shape[1] >= 2:
        # Stereo IQ recording: Channel 0 is I, Channel 1 is Q
        i_ch = data[:, 0].astype(np.float32)
        q_ch = data[:, 1].astype(np.float32)
        if np.issubdtype(data.dtype, np.integer):
            max_val = float(np.iinfo(data.dtype).max)
            i_ch /= max_val
            q_ch /= max_val
        complex_samples = (i_ch + 1j * q_ch).astype(np.complex64)
        is_stereo = True
    else:
        # Mono recording: Real baseband
        mono = data.astype(np.float32)
        if np.issubdtype(data.dtype, np.integer):
            max_val = float(np.iinfo(data.dtype).max)
            mono /= max_val
        complex_samples = (mono + 0j).astype(np.complex64)
        is_stereo = False

    out_path = os.path.splitext(wav_path)[0] + "_converted.iq"
    complex_samples.tofile(out_path)
    return out_path, sr, len(complex_samples), is_stereo
