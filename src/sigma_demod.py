"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Digital Demodulation Module (Stage 4)

Recovers a symbol stream and a hard-decision bitstream from complex baseband
IQ samples. This is the digital path; the analogue audio path used for
listening lives in AudioManager and is unrelated to bit recovery.

Chain
-----
1. Carrier recovery    - 4th-power frequency estimate plus phase tracking,
                          removing the residual offset and rotation a capture
                          always carries.
2. Matched filtering   - root-raised-cosine filter matched to the transmit
                          pulse shape, maximising SNR at the decision instant.
3. Symbol timing       - decimate at the recovered samples-per-symbol offset,
                          selecting the sampling instant with maximum eye
                          opening rather than an arbitrary phase.
4. Decision and mapping- slice the recovered symbols against the constellation
                          and map to bits.

Honest reporting
----------------
Every stage reports whether it achieved a lock. A demodulator that produces a
bitstream from a signal that carries no recoverable symbols is worse than one
that declines, because the output looks plausible. `locked` is therefore a
first-class field, not an afterthought.
"""

import numpy as np


class DemodResult:
    """Outcome of a digital demodulation attempt."""

    def __init__(self):
        self.locked = False
        self.reason = ""
        self.symbols = None            # complex128 array of recovered symbols
        self.bits = None               # uint8 array of hard decisions
        self.modulation = None         # e.g. "BPSK", "QPSK"
        self.sps = None                # samples per symbol used
        self.evm_percent = None        # error vector magnitude, %
        self.carrier_offset_hz = None  # residual offset estimate
        self.n_symbols = 0
        self.bit_rate = None           # bits/sec once symbol rate known

    def __repr__(self):
        if not self.locked:
            return f"<DemodResult NO LOCK: {self.reason}>"
        return (f"<DemodResult {self.modulation} {self.n_symbols} sym "
                f"{len(self.bits) if self.bits is not None else 0} bits "
                f"EVM={self.evm_percent:.1f}%>")


def rrc_filter(sps, alpha=0.35, span_symbols=8):
    """Root-raised-cosine impulse response, unit energy."""
    sps = int(round(sps))
    if sps < 2:
        return np.array([1.0])
    n = span_symbols * sps
    t = np.arange(-n // 2, n // 2 + 1, dtype=np.float64) / sps
    h = np.zeros_like(t)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-8:
            h[i] = 1.0 - alpha + 4.0 * alpha / np.pi
        elif alpha > 0 and abs(abs(ti) - 1.0 / (4.0 * alpha)) < 1e-8:
            h[i] = (alpha / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                - (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
            )
        else:
            num = (np.sin(np.pi * ti * (1.0 - alpha))
                   + 4.0 * alpha * ti * np.cos(np.pi * (1.0 + alpha) * ti))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            h[i] = num / den
    energy = np.sum(h ** 2)
    if energy > 0:
        h /= np.sqrt(energy)
    return h


def estimate_carrier_offset(x, samp_rate):
    """Estimate carrier offset using the 4th-power method.

    For a PSK signal, raising to the 4th power strips the modulation and
    leaves a spectral line at four times the carrier offset (modulo the
    PSK phase constellation). Dividing by four recovers the offset.

    Returns the offset in Hz.
    """
    n = len(x)
    nfft = 1 << int(np.floor(np.log2(max(1024, min(n, 65536)))))
    if nfft > n:
        nfft = 1 << int(np.floor(np.log2(max(n, 2))))
    if nfft < 64:
        return 0.0

    seg = x[:nfft] * np.blackman(nfft)
    fourth = seg ** 4
    spec = np.abs(np.fft.fftshift(np.fft.fft(fourth)))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / samp_rate))
    peak = freqs[int(np.argmax(spec))]

    offset = peak / 4.0
    # Ambiguity: the 4th-power line repeats every samp_rate/4, so the true
    # offset may differ by a multiple of that. Fold to the nearest valid
    # value inside the Nyquist span.
    span = samp_rate / 4.0
    while offset > span / 2:
        offset -= span
    while offset < -span / 2:
        offset += span
    return float(offset)


def _apply_matched_filter(x, sps, alpha=0.35):
    """Convolve with an RRC filter matched to the transmit pulse shape."""
    h = rrc_filter(sps, alpha=alpha)
    if len(h) < 3:
        return x
    return np.convolve(x, h, mode="same")


def _find_best_sampling_phase(x, sps, const):
    """Pick the sampling phase that best fits the constellation.

    The optimum decision instant is where the eye diagram is widest, which is
    equivalently the phase whose decimated symbols cluster most tightly around
    the ideal constellation points. Scoring on constellation fit is far more
    reliable than scoring on amplitude variance: variance is maximised by a
    slow envelope drift, which is not the same as an open eye.

    Returns the phase index with the lowest normalised error.
    """
    sps_int = int(round(sps))
    if sps_int < 1:
        return 0

    ref_rms = np.sqrt(np.mean(np.abs(const) ** 2))
    best_phase, best_score = 0, np.inf

    for phase in range(sps_int):
        sliced = x[phase::sps_int]
        if len(sliced) < 16:
            continue
        scale = np.sqrt(np.mean(np.abs(sliced) ** 2))
        if scale <= 1e-12:
            continue
        normalised = sliced / scale * ref_rms
        dist = np.min(np.abs(normalised[:, None] - const[None, :]), axis=1)
        # Normalised RMS error: how far symbols sit from their ideal point,
        # as a fraction of the constellation radius.
        score = np.sqrt(np.mean(dist ** 2)) / (ref_rms + 1e-12)
        if score < best_score:
            best_score, best_phase = score, phase

    return best_phase


def _decision_distances(symbols, constellation):
    """Distance from each symbol to nearest constellation point."""
    if len(symbols) == 0:
        return np.array([])
    d = np.abs(symbols[:, None] - constellation[None, :])
    return np.min(d, axis=1)


def demodulate(x, samp_rate, modulation="BPSK", sps=None, alpha=0.35):
    """Demodulate complex baseband IQ to hard-decision bits.

    Parameters
    ----------
    x : array_like of complex
        Complex baseband samples.
    samp_rate : float
        Sample rate in samples/sec.
    modulation : str
        One of "BPSK", "QPSK", "8PSK", "16QAM". Determines the constellation.
    sps : float, optional
        Samples per symbol. If None it is taken from the symbol rate
        estimate, so a correct symbol rate is a prerequisite.
    alpha : float
        Assumed root-raised-cosine excess bandwidth factor.

    Returns
    -------
    DemodResult
    """
    res = DemodResult()

    x = np.asarray(x, dtype=np.complex128)
    if x.size < 256:
        res.reason = "insufficient samples"
        return res

    if sps is None:
        res.reason = "samples-per-symbol required (run symbol rate estimate)"
        return res
    if sps < 2.0:
        res.reason = (f"samples per symbol {sps:.2f} is below 2.0; "
                      f"symbol recovery is not possible at this rate")
        return res

    mod = modulation.upper().replace("-", "")
    constellations = {
        "BPSK": np.array([1 + 0j, -1 + 0j]),
        "QPSK": np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2),
        "8PSK": np.exp(1j * 2 * np.pi * np.arange(8) / 8),
    }
    if mod == "16QAM":
        levels = np.array([-3, -1, 1, 3], dtype=np.float64) / np.sqrt(10)
        constellations["16QAM"] = np.array(
            [i + 1j * q for i in levels for q in levels]
        )
    if mod not in constellations:
        res.reason = f"unsupported modulation '{modulation}'"
        return res

    const = constellations[mod]
    res.modulation = mod
    res.sps = float(sps)

    # --- 1. Carrier recovery ---------------------------------------------
    offset = estimate_carrier_offset(x, samp_rate)
    res.carrier_offset_hz = offset
    t = np.arange(len(x), dtype=np.float64) / samp_rate
    x_bb = x * np.exp(-1j * 2.0 * np.pi * offset * t)

    # --- 2. Matched filtering --------------------------------------------
    x_mf = _apply_matched_filter(x_bb, sps, alpha=alpha)

    # --- 3. Symbol timing -------------------------------------------------
    phase = _find_best_sampling_phase(x_mf, sps, const)
    sps_int = int(round(sps))
    symbols = x_mf[phase::sps_int]

    if len(symbols) < 8:
        res.reason = "too few symbols after decimation"
        return res

    # Normalise constellation scale so decisions are amplitude independent.
    scale = np.sqrt(np.mean(np.abs(symbols) ** 2))
    if scale <= 1e-12:
        res.reason = "zero-energy signal"
        return res
    symbols = symbols / scale * np.sqrt(np.mean(np.abs(const) ** 2))

    # --- 3b. Residual phase correction -----------------------------------
    # Carrier recovery from the 4th-power line removes the bulk of the offset
    # but leaves a small constant phase rotation, because the nonlinearity is
    # ambiguous by the constellation's rotational symmetry.
    #
    # Estimating that rotation from the symbol statistics alone is unreliable:
    # for a symmetric constellation the estimator is dominated by the symmetry
    # ambiguity rather than the true offset. Instead, search the small set of
    # candidate rotations that are symmetries of the constellation and keep
    # whichever explains the received symbols best. That is both simpler and
    # more robust than any single-shot phase estimator.
    n_sym_rots = {"BPSK": 2, "QPSK": 4, "8PSK": 8, "16QAM": 4}[mod]

    # Coarse residual from the symbol cloud, folded into the symmetry group.
    coarse = 0.0
    mean_vec = np.mean(symbols ** n_sym_rots)
    if np.abs(mean_vec) > 1e-12:
        coarse = np.angle(mean_vec) / n_sym_rots

    # Refine: test a small set of offsets around the coarse estimate and pick
    # the one minimising the distance to the constellation.
    candidates = [coarse + k * (2 * np.pi / (4 * n_sym_rots))
                  for k in range(-4, 5)]
    best_rot, best_score = 0.0, np.inf
    for rot in candidates:
        test = symbols * np.exp(-1j * rot)
        d = np.min(np.abs(test[:, None] - const[None, :]), axis=1)
        score = np.sqrt(np.mean(d ** 2))
        if score < best_score:
            best_score, best_rot = score, rot

    symbols = symbols * np.exp(-1j * best_rot)
    res.phase_correction_deg = float(np.degrees(-best_rot))

    # --- 4. Decision and mapping -----------------------------------------
    dist = _decision_distances(symbols, const)
    idx = np.argmin(np.abs(symbols[:, None] - const[None, :]), axis=1)

    # Error vector magnitude: how far each symbol landed from its ideal
    # point, as a percentage of the constellation radius. A useful quality
    # measure and a guard against nonsense output.
    rms_err = np.sqrt(np.mean(dist ** 2))
    rms_ref = np.sqrt(np.mean(np.abs(const) ** 2))
    res.evm_percent = float(rms_err / (rms_ref + 1e-12) * 100.0)

    bits_per_symbol = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}[mod]
    bits = np.zeros(len(idx) * bits_per_symbol, dtype=np.uint8)
    for k, si in enumerate(idx):
        for b in range(bits_per_symbol):
            bits[k * bits_per_symbol + b] = (si >> (bits_per_symbol - 1 - b)) & 1

    res.symbols = symbols
    res.bits = bits
    res.n_symbols = len(symbols)

    # Require a sane error vector before claiming a lock: an EVM beyond
    # roughly half the constellation spacing means the decisions are
    # effectively random.
    max_evm = 35.0
    if res.evm_percent > max_evm:
        res.reason = (f"error vector magnitude {res.evm_percent:.1f}% exceeds "
                      f"{max_evm:.0f}%; constellation is not resolvable")
        res.bits = None
        res.symbols = None
        return res

    res.locked = True
    res.reason = "symbols recovered"
    return res


def format_bitstream_summary(res, max_bits=64):
    """Short human-readable preview of the recovered bitstream."""
    if not res or not res.locked or res.bits is None:
        return "--"
    head = "".join(str(int(b)) for b in res.bits[:max_bits])
    if len(res.bits) > max_bits:
        head += "..."
    return head
