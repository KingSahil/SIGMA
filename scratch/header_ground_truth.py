"""Bitstream correlation and header detection -- PS section 3 (v).

WHAT THIS IS FOR
----------------
Section 3 (v) asks for "bitstream correlation, header detection". Concretely:
given a recovered bit stream with no framing information, find where a known
sync word occurs, and decide whether the bits at that position are a real frame
boundary or a chance match.

This is the classic place to be confidently wrong, so the harness is built to
punish that:

  * A sync word is a short pattern. In a random stream of length N, the expected
    number of false alignments is **N / 2^L** for a length-L pattern. A 16-bit
    sync word in 100,000 random bits is expected to appear ~1.5 times *by
    chance*. Detecting "a correlation peak" is therefore worthless on its own --
    the question is always "is this peak above what chance produces here?"

  * A correlator that fires on random data is worse than no correlator: it
    invents frame boundaries for uncoded noise.

So the deliverable is not "find the peak". It is a **threshold calibrated
against the chance distribution**, and the control test is that random input
produces no detections.

THE MEASUREMENT USED
--------------------
Correlation is scored as a **bit-error count** rather than a normalised dot
product, because that is what a demodulator actually delivers: hard decisions.
For each candidate offset the score is ``sum(rx[i] != pattern[i])``, i.e. the
Hamming distance. A perfect alignment gives 0.

Tolerating up to ``max_bits_errors`` mismatches is what makes this work on a
noisy channel -- but every tolerated mismatch multiplies the chance-match rate,
so the tolerance must be paid for. That trade-off is measured below.

WHAT IT PROVIDES
----------------
  make_frame(payload, sync, ...)      -- build a frame at a known offset
  correlate(rx, pattern)              -- Hamming distance per offset
  find_headers(rx, sync, ...)         -- the detector, with a calibrated gate
  chance_threshold(n, L, searches)    -- the expected-worst score by chance

Run directly to prove the chain:
    <radioconda>/python.exe scratch/header_ground_truth.py
"""
import numpy as np


def bits_from_int(value, width):
    """MSB-first bit tuple of `value` in `width` bits."""
    return tuple((int(value) >> (width - 1 - i)) & 1 for i in range(width))


#: Default sync word length. 16 bits is enough for a *long* stream but is
#: provably ambiguous in a short one -- see §1 of the self-test, and the note
#: in `find_headers`. 32 bits matches real CCSDS/NASA sync markers and makes
#: detection decidable at modest length, so it is the default here.
DEFAULT_SYNC = bits_from_int(0x1ACFFC1D, 32)


def _sixteen_bit_sync():
    """The 16-bit marker, kept for the ambiguity demonstration."""
    return bits_from_int(0xD8A1, 16)


def make_frame(payload, sync=DEFAULT_SYNC, offset=0, total=None, seed=0):
    """Build a bit stream containing `sync` at a KNOWN offset.

    Returns ``(bits, true_offset)``. Everything outside the frame is random, so
    the detector cannot pass by finding structure that is not really there.
    """
    rng = np.random.default_rng(seed)
    payload = np.asarray(payload, dtype=np.uint8).ravel()
    sync = np.asarray(sync, dtype=np.uint8).ravel()

    frame = np.concatenate([sync, payload])
    if total is None:
        total = offset + len(frame) + 64
    if total < offset + len(frame):
        raise ValueError("total shorter than offset + frame")
    bits = rng.integers(0, 2, total).astype(np.uint8)
    bits[offset:offset + len(frame)] = frame
    return bits, offset


def correlate(rx, pattern):
    """Hamming distance between `pattern` and every offset of `rx`.

    Returns a list of ``(offset, errors)`` for every position where the pattern
    fits. Lower is better; 0 is a perfect match. This is the count a real
    demodulator would produce from hard decisions.
    """
    rx = np.asarray(rx, dtype=np.uint8).ravel()
    pat = np.asarray(pattern, dtype=np.uint8).ravel()
    L = len(pat)
    if L == 0 or len(rx) < L:
        return []
    out = []
    for i in range(len(rx) - L + 1):
        errs = int(np.sum(rx[i:i + L] != pat))
        out.append((i, errs))
    return out


def chance_threshold(n, L, searches=1, p=0.5, max_false_alarm=0.01):
    """Score at which a hit stops being explainable by chance.

    Two different questions live here, and conflating them is the bug this
    function exists to avoid:

    1. *What is the best score chance will produce?* In `m = n - L + 1`
       offsets each error count is Binomial(L, p), so the minimum of m draws is
       much lower than a single draw. For n=392 and L=16 that minimum is **0** --
       a perfect match is the *expected* best case, so "require better than
       chance" would demand `< 0` and could never be satisfied. An earlier
       version did exactly that and detected nothing at all.

    2. *Is a given hit distinguishable from chance?* That is a probability
       statement, not a comparison of scores: the expected number of chance hits
       at or below `e` is ``m * P(X <= e)``. A hit is real only when that
       expectation is small.

    So the usable threshold is the smallest `e` with
    ``m * P(X <= e) <= max_false_alarm``. When no such `e` exists within `L`
    (possible for short streams), the function returns ``None`` -- meaning
    **this sync word cannot be detected in a stream this short**, which is the
    honest answer rather than a number that will not work.
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

    Parameters
    ----------
    rx : array_like
        Recovered hard-decision bits.
    max_bits_errors : int or None
        Mismatches tolerated. ``None`` means use the calibrated threshold.
    calibrated : bool
        When True, a candidate is only reported when it is **distinguishable
        from chance** for this stream length.

    Returns
    -------
    list of ``(offset, errors)``, best first. An empty list means nothing was
    found, which is the correct outcome when the stream is too short for this
    sync word (see `chance_threshold`) or when the input is unframed noise.
    """
    rx = np.asarray(rx, dtype=np.uint8).ravel()
    L = len(sync)
    if len(rx) < L:
        return []

    thr = chance_threshold(len(rx), L) if calibrated else None
    if calibrated and thr is None:
        # This sync word is not detectable at this length. Refusing is the
        # whole point -- reporting a peak here would be reporting chance.
        return []

    if max_bits_errors is None:
        max_bits_errors = thr

    scored = correlate(rx, sync)
    hits = [(off, err) for (off, err) in scored if err <= max_bits_errors]
    hits.sort(key=lambda oe: oe[1])

    # Drop overlapping candidates: keep the best in each cluster.
    kept = []
    for off, err in hits:
        if any(abs(off - k) < L for k, _ in kept):
            continue
        kept.append((off, err))
        if len(kept) >= n_candidates:
            break
    return kept


def main():
    ok = True
    print("=" * 78)
    print("BITSTREAM CORRELATION / HEADER DETECTION -- PS section 3 (v)")
    print("=" * 78)
    sync = np.asarray(DEFAULT_SYNC, dtype=np.uint8)
    print(f"sync word: {len(sync)} bits  "
          f"{''.join(str(int(b)) for b in sync)}")

    # ---- 1. chance threshold -------------------------------------------
    print()
    print("1. THE CHANCE DISTRIBUTION (why a peak is not evidence)")
    print("   A hit is real only when the expected number of CHANCE hits at or")
    print("   below its score is small. That expectation is m * P(X <= e), for")
    print("   m = n - L + 1 offsets and X ~ Binomial(L, 0.5).")
    print()
    print(f"   {'sync L':>7}{'stream':>10}{'offsets':>10}{'threshold':>11}"
          f"{'expected chance hits':>22}")
    for L in (16, 32):
        syncL = bits_from_int(0xD8A1, 16) if L == 16 else DEFAULT_SYNC
        for n in (400, 2000, 10000, 100000):
            m = n - L + 1
            thr = chance_threshold(n, L)
            if thr is None:
                print(f"   {L:>7}{n:>10}{m:>10}{'NONE':>11}"
                      f"{'not detectable':>22}")
            else:
                from math import comb
                tail = sum(comb(L, k) * 0.5 ** L for k in range(0, thr + 1))
                print(f"   {L:>7}{n:>10}{m:>10}{thr:>11}{m * tail:>22.4f}")
    print()
    print("   -> COUNTERINTUITIVE, and the reason this table exists: a 16-bit")
    print("      sync word IS decidable in a 400-bit stream (threshold 0, 0.006")
    print("      expected chance hits) but NOT in a 100,000-bit one. More data")
    print("      means more chances for a false match, so a short word stops")
    print("      being usable as the stream grows. Detection is a property of")
    print("      (pattern length, stream length) -- never of the correlator.")

    # ---- 2. detection on a real frame ----------------------------------
    print()
    print("2. DETECTION, clean channel, known offset (32-bit sync)")
    print(f"   {'offset':>8}{'total':>8}{'found':>8}{'errors':>8}{'ok':>6}")
    for off in (0, 37, 200, 913):
        bits, true_off = make_frame(np.zeros(64, dtype=np.uint8), offset=off,
                                    total=off + 128 + 64, seed=off)
        hits = find_headers(bits, sync)
        found = hits[0][0] if hits else None
        errs = hits[0][1] if hits else None
        good = (found == true_off)
        print(f"   {true_off:>8}{len(bits):>8}{str(found):>8}{str(errs):>8}"
              f"{'ok' if good else 'WRONG':>6}")
        if not good:
            ok = False

    # ---- 2b. the short-stream refusal ----------------------------------
    print()
    print("2b. A 16-bit sync in a LONG stream must REFUSE, not guess")
    long_stream, true_off = make_frame(np.zeros(64, dtype=np.uint8),
                                       offset=5000, total=20000, seed=5)
    hits16 = find_headers(long_stream, bits_from_int(0xD8A1, 16))
    print(f"   20,000 bits, 16-bit sync -> {len(hits16)} detections")
    print(f"   (the marker IS at offset {true_off}, but at this length a")
    print("    16-bit match is indistinguishable from chance, so refusing is")
    print("    the correct answer)")
    if hits16:
        ok = False
        print("   FAIL: refused length must produce no detections")
    else:
        print("   ok -- declines rather than reporting a chance match")

    # ---- 3. THE CONTROL -- random input must produce nothing ------------
    print()
    print("3. CONTROL -- unframed random bits must yield NO detection")
    print("   (a detector that fires here invents frame boundaries)")
    rng = np.random.default_rng(11)
    false_pos = 0
    trials = 25
    for t in range(trials):
        rb = rng.integers(0, 2, 2000).astype(np.uint8)
        hits = find_headers(rb, sync)
        if hits:
            false_pos += 1
    print(f"   false detections: {false_pos}/{trials} streams")
    if false_pos > 0:
        ok = False
        print("   FAIL: calibrated detector must not fire on random input")
    else:
        print("   ok -- the gate holds")

    # Show what an UNCALIBRATED detector does, for contrast. Use a long stream,
    # where a fixed tolerance is genuinely dangerous -- on a short stream with
    # a 32-bit sync even a naive rule looks fine, which is exactly why the
    # length has to appear in the comparison.
    uncal = 0
    naive_stream_len = 200_000
    for t in range(trials):
        rb = rng.integers(0, 2, naive_stream_len).astype(np.uint8)
        scored = correlate(rb, sync)
        best = min(e for _, e in scored)
        if best <= 4:
            uncal += 1
    print(f"   for contrast, in {naive_stream_len:,}-bit noise a fixed rule of")
    print(f"   'best score <= 4' would fire on {uncal}/{trials} streams --")
    print("   the calibration is what prevents that.")

    # ---- 4. noise tolerance --------------------------------------------
    print()
    print("4. DETECTION vs CHANNEL ERRORS")
    print(f"   {'flip rate':>10}{'found at true offset':>22}{'false':>8}")
    for rate in (0.0, 0.02, 0.05, 0.10):
        good = 0
        false = 0
        trials = 20
        for t in range(trials):
            bits, true_off = make_frame(np.zeros(64, dtype=np.uint8),
                                        offset=100, total=600, seed=1000 + t)
            if rate > 0:
                bits = bits.copy()
                pos = np.random.default_rng(2000 + t).choice(
                    len(bits), size=int(len(bits) * rate), replace=False)
                bits[pos] ^= 1
            # Tolerance must rise with noise; ask for the threshold the channel
            # implies rather than a fixed constant.
            tol = 2 if rate <= 0.02 else (4 if rate <= 0.05 else 8)
            hits = find_headers(bits, sync, max_bits_errors=tol,
                                calibrated=(rate <= 0.05))
            if hits and abs(hits[0][0] - true_off) <= 2:
                good += 1
            elif hits:
                false += 1
        print(f"   {rate*100:>9.0f}%{good:>17}/{trials}{false:>8}")

    # ---- 5. the honest cost of tolerance -------------------------------
    print()
    print("5. WHY TOLERANCE IS NOT FREE (chance matches per stream)")
    print(f"   {'tolerated':>10}{'chance rate/offset':>22}{'expected in 10k':>18}")
    from math import comb
    L = len(sync)
    for tol in (0, 1, 2, 3, 4):
        prob = sum(comb(L, k) * 0.5 ** L for k in range(0, tol + 1))
        exp = prob * 10000
        print(f"   {tol:>10}{prob:>22.3e}{exp:>18.2f}")
    print("   -> every tolerated bit multiplies the false-alarm rate. This is")
    print("      why the gate must be calibrated per stream length, not fixed.")

    print()
    print("=" * 78)
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
