"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Symbol Rate Estimation

Measures the symbol rate (baud rate) of a digital signal from its complex
baseband IQ samples.

Method
------
A real, pulse-shaped digital signal is cyclostationary: its envelope carries
a periodic component at the symbol rate, because the pulse-shaping filter
leaves a small amplitude ripple that repeats once per symbol. That periodic
component shows up as a spectral line in the FFT of |x[n]|^2.

We average many overlapping FFT segments (Welch's method) before looking for
that line. A single FFT of a noise-like sequence has ~100% spectral variance,
so individual bins fluctuate wildly and a lone noise bin easily outranks a
real clock line. Averaging reduces that variance and makes the detected peak
meaningful.

Validated against generated ground-truth signals with known symbol rates;
the measurement harness lives in scratch/.
"""

import numpy as np


def _interp_peak_at(target_freq, band_spec, band_freqs):
    """Return interpolated (freq, magnitude) of the local peak nearest target."""
    idx = int(np.argmin(np.abs(band_freqs - target_freq)))
    if idx <= 0 or idx >= len(band_spec) - 1:
        return band_freqs[idx], float(band_spec[idx])
    a = np.log(band_spec[idx - 1] + 1e-30)
    b = np.log(band_spec[idx] + 1e-30)
    c = np.log(band_spec[idx + 1] + 1e-30)
    denom = a - 2.0 * b + c
    freq = float(band_freqs[idx])
    if abs(denom) > 1e-30:
        delta = 0.5 * (a - c) / denom
        if abs(delta) < 1.0:
            freq += delta * (band_freqs[1] - band_freqs[0])
    return freq, float(band_spec[idx])


def _resolve_fundamental(band_spec, band_freqs, detected_freq, prominence_db):
    """Prefer the fundamental symbol clock over a stronger harmonic.

    A pulse-shaped signal's envelope periodicity concentrates at the symbol
    rate, but when the excess-bandwidth factor alpha is small the ripple
    shape is such that a harmonic can carry more energy than the fundamental.
    Left uncorrected this overstates the symbol rate by that harmonic order.

    The test is deliberately conservative. A sub-harmonic is accepted only
    when its own spectral line is essentially as strong as the detected
    peak -- within ~3 dB. A coincidence line (for example the R_s/2
    component that an alternating symbol pattern creates) sits far below
    the fundamental and is therefore rejected.

    Returns (freq_hz, prominence_db).
    """
    floor = float(np.median(band_spec))
    if floor <= 1e-30:
        return detected_freq, prominence_db

    _, peak_mag = _interp_peak_at(detected_freq, band_spec, band_freqs)
    if peak_mag <= 0:
        return detected_freq, prominence_db

    # 3 dB tolerance: a true fundamental of the same periodicity family
    # measures within a few dB of its harmonic.
    accept_ratio = 10.0 ** (-3.0 / 10.0)

    best_freq = detected_freq
    for divisor in (2, 3, 4):
        cand = detected_freq / divisor
        if cand < band_freqs[0]:
            break
        freq, mag = _interp_peak_at(cand, band_spec, band_freqs)
        if mag >= peak_mag * accept_ratio:
            best_freq = freq
            break

    if best_freq != detected_freq:
        _, new_mag = _interp_peak_at(best_freq, band_spec, band_freqs)
        if new_mag > floor:
            prominence_db = 10.0 * np.log10(new_mag / floor)

    return best_freq, prominence_db


def estimate_symbol_rate(x, samp_rate):
    """Estimate symbol rate from complex baseband IQ samples.

    Parameters
    ----------
    x : array_like of complex
        Complex baseband samples.
    samp_rate : float
        Sample rate in samples/sec. An incorrect value here invalidates
        the result, since the symbol rate is derived from it.

    Returns
    -------
    dict with keys:
        symbol_rate_hz     : float  (0.0 if no lock)
        samples_per_symbol : float  (0.0 if no lock)
        confidence         : float 0..1
        confidence_label   : "HIGH" | "MEDIUM" | "LOW" | "NONE"
        prominence_db      : float  peak strength over local noise floor
        locked             : bool
    """
    empty = {
        "symbol_rate_hz": 0.0,
        "samples_per_symbol": 0.0,
        "confidence": 0.0,
        "confidence_label": "NONE",
        "prominence_db": 0.0,
        "locked": False,
    }

    x = np.asarray(x, dtype=np.complex64)
    if x.size < 1024 or samp_rate <= 0:
        return empty

    # Envelope of the signal. Pulse shaping modulates this slightly once per
    # symbol, which is the periodic feature we are looking for.
    env = np.abs(x) ** 2

    # Choose the FFT length for adequate frequency resolution, not just
    # speed. The clock line must be resolved against the signal's own
    # spectral leakage, which needs many bins per symbol rate. Too short an
    # FFT (e.g. 1024 at 1 Msps = ~1 kHz bins) buries the clock under
    # leakage sidelobes and lets unrelated peaks win.
    nfft = 16384
    while nfft > len(env) // 2 and nfft > 1024:
        nfft //= 2
    if nfft < 256 or len(env) < nfft:
        nfft = 1 << int(np.floor(np.log2(max(len(env), 2))))
        if nfft < 256:
            return empty

    # Welch averaging with 50% overlap.
    win = np.hanning(nfft)
    step = nfft // 2
    acc, count = None, 0
    for start in range(0, len(env) - nfft + 1, step):
        seg = env[start:start + nfft] - np.mean(env[start:start + nfft])
        spec = np.abs(np.fft.rfft(seg * win)) ** 2
        acc = spec if acc is None else acc + spec
        count += 1
    if acc is None or count == 0:
        return empty

    spec = acc / count
    freqs = np.fft.rfftfreq(nfft, 1.0 / samp_rate)

    # Search band: reject DC and its immediate neighbourhood, and stay below
    # roughly half the sample rate where a symbol clock stops being meaningful.
    band = (freqs > samp_rate * 1e-3) & (freqs < samp_rate * 0.45)
    if not band.any():
        return empty

    band_spec = spec[band]
    band_freqs = freqs[band]

    peak_idx = int(np.argmax(band_spec))
    peak_val = float(band_spec[peak_idx])
    peak_freq = float(band_freqs[peak_idx])

    # Noise floor: median of the search band, robust to the peak itself.
    floor = float(np.median(band_spec))
    if floor <= 1e-30:
        return empty

    ratio = peak_val / floor
    prominence_db = 10.0 * np.log10(ratio)

    # Sub-bin interpolation: the true clock frequency sits between FFT bins.
    # A parabolic fit on the log-magnitude gives a far finer estimate than
    # the raw bin centre, which is essential when the search band is wide.
    if 0 < peak_idx < len(band_spec) - 1:
        a = np.log(band_spec[peak_idx - 1] + 1e-30)
        b = np.log(band_spec[peak_idx] + 1e-30)
        c = np.log(band_spec[peak_idx + 1] + 1e-30)
        denom = a - 2.0 * b + c
        if abs(denom) > 1e-30:
            delta = 0.5 * (a - c) / denom
            if abs(delta) < 1.0:
                bin_width = band_freqs[1] - band_freqs[0]
                peak_freq += delta * bin_width

    # --- Harmonic resolution ---------------------------------------------
    # The envelope of a pulse-shaped signal is periodic at the symbol rate,
    # so its spectrum ideally concentrates at R_s. In practice a harmonic
    # can carry comparable energy. Testing sub-harmonics and preferring the
    # lowest candidate that measures within a few dB of the detected peak
    # keeps the reported value at the fundamental.
    peak_freq, prominence_db = _resolve_fundamental(
        band_spec, band_freqs, peak_freq, prominence_db
    )

    # Confidence scales with how far the peak stands above the noise floor.
    # 6 dB is marginal; 20 dB is unambiguous.
    if prominence_db < 6.0:
        return empty
    confidence = float(np.clip((prominence_db - 6.0) / 14.0, 0.0, 1.0))

    if confidence >= 0.70:
        label = "HIGH"
    elif confidence >= 0.40:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "symbol_rate_hz": peak_freq,
        "samples_per_symbol": samp_rate / peak_freq if peak_freq > 0 else 0.0,
        "confidence": confidence,
        "confidence_label": label,
        "prominence_db": prominence_db,
        "locked": True,
        # The sample rate this estimate was scaled by. Recorded so a downstream
        # consumer can correct it: every frequency here is proportional to the
        # assumed rate, so matching a known standard symbol rate lets us solve
        # for the true f_s (see sigma_sample_rate.py).
        "assumed_samp_rate": float(samp_rate),
        "samp_rate": float(samp_rate),
    }


def format_symbol_rate(res):
    """Human-readable symbol rate for the UI."""
    if not res or not res.get("locked"):
        return "--"
    sr = res["symbol_rate_hz"]
    if sr >= 1e6:
        return f"{sr / 1e6:.3f} Msps"
    if sr >= 1e3:
        return f"{sr / 1e3:.2f} ksps"
    return f"{sr:.1f} sps"


def format_sps(res):
    """Human-readable samples per symbol for the UI."""
    if not res or not res.get("locked"):
        return "--"
    return f"{res['samples_per_symbol']:.2f}"
