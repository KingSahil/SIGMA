"""Does the sub-bin refinement actually help, or does it only help some modulations?

The full sweep after adding the refinement showed BPSK and 8PSK improving a lot
(BPSK's SPS=4 refusals gone, 8PSK's 71% low-alpha case gone) while 16QAM got
slightly WORSE (mean 99.98% -> 99.33%, min 99.97% -> 93.80%). A more accurate
frequency estimate making a demodulator worse is counter-intuitive, so this
measures refine=True against refine=False through the REAL demodulate(), for
every modulation and excess bandwidth, instead of assuming the refinement helps.

Both arms go through sigma_demod.demodulate(). Only the estimator's `refine`
flag differs, so any difference is attributable to the refinement.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, score, FS, CARRIER_OFFSET
import sigma_demod as sd

_real_estimate = sd.estimate_carrier_offset


def _no_refine(x, samp_rate, power=4, refine=True):
    return _real_estimate(x, samp_rate, power=power, refine=False)


def run(refine):
    """Run every case with the estimator forced to the given refinement mode."""
    if refine:
        sd.estimate_carrier_offset = _real_estimate
    else:
        sd.estimate_carrier_offset = _no_refine

    out = []
    for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
        k_bits = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}[mod]
        for rate in (250_000, 100_000):
            for alpha in (0.50, 0.35, 0.20):
                sig, sps, exp_idx, const = make_known(
                    mod, rate, alpha=alpha, seed=7)
                res = sd.demodulate(sig, FS, modulation=mod, sps=sps)
                if not res.locked:
                    out.append((mod, rate, alpha, None, None, res.evm_percent,
                                "NO LOCK"))
                    continue
                acc, _, _ = score(res.symbols, const, exp_idx, k_bits)
                cerr = res.carrier_offset_hz - CARRIER_OFFSET
                out.append((mod, rate, alpha, acc, cerr, res.evm_percent, ""))

    sd.estimate_carrier_offset = _real_estimate
    return out


on = run(True)
off = run(False)

print("=" * 96)
print("EFFECT OF SUB-BIN REFINEMENT  (both arms through the real demodulate())")
print("=" * 96)
print(f"{'mod':>6} {'R_s':>7} {'alpha':>6} | {'carr err OFF':>13} {'EVM OFF':>8} "
      f"{'acc OFF':>9} | {'carr err ON':>12} {'EVM ON':>8} {'acc ON':>9} | {'delta':>8}")
print("-" * 96)

for a, b in zip(off, on):
    mod, rate, alpha = a[0], a[1], a[2]

    def fmt(row):
        _, _, _, acc, cerr, evm, note = row
        if note:
            return f"{'--':>13} {'--':>8} {'NO LOCK':>9}"
        return (f"{cerr:>+12.0f}  {evm:>7.1f}% {acc*100:>8.2f}%")

    d = ""
    if a[3] is not None and b[3] is not None:
        delta = (b[3] - a[3]) * 100
        d = f"{delta:>+7.2f}pt"
    elif a[3] is None and b[3] is not None:
        d = "  FIXED"
    elif a[3] is not None and b[3] is None:
        d = "  BROKE"

    print(f"{mod:>6} {rate/1e3:>6.0f}k {alpha:>6.2f} | {fmt(a)} | {fmt(b)} | {d}")

print("-" * 96)

# Per-modulation verdict, stated rather than implied
print("\nVERDICT PER MODULATION")
for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    a_mod = [r for r in off if r[0] == mod]
    b_mod = [r for r in on if r[0] == mod]
    a_ok = [r[3] for r in a_mod if r[3] is not None]
    b_ok = [r[3] for r in b_mod if r[3] is not None]
    a_mean = np.mean(a_ok) * 100 if a_ok else 0.0
    b_mean = np.mean(b_ok) * 100 if b_ok else 0.0
    a_min = np.min(a_ok) * 100 if a_ok else 0.0
    b_min = np.min(b_ok) * 100 if b_ok else 0.0
    a_locks = len(a_ok)
    b_locks = len(b_ok)
    if b_mean > a_mean + 0.001 or b_locks > a_locks:
        tag = "refinement HELPS"
    elif b_mean < a_mean - 0.001 or b_locks < a_locks:
        tag = "refinement HURTS"
    else:
        tag = "no measurable difference"
    print(f"  {mod:>6}: {tag:18s}  locks {a_locks}->{b_locks}   "
          f"mean {a_mean:6.2f}% -> {b_mean:6.2f}%   "
          f"min {a_min:6.2f}% -> {b_min:6.2f}%")
print("=" * 96)
