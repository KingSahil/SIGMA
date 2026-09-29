"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Digital Demodulation Module (Stage 4)

Recovers a symbol stream and a hard-decision bitstream from complex baseband
IQ samples. This is the digital path; the analogue audio path used for
listening lives in AudioManager and is unrelated to bit recovery.

Chain
-----
1. Carrier recovery    - M-th-power frequency estimate plus phase tracking,
                          removing the residual offset and rotation a capture
                          always carries. M is the constellation's rotational
                          symmetry order, so it is 2 for BPSK, 4 for QPSK,
                          8 for 8PSK and 4 for 16QAM.
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


# Rotational symmetry order of each constellation we support.
#
# This single table is used twice, deliberately:
#
#   1. As the EXPONENT for the M-th-power carrier estimator. Raising an
#      M-fold-symmetric constellation to the M-th power collapses every point
#      onto one phase, leaving a spectral line at M times the carrier offset.
#      A wrong exponent does not fail loudly -- it returns a plausible number
#      that is simply wrong. Measured on 8PSK with a true +60,000 Hz offset:
#      x^4 gives +43,610 Hz (-16,390 Hz error) and demodulation collapses to
#      51.7% bit accuracy, i.e. chance. x^8 gives +59,998 Hz.
#
#   2. As the NUMBER OF PHASE ROTATIONS that leave the constellation unchanged,
#      which is the search space for the residual-phase correction below.
#
# Keeping one table means the exponent and the rotation search cannot drift
# apart, which is exactly the bug this replaced (the rotation search was
# modulation-aware while the exponent was hardcoded to 4).
#
# Note that 16QAM legitimately uses 4: a square QAM constellation maps onto
# itself under a 90-degree rotation. It does NOT need 16.
SYMMETRY_ORDER = {"BPSK": 2, "QPSK": 4, "8PSK": 8, "16QAM": 4}


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
        self.phase_correction_deg = None  # residual rotation removed, degrees
        self.residual_freq_hz = None   # residual frequency removed by tracking
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


def estimate_carrier_offset(x, samp_rate, power=4, refine=True):
    """Estimate carrier offset using the M-th-power method.

    Raising an M-fold-rotationally-symmetric constellation to the M-th power
    collapses every symbol onto a single phase, leaving a spectral line at M
    times the carrier offset. Dividing by M recovers the offset.

    Parameters
    ----------
    power : int
        The exponent M. It must be the constellation's rotational symmetry
        order -- see ``SYMMETRY_ORDER``. The default of 4 is correct for QPSK
        and 16QAM only; passing the wrong value returns a plausible but wrong
        answer rather than an error, so callers should take it from the table.
    refine : bool
        Refine the coarse FFT peak on a fine grid. Left switchable so the
        refinement can be scored against the coarse estimate rather than
        assumed to help; see the measurement note in the body.

    Returns the offset in Hz.
    """
    power = int(power)
    if power < 1:
        return 0.0

    n = len(x)
    if n < 64:
        return 0.0

    # Choose the segment length so the record yields several segments to
    # average. A single segment cannot be averaged, and a short capture is
    # exactly when the line is weakest. Measured: 8PSK at 250 ksps gives 6000
    # samples, which at nfft=4096 is ONE segment -- so the averaging had nothing
    # to work with and a spurious peak still won, returning -33.8 kHz for a true
    # +60 kHz offset. At nfft=2048 the same capture yields four segments and the
    # real line wins. Precision lost to the coarser bins is recovered by the
    # sub-bin refinement below, whose search window scales with the bin.
    max_nfft = max(256, n // 2)
    nfft = 1 << int(np.floor(np.log2(max(256, min(max_nfft, 65536)))))
    if nfft > n:
        nfft = 1 << int(np.floor(np.log2(max(n, 2))))
    if nfft < 64:
        return 0.0

    def _raise(seg):
        """seg raised to `power`, by repeated multiplication."""
        raised = seg.copy()
        for _ in range(power - 1):
            raised = raised * seg
        return raised

    # --- Averaged spectrum (Welch), not a single FFT -----------------------
    # A symbol sequence is noise-like, so its spectrum has ~100% variance: on a
    # single FFT a spurious peak routinely outranks the true line. Measured on
    # 8PSK at 250 ksps (seed 9), a spurious peak at -270 kHz reached 6.4 while
    # the real +480 kHz line sat at 5.8, so the estimator returned -33.8 kHz
    # for a true +60 kHz offset and the demodulator then locked onto a rotation
    # that was not a symmetry of the constellation (65% bit accuracy).
    # Averaging overlapping segments pulls the true line clear of the noise.
    step = max(1, nfft // 2)
    acc = None
    count = 0
    for start in range(0, n - nfft + 1, step):
        seg = x[start:start + nfft] * np.blackman(nfft)
        s = np.abs(np.fft.fft(_raise(seg))) ** 2
        acc = s if acc is None else acc + s
        count += 1
    if count == 0:
        seg = x[:nfft] * np.blackman(nfft)
        acc = np.abs(np.fft.fft(_raise(seg))) ** 2
        count = 1

    spec = np.fft.fftshift(acc / count)
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / samp_rate))
    peak = freqs[int(np.argmax(spec))]

    # --- Sub-bin refinement -------------------------------------------------
    # The FFT peak is only accurate to one bin, and the residual after
    # dividing by `power` is therefore (samp_rate / nfft) / power. That matters
    # more than it looks: a residual frequency error is NOT a constant phase
    # offset, it accumulates linearly across the record, so it smears the
    # constellation even when it is small.
    #
    # Measured: BPSK at 250 ksps gives only 6000 samples, so nfft = 4096 and
    # the bin spacing is 244 Hz. The x^2 line lands one bin off, leaving
    # +58.6 Hz -- which drifts 132 degrees over 1500 symbols and pushed EVM to
    # 61.9%, above the lock threshold. The fix is not to pick a bigger exponent
    # (that trades away unambiguous span); it is to stop at bin resolution.
    #
    # This search uses the WHOLE record rather than one segment, so the line it
    # maximises is as sharp as the data allows.
    if refine:
        win = np.blackman(n)
        xw = x * win
        raised_all = _raise(xw)
        t_all = np.arange(n) / samp_rate
        half_bin = samp_rate / float(nfft) / 2.0
        grid = peak + np.linspace(-half_bin, half_bin, 41)
        best_f, best_mag = peak, -1.0
        for f in grid:
            mag = np.abs(np.sum(raised_all * np.exp(-1j * 2.0 * np.pi * f * t_all)))
            if mag > best_mag:
                best_mag, best_f = mag, float(f)
        peak = best_f

    offset = peak / power
    # Ambiguity: the M-th-power line repeats every samp_rate/M, so the true
    # offset may differ by a multiple of that. Fold to the nearest valid
    # value inside the Nyquist span.
    span = samp_rate / float(power)
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


def _mean_phase(symbols, n_sym_rots):
    """Coarse phase of the symbol cloud, folded into the symmetry group.

    Raising to n_sym_rots removes the modulation, so the angle of the mean is
    n_sym_rots times the residual phase. Repeated multiplication rather than
    `**`: on some numpy builds a complex power can silently drop the complex
    dtype, which would make this return a meaningless angle.
    """
    z = symbols.copy()
    for _ in range(int(n_sym_rots) - 1):
        z = z * symbols
    mean_vec = np.mean(z)
    if np.abs(mean_vec) <= 1e-12:
        return 0.0
    return float(np.angle(mean_vec) / n_sym_rots)


def _search_phase_rotation(symbols, const, n_sym_rots):
    """Pick the constant rotation that best explains the received symbols.

    Estimating the rotation from symbol statistics alone is unreliable: for a
    symmetric constellation the estimator is dominated by the symmetry
    ambiguity rather than the true offset. Instead, search the candidate
    rotations that are symmetries of the constellation and keep whichever
    minimises the distance to the constellation.
    """
    coarse = _mean_phase(symbols, n_sym_rots)
    candidates = [coarse + k * (2 * np.pi / (4 * n_sym_rots))
                  for k in range(-4, 5)]
    best_rot, best_score = coarse, np.inf
    for rot in candidates:
        test = symbols * np.exp(-1j * rot)
        d = np.min(np.abs(test[:, None] - const[None, :]), axis=1)
        s = float(np.sqrt(np.mean(d ** 2)))
        if s < best_score:
            best_score, best_rot = s, rot
    return float(best_rot)


def _estimate_residual_frequency(symbols, const, sps, samp_rate, blocks=64):
    """Residual frequency still present after the coarse carrier correction.

    Everything else in this module corrects a PHASE offset. A residual
    FREQUENCY error is a different failure: it accumulates linearly with symbol
    index, so even a small error smears the constellation over a long capture.
    Measured: a 58.6 Hz residual on a 250 ksps BPSK capture drifts 132 degrees
    across 1500 symbols, which pushed EVM to 61.9% and refused a signal that
    decodes perfectly once corrected.

    The estimate is DECISION-DIRECTED: slice each symbol to the nearest
    constellation point, multiply by its conjugate to remove the modulation,
    then take the phase slope of the block-averaged result. No symbol decisions
    are needed beyond the slice, and the block average suppresses noise.

    The M-th power nonlinearity is deliberately NOT used here. It is exact for
    PSK, but raising square 16QAM to the 4th power does not collapse it to one
    phase -- its 16 points land in three clusters (73.7, 180 and 286.3 degrees),
    so the "residual" read from that phase slope is a mixture and the resulting
    correction drags the constellation off. Measured: 16QAM EVM rose from 12%
    to 29% that way, close enough to the 35% refusal threshold to start
    rejecting good signals.

    Returns 0.0 when the slope is not credible, so the caller applies no
    correction rather than a wrong one.
    """
    n_blocks = len(symbols) // blocks
    if n_blocks < 3:
        return 0.0

    decided = const[np.argmin(np.abs(symbols[:, None] - const[None, :]), axis=1)]
    err = symbols * np.conj(decided)
    zc = err[:n_blocks * blocks].reshape(n_blocks, blocks).mean(axis=1)

    slope = np.polyfit(np.arange(n_blocks), np.unwrap(np.angle(zc)), 1)[0]
    candidate = float(slope * samp_rate / (2.0 * np.pi * blocks * sps))

    # Guard: a residual larger than a quarter of the symbol rate is not a
    # residual, it is a failed estimate. Discard rather than "correct".
    if abs(candidate) > (samp_rate / sps) / 4.0:
        return 0.0
    return candidate


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
    const = constellation_for(mod)
    if const is None:
        res.reason = f"unsupported modulation '{modulation}'"
        return res
    res.modulation = mod
    res.sps = float(sps)

    # --- 1. Carrier recovery ---------------------------------------------
    # The exponent must match the constellation's rotational symmetry order,
    # otherwise the modulation is not stripped and the estimate is wrong.
    n_sym_rots = SYMMETRY_ORDER[mod]

    # Always refine. An earlier revision gated the sub-bin refinement on the
    # constellation being constant modulus, because the refinement was then
    # measured to bias 16QAM by ~50 Hz on the x^4 line. That bias was an
    # artefact of refining against a SINGLE segment; the refinement now uses
    # the whole record, where the line is sharp, and the bias is gone.
    # Measured on 16QAM at 250 ksps: estimate error +58.6 Hz without the
    # refinement, -2.4 Hz with it. 58.6 Hz is not small -- at that symbol rate
    # it drifts 126 degrees across the record, which makes the rotation search
    # fit a moving cloud and cost 23 points of bit accuracy (77% vs 100%).
    offset = estimate_carrier_offset(x, samp_rate, power=n_sym_rots,
                                     refine=True)
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

    # --- 3b. Phase and residual frequency correction ---------------------
    # Iterated, because the two estimates are coupled. The rotation search
    # needs a stationary cloud, but a residual frequency error means the cloud
    # is drifting; conversely the frequency tracker is decision-directed and
    # needs a roughly correct rotation to slice against. Neither can go first
    # alone, so alternate them.
    #
    # One pass is not enough. Measured on 8PSK at 100 ksps (seed 9): a 22 Hz
    # residual drifts ~119 degrees across the record, which left the rotation
    # search fitting a moving cloud. It settled on +103.5 degrees -- not a
    # multiple of the 45-degree symmetry, so not a valid rotation -- and bit
    # accuracy collapsed to 65%. Working seeds land on 0 or a multiple of 45.
    #
    # The second rotation is not redundant either: removing a linear phase ramp
    # shifts the best constant rotation, so a rotation chosen before the
    # frequency correction is stale. Measured on 16QAM at 100 ksps, EVM 29.0%
    # before the second pass and 3.4% after -- and 3.4% is the noise floor of
    # the test signal.
    rot_total = 0.0
    residual_hz = 0.0
    for _ in range(2):
        rot = _search_phase_rotation(symbols, const, n_sym_rots)
        symbols = symbols * np.exp(-1j * rot)
        rot_total += rot

        f_step = _estimate_residual_frequency(symbols, const, sps, samp_rate)
        if f_step != 0.0:
            n_idx = np.arange(len(symbols))
            symbols = symbols * np.exp(
                -1j * 2.0 * np.pi * f_step * n_idx * sps / samp_rate)
            residual_hz += f_step

    res.phase_correction_deg = float(np.degrees(-rot_total))
    res.residual_freq_hz = residual_hz

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


# Constellation size order, smallest first. This IS the parsimony order.
CONSTELLATION_ORDER = ("BPSK", "QPSK", "8PSK", "16QAM")


# ---------------------------------------------------------------------------
# FSK -- a DIFFERENT DEMODULATION PATH, not a fifth constellation
# ---------------------------------------------------------------------------
# 2-FSK cannot go through `demodulate()` above, and the reason is structural
# rather than a missing constant. That function's chain starts with carrier
# recovery by the M-th-power method, which works by stripping the modulation
# and leaving a spectral line at M times the offset. For 2-FSK the
# constellation is a single-radius circle whose ROTATION RATE carries the
# information, so raising it to any power spreads energy rather than
# collapsing it -- there is no line to find.
#
# 2-FSK is therefore demodulated the way it is transmitted: recover the
# instantaneous frequency, find the two tones, and decide which tone each
# symbol period sits on. That needs no carrier recovery at all (a residual
# carrier offset moves BOTH tones equally, so it cancels in the decision) and
# no matched filter (a constant-envelope tone is already its own matched
# filter).
#
# The one hard problem is that the tone spacing is unknown, which is exactly
# what the classifier previously could not determine. The estimator below
# measures the spacing AND reports how well a two-tone model explains the
# signal, so the same call both identifies 2-FSK and supplies the parameter
# its demodulator needs.
#
# Measured separation (scratch/probe_fsk_snr_realistic.py), at this project's
# operating point of ~26-29 dB SNR:
#    2-FSK, 34 cases over rate x index x seed   unexplained 0.0000 .. 0.2008
#    BPSK/QPSK/8PSK/16QAM/CW/noise, 18 controls unexplained 0.3488 .. 1.0000
# The margin is taken between the WORST case of each family, not best cases.

# Maximum unexplained share for a signal to be called genuinely two-tone.
# Anchored in the measurement above: the hardest 2-FSK measured 0.2008 and the
# easiest control 0.3488, so the threshold sits between them. It is NOT set
# close to the 2-FSK side on purpose -- a real capture is less clean than a
# synthetic sweep, and a false "2-FSK" on a PSK capture is far worse than a
# missed narrow-deviation FSK, which is the region that should abstain.
FSK_MAX_UNEXPLAINED = 0.2748

# A two-tone fit needs enough samples to form a histogram worth reading.
FSK_MIN_SAMPLES = 512

# The two tones must be resolvable at all. Below this separation the
# modulation index is so small that a 2-FSK is spectrally a CW carrier, and
# the honest answer is an abstention rather than a decision.
FSK_MIN_SEPARATION_RAD = 0.02

# Below this the tones are so close that the decision is a coin flip on noise.
FSK_MIN_SYMBOL_SNR = 3.0


def estimate_fsk(x, nbins=512):
    """Measure two-tone structure in a signal's instantaneous frequency.

    Returns a dict with:
        is_two_tone     bool    -- does a two-tone model explain the signal?
        tone_lo/_hi     float   -- the two tones, radians/sample
        separation      float   -- spacing between them, radians/sample
        deviation_hz    float   -- peak-to-peak tone spacing in Hz (needs
                                   `samp_rate`; set by the caller)
        unexplained     float   -- share of samples the model cannot account
                                   for. LOW means genuinely two-tone.
        reason          str     -- why it declined, when it did

    Why "unexplained share" and not a raw statistic: every simpler statistic
    was measured and rejected. `np.std` of the differential phase has fully
    overlapping ranges between BPSK and 2-FSK (measured BPSK 0.4656..1.3831,
    2-FSK 0.0483..1.2570) because it is monotone in the modulation index. A
    separation-to-cluster-width ratio saturates at a mechanical fixed point of
    2.00. A two-cluster search quantises to its own histogram bin width. This
    one works because it is a GOODNESS OF FIT: the question is not "is there a
    statistic of the right size" but "do two tones actually explain these
    samples", which a phase-modulated signal cannot answer yes to.

    See docs/STATUS_DONE_VS_LEFT.md section 3c for the full record, including
    the four approaches that failed.
    """
    out = {
        "is_two_tone": False, "tone_lo": None, "tone_hi": None,
        "separation": 0.0, "deviation_hz": None, "unexplained": 1.0,
        "reason": "",
    }
    x = np.asarray(x, dtype=np.complex128)
    if x.size < FSK_MIN_SAMPLES:
        out["reason"] = f"insufficient samples ({x.size} < {FSK_MIN_SAMPLES})"
        return out

    # Instantaneous frequency as the adjacent-sample phase difference. This is
    # the standard discriminator; it is noisy at low SNR, which is why the
    # decision is made on the shape of the distribution rather than a single
    # sample's value.
    d = np.angle(x[1:] * np.conj(x[:-1]))

    hist, edges = np.histogram(d, bins=nbins, range=(-np.pi, np.pi))
    binw = float(edges[1] - edges[0])
    centres = (edges[:-1] + edges[1:]) / 2.0
    hist = hist.astype(np.float64)

    order = np.argsort(hist)[::-1]
    if hist.size == 0 or hist[order[0]] == 0:
        out["reason"] = "empty instantaneous-frequency distribution"
        return out

    i1 = int(order[0])
    # The second tone must be a genuinely separate peak, not the shoulder of
    # the first. 4 bins is the resolvability floor; the 10% share requirement
    # stops a lone stray bin from being promoted to "a second tone".
    i2 = None
    for i in order[1:]:
        if abs(int(i) - i1) >= 4 and hist[i] >= 0.10 * hist[i1]:
            i2 = int(i)
            break
    if i2 is None:
        out["reason"] = ("one dominant tone; not two-tone "
                         "(a CW carrier or a PSK/QAM capture)")
        return out

    o1 = float(centres[i1])
    o2 = float(centres[i2])
    sep = abs(o1 - o2)

    # Assign each sample to the nearer tone and count what is left over.
    dist1 = np.abs(np.angle(np.exp(1j * (d - o1))))
    dist2 = np.abs(np.angle(np.exp(1j * (d - o2))))
    near1 = dist1 <= dist2
    # The window scales with the spacing so a narrow tone pair can still
    # explain its own samples, with a 3-bin floor so it is never tighter than
    # the histogram resolution.
    window = max(3.0 * binw, 0.25 * sep)
    explained = np.where(near1, dist1, dist2) <= window
    unexplained = 1.0 - float(np.mean(explained))

    out["tone_lo"] = min(o1, o2)
    out["tone_hi"] = max(o1, o2)
    out["separation"] = sep
    out["unexplained"] = unexplained

    if sep < FSK_MIN_SEPARATION_RAD:
        out["reason"] = (f"tone separation {sep:.4f} rad/sample is below the "
                         f"resolvability floor {FSK_MIN_SEPARATION_RAD}; "
                         f"modulation index too small to decide")
        return out
    if unexplained > FSK_MAX_UNEXPLAINED:
        out["reason"] = (f"a two-tone model leaves {unexplained:.4f} of samples "
                         f"unexplained (limit {FSK_MAX_UNEXPLAINED}); this is "
                         f"not a two-tone signal")
        return out

    out["is_two_tone"] = True
    out["reason"] = (f"two tones {sep:.4f} rad/sample apart, "
                     f"{unexplained:.4f} unexplained")
    return out


def demodulate_fsk(x, samp_rate, fsk=None, sps=None):
    """Demodulate 2-FSK to hard-decision bits.

    Parameters
    ----------
    x : array_like of complex
        Complex baseband samples.
    samp_rate : float
        Sample rate in samples/sec.
    fsk : dict, optional
        Result of `estimate_fsk`. Measured here if not supplied, so the
        function is usable on its own.
    sps : float, optional
        Samples per symbol. Required -- without it there is no symbol clock
        to decide on.

    Returns
    -------
    DemodResult, with `modulation` set to "2-FSK" and `evm_percent`
    repurposed as a tone-separation margin measure (see the note in the body).

    Carrier recovery is deliberately ABSENT. A residual carrier offset shifts
    both tones by the same amount, so it cancels when the decision is "which of
    the two tones is this" -- there is nothing to recover. This is the one
    place 2-FSK is simpler than PSK, and adding a carrier loop here would
    reintroduce a failure mode the modulation does not have.
    """
    res = DemodResult()
    res.modulation = "2-FSK"

    x = np.asarray(x, dtype=np.complex128)
    if x.size < FSK_MIN_SAMPLES:
        res.reason = f"insufficient samples ({x.size} < {FSK_MIN_SAMPLES})"
        return res
    if sps is None:
        res.reason = "samples-per-symbol required (run symbol rate estimate)"
        return res
    if sps < 2.0:
        res.reason = (f"samples per symbol {sps:.2f} is below 2.0; "
                      f"symbol recovery is not possible at this rate")
        return res
    res.sps = float(sps)

    if fsk is None:
        fsk = estimate_fsk(x)
    if not fsk.get("is_two_tone"):
        res.reason = fsk.get("reason") or "not a two-tone signal"
        return res

    tone_lo = fsk["tone_lo"]
    tone_hi = fsk["tone_hi"]
    sep = fsk["separation"]
    if samp_rate:
        res.carrier_offset_hz = float(
            (tone_lo + tone_hi) / 2.0 * samp_rate / (2.0 * np.pi))
        res.residual_freq_hz = float(sep * samp_rate / (2.0 * np.pi))

    d = np.angle(x[1:] * np.conj(x[:-1]))
    sps_int = int(round(sps))
    if sps_int < 2:
        res.reason = "samples per symbol rounds below 2"
        return res

    # Decide on ONE sample per symbol, taken from the symbol's interior.
    #
    # MEASURED, and it took two attempts to get right, so both are recorded.
    #
    # Attempt 1 sampled the centre via `d[sps//2::sps]`. Correct for sps >= 3,
    # but at sps=2 that picks index 1 -- the LAST sample of the symbol -- which
    # straddles the boundary into the next symbol and carries its tone too.
    # Measured at 400 ksps: 51.63% bit accuracy, i.e. chance.
    #
    # Attempt 2 AVERAGED the discriminator over each symbol period, which is
    # the textbook move for a noisy discriminator. It was WORSE for the
    # phase-discontinuous case and the numbers say why. Ground truth with the
    # carrier offset accounted for, measured per sample position within a
    # symbol (dev=50 kHz at 100 ksps, sps=10):
    #     positions 0..8  error 0.022   (clean)
    #     position  9     error 0.776   (34x worse -- the boundary sample)
    # Averaging folds that one bad sample into every decision. The boundary
    # sample is not noise to be averaged away; it is a different symbol.
    #
    # So: sample the symbol's interior and EXCLUDE the last sample. The number
    # of usable interior samples is `sps_int - 1`, and the middle of that range
    # is `(sps_int - 1) // 2`, which gives index 0 for sps=2 (the only interior
    # sample), 1 for sps=3, 2 for sps=5, and 4 for sps=10 -- each well clear of
    # the boundary.
    usable = sps_int - 1
    mid = usable // 2
    centres = d[mid::sps_int]
    n_sym = len(centres)
    if n_sym < 8:
        res.reason = "too few symbols after decimation"
        return res

    mid_tone = (tone_lo + tone_hi) / 2.0
    # Which side of the midpoint between the tones does each symbol sit on?
    hi = (centres - mid_tone) > 0.0
    bits = hi.astype(np.uint8)

    # Quality measure. EVM has no meaning without a constellation, so the
    # analogue used here is the distance of each decision from the decision
    # boundary, expressed as a fraction of the half-spacing. A symbol sitting
    # exactly on a tone scores 1.0; one on the boundary scores 0.0. This is
    # reported through `evm_percent` as (1 - margin) so that LOWER IS BETTER,
    # matching every other modulation's convention and keeping the GUI's
    # existing "is this lock good" logic meaningful.
    offset = np.abs(centres - mid_tone)
    margin = float(np.mean(np.clip(offset / (sep / 2.0), 0.0, 1.0)))
    res.evm_percent = float((1.0 - margin) * 100.0)

    # Refuse a lock when the symbols sit on the decision boundary. Without
    # this a noise-only input produces a plausible-looking bitstream, which is
    # the failure this module exists to avoid.
    if margin < 0.10:
        res.reason = (f"symbols sit on the decision boundary (margin "
                      f"{margin:.3f}); tones are not resolvable")
        return res

    res.bits = bits
    # `symbols` is the per-symbol frequency offset as a complex phasor, so the
    # constellation-plotting path has something meaningful to draw: 2-FSK's
    # two points, on the unit circle.
    res.symbols = np.exp(1j * centres)
    res.n_symbols = n_sym
    res.locked = True
    res.reason = (f"two tones {sep:.4f} rad/sample apart, "
                  f"{n_sym} symbols, margin {margin:.3f}")
    return res



def constellation_for(modulation):
    """Ideal constellation points for a modulation name, or None if unknown."""
    mod = str(modulation).upper().replace("-", "")
    if mod == "BPSK":
        return np.array([1 + 0j, -1 + 0j])
    if mod == "QPSK":
        return np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
    if mod == "8PSK":
        return np.exp(1j * 2 * np.pi * np.arange(8) / 8)
    if mod == "16QAM":
        levels = np.array([-3, -1, 1, 3], dtype=np.float64) / np.sqrt(10)
        return np.array([i + 1j * q for i in levels for q in levels])
    return None


def _occupies_multiple_phases(res, const, min_phases=2, max_share=0.9):
    """Does this constellation actually MODULATE the signal?

    EVM alone cannot answer that, and getting it wrong produces the exact
    failure this module exists to avoid -- a confident, precise, meaningless
    result. Measured on genuine signals:

      - An unmodulated carrier is a single phase. A BPSK slice rotates that one
        point onto a constellation point and scores 0.2% EVM, i.e. a
        near-perfect fit for a signal carrying no symbols at all. Every symbol
        lands on the same point (share 1.00).
      - An ASK envelope has one phase and many amplitudes, so it fits 16QAM at
        8.3% EVM using only the two points along one diagonal (share 0.50).
        A share threshold alone therefore does not catch it.

    Both are excluded by a definitional requirement rather than a tuned
    threshold: a PSK or QAM signal must occupy at least TWO distinct
    constellation PHASES. An unmodulated carrier has one, and amplitude-only
    modulation has one, so neither can be a PSK/QAM signal.
    """
    if not res.locked or res.symbols is None or len(res.symbols) < 16:
        return False

    idx = np.argmin(np.abs(res.symbols[:, None] - const[None, :]), axis=1)
    counts = np.bincount(idx, minlength=len(const))
    if counts.max() / len(idx) > max_share:
        return False

    used = np.nonzero(counts)[0]
    angles = np.sort(np.angle(const[used]))
    distinct = 1
    for a, b in zip(angles, angles[1:]):
        if abs(b - a) > 1e-6:
            distinct += 1
    return distinct >= min_phases


def classify_constellation(x, samp_rate, sps, fit_evm_percent=10.0):
    """Identify the constellation by demodulating under each hypothesis.

    Returns (label, evms). `label` is None when no constellation explains the
    symbols -- the correct answer for noise, and preferable to a guess.

    Why parsimony: a lower-order constellation is a geometric SUBSET of a
    higher-order one. Every BPSK point is a QPSK point and every QPSK point is
    an 8PSK point, so a BPSK capture fits BPSK, QPSK and 8PSK equally well and
    EVM alone cannot choose between them. Among the constellations that fit
    (EVM below `fit_evm_percent`), take the one with the FEWEST points -- the
    simplest explanation that accounts for the data.

    This is what makes 8PSK and 16QAM identifiable at all. The spectral route
    cannot do it: measured on known signals, 8PSK's strongest M-th-power line
    is at x^2 rather than x^8, so spectrum-based order detection calls an 8PSK
    capture BPSK.

    Verified 144/144 over 4 modulations x 4 symbol rates x 3 excess bandwidths
    x 3 seeds, with 3/3 noise captures correctly refused and every failure mode
    an abstention rather than a wrong answer. Also verified to REFUSE an
    unmodulated carrier and an ASK envelope, both of which otherwise fit a
    constellation with a deceptively low EVM.
    (Reproduce: scratch/verify_modclass_parsimony.py,
     scratch/verify_no_symbols_guard.py)
    """
    evms = {}
    for hyp in CONSTELLATION_ORDER:
        res = demodulate(x, samp_rate, modulation=hyp, sps=sps)
        # A hypothesis only counts if it actually modulates the signal; see
        # `_occupies_multiple_phases`. Without this an unmodulated carrier is
        # reported as a perfect BPSK fit (measured EVM 0.2%).
        if res.locked and _occupies_multiple_phases(res, constellation_for(hyp)):
            evms[hyp] = res.evm_percent
        else:
            evms[hyp] = float("inf")

    fitting = [m for m in CONSTELLATION_ORDER if evms[m] < fit_evm_percent]
    return (fitting[0] if fitting else None), evms
