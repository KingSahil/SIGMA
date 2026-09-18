"""Coding-layer analysis for PS section 3 (iii) / (iv).

Everything here operates on the **demodulated bit stream** produced by
``sigma_demod.demodulate()`` (``DemodResult.bits``). Nothing in this module
touches IQ samples or the GUI.

Design rule that shapes the whole file: **a FEC decoder cannot be verified
without coded input.** Running Viterbi over uncoded bits returns confident
garbage that looks like a decode. So the encoder lives here alongside the
decoder, the decode is always reported with the *re-encode residual* that
proves the input was a valid codeword, and no function ever claims a decoded
payload unless that residual is near zero.

Chain this module implements::

    demodulated bits -> de-interleave -> convolutional decode -> information bits

and, for detection::

    demodulated bits -> for each candidate interleaver: de-interleave,
                        decode, re-encode, measure residual -> name the mode

What this module does NOT do
----------------------------
It does not *discover* an unknown FEC code. The code (a (2,1,3) convolutional
code by default) is an input, because that is what the receiver has. Blind
identification of an unknown code from a bit stream is not implemented, and
nothing here should be described as if it were.

Provenance note: the measurements backing these functions were established in
``scratch/fec_ground_truth.py`` and ``scratch/verify_interleaver_detect.py``.
Those files remain the scored ground truth; this module is the shipped copy.
"""

import numpy as np

# ---------------------------------------------------------------------------
# The code
# ---------------------------------------------------------------------------

#: Constraint length. K=3 means a 2-bit state memory (4 states).
DEFAULT_K = 3

#: Generator polynomials, LSB = most recent bit. (2,1,3) NASA/CCSDS code.
DEFAULT_POLYS = (0b111, 0b101)

#: The four interleaver families named in PS section 3 (iii).
INTERLEAVE_MODES = ("block", "convolutional", "diagonal", "pseudo_random")


# ---------------------------------------------------------------------------
# Convolutional encoding
# ---------------------------------------------------------------------------


def conv_encode(bits, K=DEFAULT_K, polys=DEFAULT_POLYS):
    """Encode bits with a rate-1/len(polys) convolutional code.

    Returns a ``uint8`` array of length ``len(bits) * len(polys)``.

    The stream is terminated with ``K-1`` zero tail bits so the trellis returns
    to state 0. Without termination the final state is unknown and a decoder has
    to guess it, which silently loses the last few information bits and makes a
    correct decoder look broken.
    """
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    n_out = len(polys)
    state_bits = K - 1

    padded = np.concatenate([bits, np.zeros(state_bits, dtype=np.uint8)])

    out = np.zeros(len(padded) * n_out, dtype=np.uint8)
    reg = 0                       # the previous K-1 bits
    for i, b in enumerate(padded):
        # The K-bit window is the current bit FOLLOWED BY the previous K-1 bits,
        # so `reg` must hold the history *before* this bit is shifted in.
        #
        # An earlier version shifted the current bit into `reg` first and then
        # OR'd it on top, so the window contained the current bit twice and
        # dropped the oldest history bit. Generator 2 (0b101) then fired on a
        # 2-bit window and emitted 0 almost always -- still a plausible-looking
        # bitstream, and it cost hours of chasing the wrong bug.
        window = int(b)
        hist = reg
        for _ in range(state_bits):
            window = (window << 1) | (hist & 1)
            hist >>= 1
        reg = ((reg << 1) | int(b)) & ((1 << state_bits) - 1) if state_bits else 0
        for j, p in enumerate(polys):
            out[i * n_out + j] = bin(window & p).count("1") & 1
    return out


# ---------------------------------------------------------------------------
# Viterbi decoding
# ---------------------------------------------------------------------------


def viterbi_decode(rx, K=DEFAULT_K, polys=DEFAULT_POLYS, soft=False):
    """Hard/soft-decision Viterbi decode. Returns the information bits.

    Parameters
    ----------
    rx : array_like
        Received bits (or soft values when ``soft=True``), grouped in blocks of
        ``len(polys)`` per trellis step.
    soft : bool
        When True, ``rx`` holds float reliabilities; the branch metric becomes a
        Euclidean distance instead of a Hamming distance.

    Notes
    -----
    The traceback stores the **predecessor state**, not the input bit. This is
    not an optimisation -- reversing ``next = (prev >> 1) | (bit << (K-2))``
    from ``(next, bit)`` recovers ``bit`` and the predecessor's high bit, but
    the predecessor's **low bit is not recoverable**. Every ``(next, bit)`` pair
    for K=3 has exactly 2 predecessors, so a traceback that reconstructs the
    state from the bit walks a path that never existed. It does not crash; it
    returns ~47% and is completely insensitive to noise, because it locks onto
    one fixed path (in practice the all-zero one).
    """
    rx = np.asarray(rx, dtype=np.float64).ravel()
    n_out = len(polys)
    n_steps = len(rx) // n_out
    if n_steps == 0:
        return np.zeros(0, dtype=np.uint8)

    state_bits = K - 1
    n_states = 1 << state_bits
    INF = np.inf

    # CONVENTION -- the part that is easy to get silently wrong.
    #
    # A trellis state is the encoder's memory BEFORE the current bit:
    #
    #     state holds (b[t-1], b[t-2], ..., b[t-(K-1)])  as a K-1 bit word
    #
    # so the K-bit window is  window = (bit << (K-1)) | state, MSB = oldest,
    # matching conv_encode().
    #
    # The tempting alternative -- defining the state as the register AFTER
    # shifting the new bit in -- produces a perfectly self-consistent trellis
    # that is simply NOT the encoder's, because the window then doubles the
    # newest bit and drops the oldest. The decoder runs happily and returns
    # ~50% garbage on a noiseless channel.
    #
    # This port initially built the window with a linear-feedback shift
    # (`window = bit; then shift in history bits`), which reverses the bit
    # order relative to `(bit << state_bits) | state`. Measured: 54.25% on a
    # noiseless channel and a re-encode residual of 0.32 instead of 0.0000.
    # Build the window the same way the encoder does, from the same pieces.
    def window_for(state, bit):
        return (bit << state_bits) | state

    def emit(state, bit):
        w = window_for(state, bit)
        return [bin(w & p).count("1") & 1 for p in polys]

    def step(state, bit):
        """New history after consuming `bit`: shift right, insert at the top."""
        return (state >> 1) | (bit << (state_bits - 1)) if state_bits else 0

    path_metric = np.full(n_states, INF)
    path_metric[0] = 0.0                     # encoder memory starts empty
    # pred_table[t, ns] = the predecessor STATE that reached ns at step t.
    pred_table = np.zeros((n_steps, n_states), dtype=np.int32)

    for t in range(n_steps):
        rx_t = rx[t * n_out:(t + 1) * n_out]
        new_metric = np.full(n_states, INF)
        for state in range(n_states):
            if path_metric[state] == INF:
                continue
            for b in (0, 1):
                ns = step(state, b)
                exp = emit(state, b)
                if soft:
                    # Correlation metric: soft value times expected sign.
                    cost = -sum(v if e == 0 else -v
                                for v, e in zip(rx_t, exp))
                else:
                    cost = float(sum(1 for v, e in zip(rx_t, exp)
                                     if int(v) != e))
                cand = path_metric[state] + cost
                if cand < new_metric[ns]:
                    new_metric[ns] = cand
                    pred_table[t, ns] = state
        path_metric = new_metric

    # Terminated trellis: start the traceback from state 0 when reachable.
    state = 0 if path_metric[0] < INF else int(np.argmin(path_metric))
    bits = np.zeros(n_steps, dtype=np.uint8)
    for t in range(n_steps - 1, -1, -1):
        prev = int(pred_table[t, state])
        # Recover the input bit from (prev -> state): it is the state's top bit.
        bits[t] = (state >> (state_bits - 1)) & 1 if state_bits else 0
        state = prev

    # Drop the K-1 terminating tail bits.
    return bits[:max(len(bits) - state_bits, 0)]


# ---------------------------------------------------------------------------
# Interleavers
# ---------------------------------------------------------------------------


def _block_perm(n, rows, cols):
    """Write row-wise, read column-wise."""
    assert rows * cols == n, f"block interleaver needs rows*cols == n ({rows}*{cols} != {n})"
    perm = np.empty(n, dtype=np.int64)
    k = 0
    for c in range(cols):
        for r in range(rows):
            perm[k] = r * cols + c
            k += 1
    return perm


def _diagonal_perm(n, rows, cols):
    """Block interleaver with each row rotated by its own index (DVB-style)."""
    assert rows * cols == n, f"diagonal interleaver needs rows*cols == n ({rows}*{cols} != {n})"
    perm = np.empty(n, dtype=np.int64)
    k = 0
    for c in range(cols):
        for r in range(rows):
            perm[k] = r * cols + (c + r) % cols
            k += 1
    return perm


def _convolutional_perm(n, S, j):
    """Forney (S, 1, j) stream interleaver.

    Branch index is ``i = index mod S``; each branch is skewed by ``i * j``.
    This is a genuine stream interleaver -- it needs no block alignment, which
    is why it is used on continuous links.
    """
    counters = [0] * S
    out_slot = np.empty(n, dtype=np.int64)
    per_branch = []
    for i in range(S):
        per_branch.append(len(range(i, n, S)))
    starts = np.zeros(S, dtype=np.int64)
    acc = 0
    for i in range(S):
        starts[i] = acc
        acc += per_branch[i]
    for idx in range(n):
        i = idx % S
        pos = counters[i]
        counters[i] += 1
        out_slot[idx] = starts[i] + pos
    for i in range(S):
        span = per_branch[i]
        if span == 0:
            continue
        rot = (i * j) % span
        seg = out_slot[starts[i]:starts[i] + span].copy()
        out_slot[starts[i]:starts[i] + span] = np.roll(seg, rot)
    perm = np.empty(n, dtype=np.int64)
    for idx in range(n):
        perm[out_slot[idx]] = idx
    return perm


def _pseudo_random_perm(n, seed=12345):
    return np.random.default_rng(seed).permutation(n).astype(np.int64)


def interleave_perm(n, mode, rows=None, cols=None, S=8, j=2, seed=12345):
    """Return `perm` such that ``interleaved == bits[perm]``.

    Returning the permutation (rather than shuffling inline) is what makes
    de-interleaving *provable*: the inverse is ``argsort(perm)``, and the
    self-test asserts round-tripping for every mode.
    """
    if mode == "pseudo_random":
        return _pseudo_random_perm(n, seed)
    if mode == "convolutional":
        return _convolutional_perm(n, S, j)

    if rows is None or cols is None:
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        if rows * cols != n:
            for c in range(cols, 1, -1):
                if n % c == 0:
                    cols, rows = c, n // c
                    break
            if rows * cols != n:
                raise ValueError(
                    f"n={n} is prime; block/diagonal interleaving needs a "
                    f"composite length. Pad the input or pass rows/cols.")
    if mode == "block":
        return _block_perm(n, rows, cols)
    if mode == "diagonal":
        return _diagonal_perm(n, rows, cols)
    raise ValueError(f"unknown interleave mode {mode!r}")


def interleave(bits, mode, **kw):
    """Interleave a bit array under `mode`."""
    perm = interleave_perm(len(bits), mode, **kw)
    return np.asarray(bits, dtype=np.uint8)[perm]


def deinterleave(bits, mode, **kw):
    """Inverse of :func:`interleave`."""
    perm = interleave_perm(len(bits), mode, **kw)
    out = np.empty(len(bits), dtype=np.uint8)
    out[perm] = np.asarray(bits, dtype=np.uint8)
    return out


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def reencode_residual(bits, K=DEFAULT_K, polys=DEFAULT_POLYS):
    """Fraction of positions where decode + re-encode fails to reproduce `bits`.

    This is the codeword-validity test for a **non-systematic** code, where
    there is no direct parity check on the raw bits:

        decode(bits) -> re-encode -> compare

    ~0.000 means the input was a valid codeword (or within the correction
    radius). ~0.14 means it was not a codeword at all.

    Measured on 192 information bits: clean codeword 0.0000, three channel
    errors 0.0077, shuffled codeword 0.1366, random bits 0.1418.

    This is a *ranking* signal, not a threshold: Viterbi always returns the
    nearest codeword, so even scrambled input re-encodes to something merely
    somewhat-off rather than maximally wrong.
    """
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    if len(bits) < 8:
        return 1.0
    dec = viterbi_decode(bits, K=K, polys=polys)
    re = conv_encode(dec, K=K, polys=polys)
    m = min(len(re), len(bits))
    if m == 0:
        return 1.0
    return float(np.mean(re[:m] != bits[:m]))


def _factorisations(n, max_candidates=8):
    """Plausible ``(rows, cols)`` pairs for a block interleaver of length `n`.

    A real receiver does **not** know the block geometry, so guessing a single
    factorisation is not sufficient. Measured failure of that approach: a
    stream generated with rows=49, cols=8 was auto-factorised to rows=28,
    cols=14 (the largest factor <= sqrt(n)), and the detector then scored
    ``block`` as ``convolutional`` and declined ``diagonal`` -- the hypotheses
    it tested were simply *different interleavers*.

    So enumerate the factorisations instead. Ordered near-square first, since
    that is the common choice, but the search covers all of them.
    """
    pairs = []
    for c in range(1, n + 1):
        if n % c == 0:
            pairs.append((n // c, c))
    if not pairs:
        return []
    # Near-square first: minimise |rows - cols|.
    pairs.sort(key=lambda rc: abs(rc[0] - rc[1]))
    return pairs[:max_candidates]


def detect_interleaver(bits, K=DEFAULT_K, polys=DEFAULT_POLYS,
                       rows=None, cols=None, S=8, j=2, margin=0.02,
                       return_geometry=False):
    """Name the interleaving mode of an interleaved *coded* bit stream.

    The detector is given the coded bits and the FEC code (the receiver's
    legitimate advantage) but **not** the permutation. Each candidate mode is
    constructed from its parameters, applied as a de-interleaver, and scored by
    :func:`reencode_residual`; the lowest residual wins.

    When ``rows``/``cols`` are not supplied, every plausible factorisation is
    searched (see :func:`_factorisations`) rather than a single guess.

    Returns ``(mode, scores)`` where `mode` is one of ``INTERLEAVE_MODES`` or
    ``None`` when no candidate is clearly best. Declining is a legitimate
    outcome. With ``return_geometry=True`` the return is
    ``(mode, scores, geometry)`` where ``geometry`` maps mode -> the
    ``(rows, cols)`` that achieved its best score; the caller needs this to
    de-interleave with the same parameters that won.

    Measured performance (192 information bits): 4/4 blind on a clean channel
    when the geometry is searched. The earlier single-guess version scored
    **2/4** on the same data -- a bug found only by exercising this function
    through its real caller rather than in isolation.

    KNOWN LIMITATION: past ~15% channel errors the detector mostly answers
    *wrong* rather than declining (at 30%: 24/40 wrong, 9/40 declined). The
    residual never becomes large enough to trip an absolute threshold, because
    Viterbi always returns a nearest codeword. The `margin` only catches
    near-ties, not confidence collapse. Do not describe this as "abstains when
    unsure" without re-measuring.
    """
    n = len(bits)

    if rows is not None and cols is not None:
        geometry = [(rows, cols)]
    else:
        geometry = _factorisations(n)

    scores = {}
    chosen_geometry = {}
    for mode in INTERLEAVE_MODES:
        best = None
        best_rc = None
        for (r, c) in geometry:
            if r * c != n:
                continue
            try:
                perm = interleave_perm(n, mode, rows=r, cols=c, S=S, j=j)
                cand = np.empty(n, dtype=np.uint8)
                cand[perm] = np.asarray(bits, dtype=np.uint8)
                val = reencode_residual(cand, K=K, polys=polys)
            except Exception:
                continue
            if best is None or val < best:
                best = val
                best_rc = (r, c)
        if best is not None:
            scores[mode] = best
            chosen_geometry[mode] = best_rc

    if not scores:
        return (None, {}, {}) if return_geometry else (None, {})
    best_mode = min(scores, key=scores.get)
    ordered = sorted(scores.values())
    if len(ordered) > 1 and (ordered[1] - ordered[0]) < margin:
        return (None, scores, chosen_geometry) if return_geometry else (None, scores)
    if return_geometry:
        return best_mode, scores, chosen_geometry
    return best_mode, scores


# ---------------------------------------------------------------------------
# Bitstream correlation / header detection (PS section 3 v)
# ---------------------------------------------------------------------------


def bits_from_int(value, width):
    """MSB-first bit tuple of `value` in `width` bits."""
    return tuple((int(value) >> (width - 1 - i)) & 1 for i in range(width))


#: Default sync word: 32 bits, the shape of real CCSDS/NASA sync markers.
#: Length matters more than the correlator does -- see `chance_threshold`.
DEFAULT_SYNC = bits_from_int(0x1ACFFC1D, 32)


def correlate(rx, pattern):
    """Hamming distance between `pattern` and every offset of `rx`.

    Returns a list of ``(offset, errors)``. Lower is better; 0 is a perfect
    match. Hard decisions, because that is what a demodulator delivers.
    """
    rx = np.asarray(rx, dtype=np.uint8).ravel()
    pat = np.asarray(pattern, dtype=np.uint8).ravel()
    L = len(pat)
    if L == 0 or len(rx) < L:
        return []
    out = []
    for i in range(len(rx) - L + 1):
        out.append((i, int(np.sum(rx[i:i + L] != pat))))
    return out


def chance_threshold(n, L, p=0.5, max_false_alarm=0.01):
    """Score at which a hit stops being explainable by chance, or ``None``.

    Two distinct questions get conflated here, and doing so is a real bug:

    1. *What is the best score chance will produce?* With ``m = n - L + 1``
       offsets and each error count ``Binomial(L, p)``, the minimum of m draws
       sits far below a single draw. Requiring "strictly better than that
       minimum" is **unsatisfiable** whenever the minimum is already 0 -- and
       an implementation that did this detected nothing at all.

    2. *Is a given hit distinguishable from chance?* That is a probability
       statement: the expected number of chance hits at or below ``e`` is
       ``m * P(X <= e)``. A hit is usable only when that expectation is small.

    So this returns the smallest ``e`` with ``m * P(X <= e) <= max_false_alarm``
    and ``None`` when no such ``e`` exists -- meaning "this sync word cannot be
    detected in a stream this long", which is the honest answer.

    Note the counterintuitive consequence, measured in the self-test: a 16-bit
    word IS decidable in a 400-bit stream but NOT in a 100,000-bit one. More
    data means more chances for a false match, so a short marker stops being
    usable as the stream grows.
    """
    from math import comb
    m = max(n - L + 1, 1)
    for e in range(0, L + 1):
        tail = sum(comb(L, k) * (p ** k) * ((1 - p) ** (L - k))
                   for k in range(0, e + 1))
        if m * tail <= max_false_alarm:
            return e
    return None


def find_headers(rx, sync=DEFAULT_SYNC, max_bits_errors=None, n_candidates=4,
                 calibrated=True):
    """Find sync-word positions in a bit stream.

    Returns a list of ``(offset, errors)``, best first. **An empty list is the
    correct answer** when the stream is unframed noise, or too long for this
    sync word to be distinguishable from chance. Reporting a peak in either
    case would be reporting chance as a detection.
    """
    rx = np.asarray(rx, dtype=np.uint8).ravel()
    L = len(sync)
    if len(rx) < L:
        return []

    thr = chance_threshold(len(rx), L) if calibrated else None
    if calibrated and thr is None:
        return []

    if max_bits_errors is None:
        max_bits_errors = thr

    hits = [(off, err) for (off, err) in correlate(rx, sync)
            if err <= max_bits_errors]
    hits.sort(key=lambda oe: oe[1])

    kept = []
    for off, err in hits:
        if any(abs(off - k) < L for k, _ in kept):
            continue
        kept.append((off, err))
        if len(kept) >= n_candidates:
            break
    return kept


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


class CodingResult:
    """Outcome of the coding-layer analysis over a demodulated bit stream."""

    def __init__(self):
        self.analysed = False
        self.reason = ""
        self.interleaver = None          # detected mode, or None
        self.interleaver_scores = {}     # mode -> reencode residual
        self.interleaver_geometry = {}   # mode -> (rows, cols) that won
        self.residual = None             # residual under the chosen mode
        self.had_fec = False             # did the stream look like a codeword?
        self.decoded_bits = None         # information bits after FEC decode
        self.n_bits_in = 0
        self.n_bits_out = 0
        # PS section 3 (v): sync-word / frame-boundary search.
        self.sync_hits = []              # [(offset, errors)] best first
        self.sync_detectable = None      # None = not decidable at this length

    def __repr__(self):
        if not self.analysed:
            return f"<CodingResult NOT ANALYSED: {self.reason}>"
        fec = 'yes' if self.had_fec else 'no'
        syn = (f"{len(self.sync_hits)} sync" if self.sync_hits
               else ("no sync" if self.sync_detectable is not None
                     else "sync n/a"))
        return (f"<CodingResult {self.interleaver or 'no interleaver'} "
                f"FEC={fec} {syn} "
                f"residual={self.residual:.4f}>"
                if self.residual is not None else
                f"<CodingResult {self.interleaver or 'unknown'}>")


def analyse_coding_layer(bits, K=DEFAULT_K, polys=DEFAULT_POLYS,
                         try_interleavers=True, min_bits=32,
                         sync=DEFAULT_SYNC, try_headers=True):
    """Run interleaver detection, FEC decode and header search over bit stream.

    Parameters
    ----------
    bits : array_like
        The hard-decision bits from ``DemodResult.bits``.
    try_interleavers : bool
        When False, skip detection and evaluate the stream assuming it was not
        interleaved. Useful for a fast path.
    sync : array_like
        Sync word for the header search (PS section 3 v). Defaults to a 32-bit
        CCSDS-shaped marker.
    try_headers : bool
        When False, skip the header search.

    Returns
    -------
    CodingResult

    Honest behaviour on ordinary (uncoded, unframed) traffic: the residual will
    be high (~0.13+), ``had_fec`` stays False, ``decoded_bits`` is left as None,
    and ``sync_hits`` is empty. Viterbi over uncoded bits *would* return
    something, and reporting it would be the bug -- so this function refuses
    instead.
    """
    res = CodingResult()
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    res.n_bits_in = len(bits)

    if len(bits) < min_bits:
        res.reason = f"only {len(bits)} bits; need >= {min_bits} to analyse"
        return res

    # 0. Header search. Independent of FEC: a framing pattern can be present on
    #    an uncoded stream, so this runs regardless. An empty result is normal.
    if try_headers:
        res.sync_detectable = chance_threshold(len(bits), len(sync))
        if res.sync_detectable is not None:
            res.sync_hits = find_headers(bits, sync)

    # 1. Is this a valid codeword as-is?
    direct = reencode_residual(bits, K=K, polys=polys)

    # 2. If not, does any interleaver make it one?
    interleaver = None
    scores = {}
    geom = {}
    if try_interleavers:
        interleaver, scores, geom = detect_interleaver(
            bits, K=K, polys=polys, return_geometry=True)
    res.interleaver = interleaver
    res.interleaver_scores = scores
    res.interleaver_geometry = geom
    chosen = scores.get(interleaver) if interleaver else direct
    res.residual = direct if chosen is None else chosen

    # A genuine codeword reproduces itself (or comes within the code's
    # correction radius). Anything above this is not a codeword and must not be
    # decoded -- see the note in the docstring.
    FEC_THRESHOLD = 0.03
    if res.residual <= FEC_THRESHOLD:
        res.had_fec = True
        target = bits
        if interleaver:
            # De-interleave with the geometry that actually won, not a default.
            # Using the wrong factorisation here silently decodes the wrong
            # permutation of the bits and reports it as a payload.
            geom = res.interleaver_geometry or {}
            rc = geom.get(interleaver)
            kw = {"rows": rc[0], "cols": rc[1]} if rc else {}
            perm = interleave_perm(len(bits), interleaver, **kw)
            target = np.empty(len(bits), dtype=np.uint8)
            target[perm] = bits
        res.decoded_bits = viterbi_decode(target, K=K, polys=polys)
        res.n_bits_out = len(res.decoded_bits)
        res.analysed = True
        res.reason = ("valid codeword"
                      + (f"; interleaver {interleaver}" if interleaver else "")
                      + _sync_suffix(res))
        return res

    res.analysed = True
    res.reason = (f"no FEC detected (residual {res.residual:.3f} > "
                  f"{FEC_THRESHOLD:.2f}); stream appears uncoded or is not a "
                  f"codeword" + _sync_suffix(res))
    return res


def _sync_suffix(res):
    """Human-readable header-search outcome, appended to a reason string."""
    if res.sync_hits:
        off, err = res.sync_hits[0]
        return f"; header found at bit {off} ({err} bit errors)"
    if res.sync_detectable is None:
        return "; no header search (sync word not decidable at this length)"
    return ""
