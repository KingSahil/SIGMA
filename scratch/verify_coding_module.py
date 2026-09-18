"""Score the SHIPPED coding module -- src/sigma_coding.py.

This is the counterpart to ``scratch/fec_ground_truth.py`` (which scores a
scratch implementation). Here the module under test is the one that ships, so
the numbers in the docs describe the actual product code.

The check that matters most is #3: an uncoded bit stream must be REFUSED.
A Viterbi decoder will happily emit confident output for any input, so a coding
analyser that reports "decoded" on uncoded traffic is worse than useless -- it
invents a payload. That refusal is what makes the module safe to run
unconditionally on every capture.

Run:  python scratch/verify_coding_module.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from sigma_coding import (              # noqa: E402
    DEFAULT_K,
    DEFAULT_POLYS,
    DEFAULT_SYNC,
    INTERLEAVE_MODES,
    analyse_coding_layer,
    bits_from_int,
    chance_threshold,
    conv_encode,
    correlate,
    deinterleave,
    detect_interleaver,
    find_headers,
    interleave,
    interleave_perm,
    reencode_residual,
    viterbi_decode,
)


def main():
    ok = True
    print("=" * 78)
    print("CODING MODULE -- src/sigma_coding.py")
    print("=" * 78)
    print(f"code: K={DEFAULT_K}, rate 1/{len(DEFAULT_POLYS)}, "
          f"polys={[bin(p) for p in DEFAULT_POLYS]}")

    rng = np.random.default_rng(7)
    info = rng.integers(0, 2, 400).astype(np.uint8)

    # ---- 1. encode -> decode -------------------------------------------
    print()
    print("1. ENCODE -> DECODE, no channel errors")
    enc = conv_encode(info)
    dec = viterbi_decode(enc)
    m = min(len(info), len(dec))
    acc = float(np.mean(dec[:m] == info[:m]))
    print(f"   info {len(info)} bits, encoded {len(enc)} bits "
          f"(rate {len(info)/len(enc):.2f})")
    print(f"   decoded {len(dec)} bits, accuracy {acc*100:.2f}%")
    if acc < 1.0:
        ok = False
        print("   FAIL: a noiseless channel must decode exactly")
    else:
        print("   ok")

    # ---- 2. error correction, scored by ERROR COUNT ---------------------
    print()
    print("2. DOES IT CORRECT? (scored by error count, not accuracy)")
    print(f"   {'flips':>6}{'uncorrected':>14}{'decoded':>10}{'errors fixed':>14}")
    for n_flip in (1, 5, 10, 20, 40, 80):
        noisy = enc.copy()
        pos = rng.choice(len(noisy), size=n_flip, replace=False)
        noisy[pos] ^= 1
        dec_n = viterbi_decode(noisy)
        mm = min(len(info), len(dec_n))
        acc_n = float(np.mean(dec_n[:mm] == info[:mm]))
        raw_acc = float(np.mean(noisy[:mm * 2] == enc[:mm * 2]))
        err_after = int(np.sum(dec_n[:mm] != info[:mm]))
        print(f"   {n_flip:>6}{raw_acc*100:>13.2f}%{acc_n*100:>9.2f}%"
              f"{n_flip - err_after:>10}/{n_flip}")
        if n_flip <= 10 and acc_n < 1.0:
            ok = False
            print("   FAIL: <=10 flips in 800 bits must be fully corrected")
    print("   (accuracy alone would call 1 flip 'no help': uncorrected is")
    print("    already 99.88%, yet 1/1 errors were removed)")

    # ---- 3. THE REFUSAL CHECK -------------------------------------------
    print()
    print("3. UNCODED INPUT MUST BE REFUSED  <-- the safety property")
    uncoded = rng.integers(0, 2, 400).astype(np.uint8)
    r = analyse_coding_layer(uncoded)
    print(f"   plain random 400 bits -> had_fec={r.had_fec}  "
          f"residual={r.residual:.4f}")
    print(f"   reason: {r.reason}")
    if r.had_fec or r.decoded_bits is not None:
        ok = False
        print("   FAIL: invented a decode for uncoded input")
    else:
        print("   ok -- refuses rather than inventing a payload")

    # also: too-short input
    r_short = analyse_coding_layer(np.array([1, 0, 1, 0], dtype=np.uint8))
    print(f"   4 bits -> analysed={r_short.analysed}  reason: {r_short.reason}")
    if r_short.analysed:
        ok = False
        print("   FAIL: should decline a too-short stream")

    # ---- 4. interleaver detection (the shipped detector) ----------------
    print()
    print("4. INTERLEAVER DETECTION -- shipped detector, blind")
    payload = rng.integers(0, 2, 192).astype(np.uint8)
    e = conv_encode(payload)
    cols = 8
    rows = (len(e) + cols - 1) // cols
    ep = np.concatenate([e, np.zeros(rows * cols - len(e), dtype=np.uint8)])
    hits = 0
    for mode in INTERLEAVE_MODES:
        il = interleave(ep, mode, rows=rows, cols=cols)
        det, scores = detect_interleaver(il, rows=rows, cols=cols)
        good = (det == mode)
        hits += int(good)
        s = " ".join(f"{k}={v:.4f}" for k, v in sorted(scores.items()))
        print(f"   {mode:<15} -> {str(det):<15} {'ok' if good else 'WRONG':<6} [{s}]")
    print(f"   score: {hits}/{len(INTERLEAVE_MODES)}")
    if hits < 4:
        ok = False
        print("   FAIL: the shipped detector must name all four cleanly")

    # ---- 4b. WITHOUT the geometry hint ----------------------------------
    # A real receiver does not know rows/cols. This is the configuration that
    # exposed the single-guess bug (which scored 2/4 here while scoring 4/4
    # above) -- so it has to stay in the suite.
    print()
    print("4b. BLIND, NO geometry hint (the realistic case)")
    blind_hits = 0
    for mode in INTERLEAVE_MODES:
        il = interleave(ep, mode, rows=rows, cols=cols)
        det, _ = detect_interleaver(il)          # no rows/cols
        good = (det == mode)
        blind_hits += int(good)
        print(f"   {mode:<15} -> {str(det):<15} {'ok' if good else 'WRONG'}")
    print(f"   score: {blind_hits}/{len(INTERLEAVE_MODES)}")
    if blind_hits < 4:
        ok = False
        print("   FAIL: geometry search must recover the mode without a hint")
    else:
        print("   ok -- the factorisation search finds it unaided")

    # ---- 4c. geometry sweep ---------------------------------------------
    print()
    print("4c. GEOMETRY SWEEP, blind (24 payloads per cell)")
    print(f"   {'info bits':>10}{'cols':>6}{'correct':>10}")
    sweep_ok = True
    for nb in (48, 96, 192):
        for c in (2, 4, 8, 16):
            hit = 0
            tot = 0
            for s in range(24):
                p = np.random.default_rng(3000 + s).integers(0, 2, nb).astype(np.uint8)
                ee = conv_encode(p)
                r = (len(ee) + c - 1) // c
                epp = np.concatenate([ee, np.zeros(r * c - len(ee), dtype=np.uint8)])
                mode = INTERLEAVE_MODES[s % 4]
                il = interleave(epp, mode, rows=r, cols=c)
                d, _ = detect_interleaver(il)
                hit += int(d == mode)
                tot += 1
            if hit < tot:
                sweep_ok = False
                print(f"   {nb:>10}{c:>6}{hit:>7}/{tot}  <-- not perfect")
    print(f"   overall: {'all cells perfect' if sweep_ok else 'some cells imperfect'}")

    # control: random bits must not be confidently classified
    ctrl = 0
    for mode in INTERLEAVE_MODES:
        rb = interleave(rng.integers(0, 2, len(ep)).astype(np.uint8), mode,
                        rows=rows, cols=cols)
        det, _ = detect_interleaver(rb)
        ctrl += int(det == mode)
    print(f"   control (random bits): {ctrl}/4  "
          f"(4/4 would prove the detector is cheating)")
    if ctrl == 4:
        ok = False
        print("   FAIL: perfect score on unclassifiable input")

    # ---- 5. end to end through analyse_coding_layer ---------------------
    print()
    print("5. END TO END -- coded + interleaved stream in, payload out")
    print(f"   {'mode':<15}{'detected':<15}{'had_fec':>9}{'recovered':>12}")
    for mode in INTERLEAVE_MODES:
        il = interleave(ep, mode, rows=rows, cols=cols)
        r = analyse_coding_layer(il)
        got = "--"
        if r.decoded_bits is not None:
            mm = min(len(payload), len(r.decoded_bits))
            got = f"{np.mean(r.decoded_bits[:mm] == payload[:mm])*100:.2f}%"
        flag = "ok" if (r.had_fec and r.interleaver == mode) else "check"
        print(f"   {mode:<15}{str(r.interleaver):<15}{str(r.had_fec):>9}"
              f"{got:>12}  {flag}")

    # ---- 6. header detection (PS section 3 v) ---------------------------
    print()
    print("6. HEADER DETECTION -- sync-word search with a calibrated gate")
    sync = np.asarray(DEFAULT_SYNC, dtype=np.uint8)
    print(f"   sync word: {len(sync)} bits")

    # 6a. decidable at this length?
    print()
    print("   6a. IS THIS SYNC WORD DECIDABLE HERE?")
    print(f"   {'sync L':>7}{'stream':>10}{'threshold':>22}")
    for L in (16, 32):
        for n in (400, 20000):
            t = chance_threshold(n, L)
            label = "NONE (not decidable)" if t is None else str(t)
            print(f"   {L:>7}{n:>10}{label:>22}")
    print("   -> a 16-bit word is decidable in 400 bits but NOT in 20,000:")
    print("      more data means more chances for a false match.")

    # 6b. detect at a known offset
    print()
    print("   6b. DETECTION AT A KNOWN OFFSET (32-bit sync)")
    hdr_hits = 0
    for off in (0, 37, 200, 913):
        bits_h = rng.integers(0, 2, off + 192).astype(np.uint8)
        bits_h[off:off + len(sync)] = sync
        hits = find_headers(bits_h, sync)
        found = hits[0][0] if hits else None
        good = (found == off)
        hdr_hits += int(good)
        print(f"   true {off:>5} -> found {str(found):>6}  "
              f"{'ok' if good else 'WRONG'}")
    if hdr_hits < 4:
        ok = False
        print("   FAIL: must locate the sync word at every offset")

    # 6c. THE CONTROL
    print()
    print("   6c. CONTROL -- unframed noise must yield NO detection")
    false_pos = 0
    for t in range(25):
        rb = rng.integers(0, 2, 2000).astype(np.uint8)
        if find_headers(rb, sync):
            false_pos += 1
    print(f"   false detections: {false_pos}/25")
    if false_pos:
        ok = False
        print("   FAIL: calibrated detector fired on random input")
    else:
        print("   ok -- the gate holds")

    # 6d. refusal when not decidable
    print()
    print("   6d. REFUSAL -- 16-bit sync in a long stream")
    long_bits = rng.integers(0, 2, 20000).astype(np.uint8)
    long_bits[5000:5016] = bits_from_int(0xD8A1, 16)
    ref = find_headers(long_bits, bits_from_int(0xD8A1, 16))
    print(f"   marker IS at offset 5000 -> {len(ref)} detections (expected 0)")
    if ref:
        ok = False
        print("   FAIL: must decline when the word is not decidable")
    else:
        print("   ok -- declines rather than reporting a chance match")

    # 6e. end to end through analyse_coding_layer
    print()
    print("   6e. THROUGH analyse_coding_layer")
    framed = rng.integers(0, 2, 600).astype(np.uint8)
    framed[123:123 + len(sync)] = sync
    r_h = analyse_coding_layer(framed)
    print(f"   framed stream -> sync_hits={r_h.sync_hits[:1]} "
          f"detectable={r_h.sync_detectable}")
    print(f"   reason: {r_h.reason}")
    if not r_h.sync_hits or r_h.sync_hits[0][0] != 123:
        ok = False
        print("   FAIL: coding layer did not surface the header")
    else:
        print("   ok -- header position surfaced with no FEC present")
    plain = analyse_coding_layer(rng.integers(0, 2, 600).astype(np.uint8))
    print(f"   unframed stream -> sync_hits={plain.sync_hits} "
          f"(expected empty)")
    if plain.sync_hits:
        ok = False
        print("   FAIL: invented a header in unframed input")

    # ---- 7. trellis invariant (zero-cost, catches the traceback trap) ---
    print()
    print("7. TRELLIS INVARIANT")
    _K = DEFAULT_K
    sb = _K - 1
    n_states = 1 << sb
    max_preds = 0
    for ns in range(n_states):
        for b in (0, 1):
            preds = 0
            for s in range(n_states):
                if ((s >> 1) | (b << (sb - 1))) == ns:
                    preds += 1
            max_preds = max(max_preds, preds)
    print(f"   max predecessors for any (state, bit): {max_preds}")
    print("   -> reverse-from-bit is AMBIGUOUS; the traceback MUST store the")
    print("      predecessor state. This assert costs nothing and fires before")
    print("      any signal is involved.")
    if max_preds != 2:
        ok = False
        print(f"   FAIL: expected 2 predecessors for K={_K}")

    print()
    print("=" * 78)
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
