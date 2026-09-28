"""Two questions.

Q1. After reverting the 8PSK rule, does the classifier behave as it did before?
    It must abstain on noise and on an unmodulated carrier, and must still name
    BPSK and QPSK. The reverted rule is compared against the measurements that
    got it rejected.

Q2. Can the DEMODULATOR classify better than the spectrum? EVM is a direct
    measurement of how well a constellation explains the received symbols, so
    demodulating under each hypothesis and keeping the lowest EVM is a
    likelihood test rather than a heuristic. If the true modulation reliably
    wins, that is the path to 8PSK/16QAM identification -- and it is measurable,
    so it can be scored rather than asserted.

Calls the real SignalMetadata methods and the real sigma_demod.demodulate().
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, score, FS
from sigma_analyzer_core import SignalMetadata
import sigma_demod as sd


class _Probe:
    PSK_LINE_MARGIN_DB = SignalMetadata.PSK_LINE_MARGIN_DB
    _psk_line_scores = SignalMetadata._psk_line_scores
    _detect_psk_order = SignalMetadata._detect_psk_order


probe = _Probe()
MODS = ("BPSK", "QPSK", "8PSK", "16QAM")
KB = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}

# ---------------------------------------------------------------------------
print("=" * 84)
print("Q1. Reverted classifier - must abstain where it has no evidence")
print("=" * 84)
print(f"{'signal':>10} | {'x^2':>7} {'x^4':>7} | {'order':>6} {'verdict':>12}")
print("-" * 84)

rng = np.random.default_rng(99)
noise = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
         * 0.05).astype(np.complex64)
t = np.arange(20000) / FS
cw = (np.exp(1j * 2 * np.pi * 60_000 * t) * 0.9).astype(np.complex64)

for name, sig in (("noise", noise), ("CW", cw)):
    sc = probe._psk_line_scores(sig, orders=(2, 4))
    order = probe._detect_psk_order(sig)
    verdict = "abstained" if order == 0 else f"CALLED {order}-PSK"
    print(f"{name:>10} | {sc.get(2, float('nan')):>7.1f} "
          f"{sc.get(4, float('nan')):>7.1f} | {order:>6} {verdict:>12}")

for mod, expected in (("BPSK", 2), ("QPSK", 4)):
    sig, sps, idx, const = make_known(mod, 100_000, seed=7)
    sc = probe._psk_line_scores(sig, orders=(2, 4))
    order = probe._detect_psk_order(sig)
    verdict = "correct" if order == expected else "WRONG"
    print(f"{mod:>10} | {sc.get(2, float('nan')):>7.1f} "
          f"{sc.get(4, float('nan')):>7.1f} | {order:>6} {verdict:>12}")

# ---------------------------------------------------------------------------
print()
print("=" * 84)
print("Q2. Demodulator-based classification - does the true constellation win?")
print("=" * 84)
print(f"{'true':>6} {'R_s':>7} | " + " ".join(f"{m:>16}" for m in MODS))
print(f"{'':>6} {'':>7} | " + " ".join(f"{'EVM (lock)':>16}" for _ in MODS))
print("-" * 84)

correct = 0
total = 0
rows = []
for true_mod in MODS:
    for rate in (100_000, 250_000):
        sig, sps, exp_idx, const = make_known(true_mod, rate, seed=7)
        cells = []
        evms = {}
        for hyp in MODS:
            r = sd.demodulate(sig, FS, modulation=hyp, sps=sps)
            if r.locked:
                evms[hyp] = r.evm_percent
                cells.append(f"{r.evm_percent:>7.1f}% (y)")
            else:
                evms[hyp] = float("inf")
                cells.append(f"{'--':>7} (-)")
        winner = min(evms, key=lambda k: evms[k])
        ok = winner == true_mod
        correct += int(ok)
        total += 1
        rows.append((true_mod, rate, winner, ok, dict(evms)))
        print(f"{true_mod:>6} {rate/1e3:>6.0f}k | " + " ".join(f"{c:>16}" for c in cells)
              + f"   -> {winner}{'' if ok else '  WRONG'}")

print("-" * 84)

# The naive "lowest EVM wins" rule ties whenever the true constellation is a
# SUBSET of a larger one -- every BPSK point is a QPSK point, and every QPSK
# point is an 8PSK point -- so a BPSK capture fits QPSK and 8PSK perfectly too.
# Parsimony resolves it: among the constellations that FIT, take the one with
# the fewest points.
FIT_EVM_PERCENT = 10.0
BY_SIZE = ["BPSK", "QPSK", "8PSK", "16QAM"]

print()
print("=" * 84)
print("PARSIMONY RULE - among constellations that fit, fewest points wins")
print("=" * 84)
print(f"  a constellation 'fits' when its EVM is below {FIT_EVM_PERCENT:.0f}%")
print()
print(f"{'true':>6} {'R_s':>7} | {'fitting set':>26} | {'picked':>7} {'result':>8}")
print("-" * 84)

parsimony_correct = 0
for true_mod, rate, winner, ok, evms in rows:
    fitting = [m for m in BY_SIZE if evms.get(m, float("inf")) < FIT_EVM_PERCENT]
    picked = fitting[0] if fitting else None
    good = picked == true_mod
    parsimony_correct += int(good)
    print(f"{true_mod:>6} {rate/1e3:>6.0f}k | "
          f"{(', '.join(fitting) if fitting else 'none'):>26} | "
          f"{str(picked):>7} {'ok' if good else 'WRONG':>8}")

print("-" * 84)
print(f"  lowest-EVM rule        : {correct}/{total}")
print(f"  parsimony rule         : {parsimony_correct}/{total}")
print("=" * 84)
