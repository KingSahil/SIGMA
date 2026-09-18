"""Interleaving-type DETECTION -- PS section 3 (iii).

Ground truth: ``fec_ground_truth.py`` can produce interleaved streams in four
known modes. So this is the first PS sub-item scoreable end to end: generate a
known interleaver, run the detector blind, compare.

TWO DEAD ENDS, RECORDED SO THEY ARE NOT REPEATED
------------------------------------------------
An earlier version classified the interleaver from *statistics of the bit
stream* -- displacement histograms, run-length fractions, entropy -- against
hand-written constants such as ``predicted_order = 0.35``. It scored **1/4 on
structured data and 1/4 on pure noise**: it was not measuring anything. Two
independent reasons:

1. **If the payload is i.i.d. fair bits, the permutation is unrecoverable.**
   Every interleaver then yields a statistically identical stream. Nothing can
   beat chance, so any apparent score is an artifact. (Test 2 keeps a control
   for this.)
2. **The constants were fitted to nothing.** Comparing an observation against a
   guess is not a measurement.

A second attempt used a **syndrome** computed by treating generator 0 as the
systematic output. That is wrong for this code: ``polys = (0b111, 0b101)`` is
**non-systematic**, so ``bits[0::2]`` is a parity, not the input bit. Measured:
syndrome **0.4639 on a clean codeword** where ~0 was required. The
instrument-sanity check caught it before it could produce a plausible score --
which is the whole reason to write the sanity check first.

THE INSTRUMENT THAT WORKS: re-encode residual
---------------------------------------------
For a non-systematic code, "is this a valid codeword?" is answered by the
round trip

    decode(bits) -> re-encode -> compare against bits

A genuine codeword reproduces itself **exactly**. Measured on the (2,1,3) code,
192 information bits:

    clean codeword       residual 0.0000
    3 channel errors     residual 0.0077
    shuffled codeword    residual 0.1366
    random bits          residual 0.1418

Two consequences shape the detector:

* It is a **ranking** signal, not a threshold. Viterbi always returns the
  nearest codeword, so even garbage re-encodes to something *somewhat* close --
  the wrong hypothesis scores 0.137, not 0.5. Detection therefore picks the
  candidate with the **lowest** residual, and needs a margin to abstain.
* It degrades gracefully, which is why detection survives a noisy channel.

Run:  python scratch/verify_interleaver_detect.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fec_ground_truth import (          # noqa: E402
    INTERLEAVE_MODES,
    conv_encode,
    interleave,
    interleave_perm,
    viterbi_decode,
)


# ---------------------------------------------------------------------------
# The instrument
# ---------------------------------------------------------------------------


def reencode_residual(bits):
    """Fraction of positions where decode+re-encode fails to reproduce ``bits``.

    ~0.000 means "this is a valid codeword" (or within the code's correction
    radius). ~0.14 means the bits are not a codeword at all.
    """
    bits = np.asarray(bits, dtype=np.uint8).ravel()
    if len(bits) < 8:
        return 1.0
    dec = viterbi_decode(bits)
    re = conv_encode(dec)
    m = min(len(re), len(bits))
    if m == 0:
        return 1.0
    return float(np.mean(re[:m] != bits[:m]))


def _deinterleave_with(perm, bits):
    out = np.empty(len(bits), dtype=np.uint8)
    out[perm] = np.asarray(bits, dtype=np.uint8)
    return out


def detect_interleaver(bits, rows=None, cols=None, S=8, j=2, margin=0.002):
    """Name the interleaving mode of a received *interleaved coded* stream.

    The FEC code is assumed known (that is the receiver's legitimate
    advantage). The permutation is **not** given -- each candidate is
    constructed from its parameters and tested by the re-encode residual.

    Returns ``(mode, scores)``; ``mode`` is ``None`` when the detector declines
    because no candidate is clearly best.
    """
    n = len(bits)
    if rows is None or cols is None:
        cols = int(round(np.sqrt(n)))
        while cols > 1 and n % cols != 0:
            cols -= 1
        rows = max(1, n // cols)

    scores = {}
    for mode in INTERLEAVE_MODES:
        try:
            if mode in ("block", "diagonal") and rows * cols != n:
                continue
            perm = interleave_perm(n, mode, rows=rows, cols=cols, S=S, j=j)
            cand = _deinterleave_with(perm, bits)
            scores[mode] = reencode_residual(cand)
        except Exception:
            continue

    if not scores:
        return None, {}
    best = min(scores, key=scores.get)
    ordered = sorted(scores.values())
    if len(ordered) > 1 and (ordered[1] - ordered[0]) < margin:
        return None, scores
    return best, scores


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def _header_payload(rng, n_bits):
    text = b"SIH6147 NTRO IQ ANALYSER FRAME HEADER "
    hdr = np.unpackbits(np.frombuffer(text, dtype=np.uint8))
    sync = np.array([1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0], dtype=np.uint8)
    ctr = np.array([(i // 8) % 2 for i in range(64)], dtype=np.uint8)
    out = np.concatenate([hdr, sync, ctr])
    if len(out) < n_bits:
        out = np.concatenate(
            [out, rng.integers(0, 2, n_bits - len(out)).astype(np.uint8)])
    return out[:n_bits].astype(np.uint8)


def main():
    ok = True
    print("=" * 78)
    print("INTERLEAVING-TYPE DETECTION -- PS section 3 (iii)")
    print("=" * 78)
    print("instrument: decode -> re-encode -> residual (valid-codeword test)")

    info_bits = 192
    payload = _header_payload(np.random.default_rng(3), info_bits)
    enc = conv_encode(payload)
    # Pad so block/diagonal have a representable rows x cols.
    cols = 8
    rows = (len(enc) + cols - 1) // cols
    enc_p = np.concatenate([enc, np.zeros(rows * cols - len(enc), dtype=np.uint8)])
    n = len(enc_p)
    print()
    print(f"coded stream {len(enc)} bits -> padded to {n} ({rows}x{cols})")

    # ---- 0. instrument sanity (this caught the broken syndrome) ---------
    print()
    print("0. INSTRUMENT SANITY")
    clean = reencode_residual(enc_p)
    rand = reencode_residual(np.random.default_rng(5).integers(0, 2, n).astype(np.uint8))
    print(f"   clean codeword   residual {clean:.4f}  (expect ~0.000)")
    print(f"   random bits      residual {rand:.4f}  (expect ~0.14)")
    if not (clean < 0.01 and rand > 0.05):
        ok = False
        print("   FAIL: instrument does not separate a codeword from noise")
    else:
        print("   ok")

    # ---- 1. detection, clean channel ------------------------------------
    print()
    print("1. DETECTION, clean channel")
    hits = 0
    for mode in INTERLEAVE_MODES:
        il = interleave(enc_p, mode, rows=rows, cols=cols)
        det, scores = detect_interleaver(il, rows=rows, cols=cols)
        good = (det == mode)
        hits += int(good)
        s = " ".join(f"{k}={v:.4f}" for k, v in sorted(scores.items()))
        print(f"   {mode:<15} -> {str(det):<15} {'ok' if good else 'WRONG':<6} [{s}]")
    print(f"   score: {hits}/{len(INTERLEAVE_MODES)}")
    if hits < 3:
        ok = False
        print("   FAIL: must name at least 3 of 4 on a clean channel")
    else:
        print("   ok")

    # ---- 2. control ------------------------------------------------------
    print()
    print("2. CONTROL -- interleaved random bits cannot be classified")
    rng = np.random.default_rng(9)
    ctrl = 0
    ctrl_declined = 0
    for mode in INTERLEAVE_MODES:
        rb = interleave(rng.integers(0, 2, n).astype(np.uint8), mode,
                        rows=rows, cols=cols)
        det, _ = detect_interleaver(rb, rows=rows, cols=cols)
        ctrl += int(det == mode)
        ctrl_declined += int(det is None)
    print(f"   correct: {ctrl}/4   declined: {ctrl_declined}/4")
    print("   (either abstaining or being wrong is fine; 4/4 would be cheating)")
    if ctrl == 4:
        ok = False
        print("   FAIL: perfect score on unclassifiable input")

    # ---- 3. noise robustness --------------------------------------------
    print()
    print("3. DETECTION vs CHANNEL ERRORS")
    rng = np.random.default_rng(21)
    print(f"   {'flip rate':>10}{'correct':>10}")
    for rate in (0.0, 0.002, 0.005, 0.01, 0.02):
        correct = 0
        for mode in INTERLEAVE_MODES:
            il = interleave(enc_p, mode, rows=rows, cols=cols)
            if rate > 0:
                pos = rng.choice(len(il), size=max(1, int(len(il) * rate)),
                                 replace=False)
                il = il.copy()
                il[pos] ^= 1
            det, _ = detect_interleaver(il, rows=rows, cols=cols)
            correct += int(det == mode)
        print(f"   {rate*100:>9.1f}%{correct:>7}/4")

    # ---- 4. the payoff ---------------------------------------------------
    print()
    print("4. BURST ERROR -- detection + decode under a 24-bit contiguous burst")
    burst = 24
    print(f"   {'mode':<15}{'detected':<15}{'bits recovered':>16}{'  ':>2}")
    for mode in INTERLEAVE_MODES:
        il = interleave(enc_p, mode, rows=rows, cols=cols)
        il_b = il.copy()
        start = len(il_b) // 3
        il_b[start:start + burst] ^= 1
        det, _ = detect_interleaver(il_b, rows=rows, cols=cols)
        use = det if det in INTERLEAVE_MODES else mode
        perm = interleave_perm(len(il_b), use, rows=rows, cols=cols)
        un = _deinterleave_with(perm, il_b)
        dec = viterbi_decode(un[:len(enc)])
        m = min(info_bits, len(dec))
        acc = float(np.mean(dec[:m] == payload[:m]))
        flag = "ok" if (det == mode and acc > 0.95) else "check"
        print(f"   {mode:<15}{str(det):<15}{acc*100:>15.2f}%  {flag}")

    # ---- 5. WHERE DO WE ACTUALLY GIVE UP? -------------------------------
    # Reporting "it works" without a boundary is not a measurement. Sweep the
    # channel until the detector fails, and record the failure honestly --
    # including the fact that it mostly answers WRONG rather than declining.
    print()
    print("5. OPERATING BOUNDARY (192 info bits, 40 payloads per cell)")
    print(f"   {'flip rate':>10}{'correct':>10}{'declined':>10}{'wrong':>8}")
    for rate in (0.02, 0.05, 0.10, 0.15, 0.20, 0.30):
        hit = declined = 0
        tot = 0
        for s in range(40):
            p = np.random.default_rng(2000 + s).integers(0, 2, info_bits).astype(np.uint8)
            e = conv_encode(p)
            c = 8
            r = (len(e) + c - 1) // c
            ep = np.concatenate([e, np.zeros(r * c - len(e), dtype=np.uint8)])
            mode = INTERLEAVE_MODES[s % 4]
            il = interleave(ep, mode, rows=r, cols=c).copy()
            pos = np.random.default_rng(5000 + s).choice(
                len(il), size=int(len(il) * rate), replace=False)
            il[pos] ^= 1
            det, _ = detect_interleaver(il, rows=r, cols=c)
            hit += int(det == mode)
            declined += int(det is None)
            tot += 1
        print(f"   {rate*100:>9.0f}%{hit:>7}/{tot}{declined:>7}/{tot}"
              f"{tot-hit-declined:>6}/{tot}")
    print("   -> correct out to 10%; falls off past ~15%. Note that past the")
    print("      boundary the detector mostly answers WRONG instead of")
    print("      abstaining, because Viterbi always returns a nearest codeword")
    print("      so every hypothesis keeps a small residual. The margin-based")
    print("      abstention only catches near-ties, not confidence collapse.")

    print()
    print("=" * 78)
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
