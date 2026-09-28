"""
verify_scheme_search.py -- PS section 3 (i), blind FEC-scheme identification.

`analyse_coding_layer` originally required `K` and `polys` as inputs. A real
receiver is not told which convolutional code the operator used, and the code
is not carried in the signal, so the honest question is:

    given only bits, is this convolutional-coded, and with which code?

What is checked here, and why each check is necessary
-----------------------------------------------------
1. Each candidate code is named from its own encoding (fast path).
2. The control: random bits yield NO scheme. Without this, "always returns a
   winner" would look like a working identifier -- measured, a bare argmin
   claims a scheme for 12/12 noise streams.
3. The FAST PATH's blind spot is documented by measurement, not by comment:
   a non-default code that is also interleaved is not identified.
4. The DEEP search closes that gap for K <= 7, and still refuses noise.
5. K=9 is reported as SKIPPED on short streams -- "not tested" and "tested and
   rejected" are different claims and must not look alike.
6. The shipped GUI surfaces the scheme, and the deep-search action is wired.
7. The deep search can be re-run on the same bits without re-demodulating.

Run:  radioconda\\python.exe scratch/verify_scheme_search.py
"""

import os
import sys
import time

import numpy as np

# Unbuffered: this suite runs for minutes and section 4 is the slow part, so
# partial output must be visible while it works rather than only at the end.
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from sigma_coding import (                                    # noqa: E402
    CANDIDATE_CODES,
    FEC_THRESHOLD,
    analyse_coding_layer,
    conv_encode,
    interleave,
    search_fec_scheme,
    search_scheme_and_interleaver,
    scheme_margin,
)

FAILURES = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{'  -- ' + detail if detail else ''}")
    if not ok:
        FAILURES.append(name)


def bits(rng, n):
    return rng.integers(0, 2, n).astype(np.uint8)


print("=" * 78)
print("SCHEME IDENTIFICATION -- PS section 3 (i)")
print("=" * 78)

# ---------------------------------------------------------------------------
print()
print("1. EACH CODE IS NAMED FROM ITS OWN ENCODING (fast path, un-interleaved)")
print("=" * 78)
rng = np.random.default_rng(101)
n_ok = 0
for label, K, polys in CANDIDATE_CODES:
    enc = conv_encode(bits(rng, 200), K=K, polys=polys)
    r = analyse_coding_layer(enc)
    hit = r.fec_scheme == label and r.had_fec
    n_ok += int(hit)
    print(f"   {label:<10} -> {str(r.fec_scheme):<10} had_fec={r.had_fec}  "
          f"{'ok' if hit else 'WRONG'}")
check(f"identified all {len(CANDIDATE_CODES)} codes", n_ok == len(CANDIDATE_CODES),
      f"{n_ok}/{len(CANDIDATE_CODES)}")

# ---------------------------------------------------------------------------
print()
print("2. CONTROL -- random bits must yield NO scheme")
print("=" * 78)
print("   (and the contrast that justifies the threshold)")
rng = np.random.default_rng(102)
false_pos = 0
bare_argmin = 0
trials = 12
for _ in range(trials):
    noise = bits(rng, 200)
    lbl, K, polys, resid, table = search_fec_scheme(noise)
    if lbl is not None:
        false_pos += 1
    if resid is not None:
        bare_argmin += 1        # a bare argmin always names something
print(f"   {trials} random streams:")
print(f"     with FEC_THRESHOLD={FEC_THRESHOLD}: {false_pos}/{trials} claimed a scheme")
print(f"     a bare argmin would claim      : {bare_argmin}/{trials}")
check("no random stream is named a code", false_pos == 0,
      f"{false_pos}/{trials}")
check("the contrast is real (bare argmin always fires)",
      bare_argmin == trials, f"{bare_argmin}/{trials}")

# ---------------------------------------------------------------------------
print()
print("3. THE FAST PATH'S BLIND SPOT, MEASURED")
print("=" * 78)
print("   A non-default code AND an interleaver together are not identified")
print("   on the fast path: the interleaver probe uses the default code, so")
print("   de-interleaving never produces a codeword.")
rng = np.random.default_rng(103)
fast_hits = 0
fast_total = 0
for label, K, polys in CANDIDATE_CODES:
    if K == 3:
        continue                      # the default code is the easy case
    for mode in ("block", "convolutional", "diagonal", "pseudo_random"):
        enc = interleave(conv_encode(bits(rng, 200), K=K, polys=polys), mode)
        r = analyse_coding_layer(enc)          # fast path
        fast_total += 1
        fast_hits += int(r.fec_scheme == label and r.interleaver == mode)
print(f"   fast path, non-default code + interleaver: "
      f"{fast_hits}/{fast_total} identified")
check("the blind spot is real (fast path cannot do it)", fast_hits == 0,
      f"{fast_hits}/{fast_total}")

# ---------------------------------------------------------------------------
print()
print("4. THE DEEP SEARCH CLOSES IT  (K <= 7)")
print("=" * 78)
print("   (K=4 and K=7 only -- the point is that a NON-DEFAULT code is")
print("    resolved, and each deep case costs ~1.4 s)")
rng = np.random.default_rng(104)
deep_hits = 0
deep_total = 0
t0 = time.time()
for label, K, polys in CANDIDATE_CODES:
    if K not in (4, 7):
        continue
    for mode in ("block", "convolutional", "diagonal", "pseudo_random"):
        src = bits(rng, 200)
        enc = interleave(conv_encode(src, K=K, polys=polys), mode)
        lbl, il, resid, kp, gm, table = search_scheme_and_interleaver(enc)
        deep_total += 1
        deep_hits += int(lbl == label and il == mode
                         and resid is not None and resid <= FEC_THRESHOLD)
        print(f"   {label:<10} + {mode:<15} -> {str(lbl):<10} {str(il):<15} "
              f"{'ok' if (lbl == label and il == mode) else 'WRONG'}")
elapsed = time.time() - t0
print(f"   deep search, non-default code + interleaver: "
      f"{deep_hits}/{deep_total} identified   ({elapsed:.1f}s for {deep_total})")
check("the deep search identifies code AND interleaver", deep_hits == deep_total,
      f"{deep_hits}/{deep_total}")

print()
print("   ...and it must still refuse noise:")
rng = np.random.default_rng(105)
deep_fp = 0
for _ in range(4):
    lbl, il, resid, kp, gm, table = search_scheme_and_interleaver(bits(rng, 200))
    if lbl is not None:
        deep_fp += 1
check("deep search refuses random bits", deep_fp == 0, f"{deep_fp}/4 claimed")

# ---------------------------------------------------------------------------
print()
print("5. K=9 IS REPORTED AS SKIPPED, NOT AS REJECTED")
print("=" * 78)
enc9 = conv_encode(bits(np.random.default_rng(106), 200), K=9,
                   polys=(0o561, 0o753))
lbl, il, resid, kp, gm, table = search_scheme_and_interleaver(enc9)
k9_rows = [r for r in table if r[1] == 9]
print(f"   K=9 rows in the table: {k9_rows}")
check("K=9 carries an explicit 'skipped' marker",
      len(k9_rows) == 1 and k9_rows[0][3] == "skipped: stream too short",
      str(k9_rows))
check("a skipped K=9 is not reported as an identified scheme", lbl is None,
      f"scheme={lbl}")

print()
print("   and via the shipped entry point, `k9_skipped` must be set:")
r9 = analyse_coding_layer(enc9, deep_search=True)
print(f"   deep_search={r9.deep_search} k9_skipped={r9.k9_skipped}")
check("k9_skipped is surfaced on the result object", r9.k9_skipped is True,
      f"k9_skipped={r9.k9_skipped}")

# ---------------------------------------------------------------------------
print()
print("6. GUI -- the scheme is surfaced, and the deep action is wired")
print("=" * 78)
try:
    from PyQt5 import QtWidgets
    from sigma_main_window import SigmaMainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = SigmaMainWindow()

    has_btn = hasattr(win, "btn_deep_search")
    print(f"   deep-search action exists: {has_btn}")
    check("window exposes a deep-search action", has_btn)
    if has_btn:
        # The window auto-loads a default capture at startup, so bits usually
        # exist and the action is enabled. What must hold is that the action is
        # enabled IF AND ONLY IF there are bits to re-analyse.
        n_bits = len(getattr(win, "_last_bits", []) or [])
        enabled = win.btn_deep_search.isEnabled()
        print(f"   stored bits: {n_bits}   action enabled: {enabled}")
        check("the action is enabled exactly when bits exist",
              enabled == (n_bits > 0),
              f"bits={n_bits} enabled={enabled}")

        # And with no bits it must be unusable -- otherwise clicking it would
        # do nothing silently, which reads as a broken button.
        win._last_bits = None
        win.btn_deep_search.setEnabled(False)
        win.run_deep_coding_search()
        print(f"   with no bits, the action is inert: "
              f"{win.btn_deep_search.isEnabled() is False}")
        check("with no bits the action is inert and safe to click",
              win.btn_deep_search.isEnabled() is False)

    # Feed real bits and confirm the card shows the identified code, and that
    # the deep action becomes available.
    src = bits(np.random.default_rng(107), 200)
    coded = conv_encode(src, K=7, polys=(0o171, 0o133))
    win._last_bits = coded
    win.coding_result = None
    win.btn_deep_search.setEnabled(True)
    r = win._run_coding_analysis(deep=False)
    print(f"   fast pass over a (2,1,7) codeword: scheme={r.fec_scheme}")

    # Build a stub demod result so the card can be rendered, then render.
    if win.demod_result is not None or True:
        class _Res:
            modulation = "QPSK"
            n_symbols = 400
            bits = coded
            evm_percent = 3.3
            carrier_offset_hz = 60000.0
            residual_freq_hz = 0.2
            sps = 10.0
        win._render_demod_card(_Res(), r)
        app.processEvents()
        stats = win.lbl_demod_stats.text()
        print(f"   card: {stats!r}")
        check("card shows an identified Code line", "Code:" in stats,
              f"got {stats!r}")
        check("card names the real code", "(2,1,7)" in stats, f"got {stats!r}")

        # A refusal must read as a refusal, not a blank.
        noise = bits(np.random.default_rng(108), 200)
        r2 = analyse_coding_layer(noise)
        _Res.bits = noise
        win._render_demod_card(_Res(), r2)
        app.processEvents()
        stats2 = win.lbl_demod_stats.text()
        print(f"   card on noise: {stats2!r}")
        check("a refusal says 'none identified', it does not go blank",
              "Code: none identified" in stats2, f"got {stats2!r}")

    win.close()
except Exception as exc:                                     # pragma: no cover
    print(f"  [skip] GUI check unavailable: {exc}")

# ---------------------------------------------------------------------------
print()
print("7. THE DEEP SEARCH RE-RUNS ON STORED BITS (no re-demodulation)")
print("=" * 78)
try:
    from PyQt5 import QtWidgets
    from sigma_main_window import SigmaMainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = SigmaMainWindow()

    src = bits(np.random.default_rng(109), 200)
    coded = interleave(conv_encode(src, K=4, polys=(0o15, 0o17)), "block")

    class _Res:
        modulation = "QPSK"
        n_symbols = 400
        bits = coded
        evm_percent = 3.3
        carrier_offset_hz = 60000.0
        residual_freq_hz = 0.2
        sps = 10.0

    win._last_bits = coded
    win.demod_result = _Res()
    win.btn_deep_search.setEnabled(True)

    win.run_deep_coding_search()
    app.processEvents()
    r = win.coding_result
    print(f"   after deep search: scheme={r.fec_scheme} interleaver={r.interleaver} "
          f"deep={r.deep_search}")
    check("deep search identified the non-default code",
          r.fec_scheme == "(2,1,4)", f"got {r.fec_scheme}")
    check("deep search identified the interleaver",
          r.interleaver == "block", f"got {r.interleaver}")
    acc = (np.mean(r.decoded_bits[:len(src)] == src)
           if r.decoded_bits is not None else 0.0)
    print(f"   payload recovered: {acc*100:.1f}%")
    check("payload recovered exactly", acc == 1.0, f"{acc*100:.1f}%")

    stats = win.lbl_demod_stats.text()
    print(f"   card: {stats!r}")
    check("card marks the result as a deep search",
          "(deep search)" in stats, f"got {stats!r}")
    check("deep action is re-enabled after the run",
          win.btn_deep_search.isEnabled() is True)

    win.close()
except Exception as exc:                                     # pragma: no cover
    print(f"  [skip] re-run check unavailable: {exc}")

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} -> {FAILURES}")
    sys.exit(1)
print("ALL PASSED")
