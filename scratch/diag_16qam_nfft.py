"""16QAM at 250 ksps regressed when the Welch segment length shrank.

Welch averaging wants several segments, which forces a smaller nfft; but 16QAM's
x^4 spectrum is not a single line (its 16 points land in three phase clusters),
so a coarser bin localises it worse. This measures the trade directly.

Arms:
  A  current behaviour
  B  refinement forced ON for 16QAM as well
  C  the previous fixed nfft floor of 4096
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, score, FS, CARRIER_OFFSET
import sigma_demod as sd

KB = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}

_real_estimate = sd.estimate_carrier_offset


def run(mod, rate, alpha, seed, force_refine=None):
    sig, sps, exp_idx, const = make_known(mod, rate, alpha=alpha, seed=seed)
    power = sd.SYMMETRY_ORDER[mod]

    if force_refine is None:
        est = _real_estimate(sig, FS, power=power, refine=True)
    else:
        est = _real_estimate(sig, FS, power=power, refine=force_refine)

    r = sd.demodulate(sig, FS, modulation=mod, sps=sps)
    if not r.locked:
        return est, None, None, None
    acc, _, _ = score(r.symbols, const, exp_idx, KB[mod])
    return est, r.evm_percent, acc * 100, r.residual_freq_hz


print("=" * 92)
print("CARRIER ESTIMATE QUALITY - does the refinement help 16QAM at a coarse bin?")
print("=" * 92)
print(f"{'mod':>6} {'R_s':>7} {'alpha':>6} {'seed':>5} | {'refine':>7} "
      f"{'est err':>9} {'EVM':>7} {'acc':>8} {'residual':>9}")
print("-" * 92)

for mod in ("16QAM", "8PSK"):
    for rate in (250_000, 100_000):
        for seed in (7, 8):
            for refine in (True, False):
                est, evm, acc, resid = run(mod, rate, 0.35, seed, force_refine=refine)
                err = est - CARRIER_OFFSET
                evm_s = f"{evm:.1f}%" if evm is not None else "--"
                acc_s = f"{acc:.2f}%" if acc is not None else "NO LOCK"
                res_s = f"{resid:+.1f}" if resid is not None else "--"
                print(f"{mod:>6} {rate/1e3:>6.0f}k {0.35:>6.2f} {seed:>5} | "
                      f"{str(refine):>7} {err:>+8.1f} {evm_s:>7} {acc_s:>8} {res_s:>9}")
        print()

print("-" * 92)

# How many segments does each record actually yield at the adaptive length?
print()
print("=" * 92)
print("SEGMENTS AVAILABLE vs RECORD LENGTH (adaptive nfft = largest pow2 <= n//2)")
print("=" * 92)
print(f"{'n':>8} {'nfft':>7} {'bin (Hz)':>10} {'step':>7} {'segments':>9}")
print("-" * 92)
for n in (3000, 6000, 10000, 15000, 30000, 60000):
    max_nfft = max(256, n // 2)
    nfft = 1 << int(np.floor(np.log2(max(256, min(max_nfft, 65536)))))
    if nfft > n:
        nfft = 1 << int(np.floor(np.log2(max(n, 2))))
    step = max(1, nfft // 2)
    segs = len(range(0, n - nfft + 1, step))
    print(f"{n:>8} {nfft:>7} {FS/nfft:>10.1f} {step:>7} {segs:>9}")
print("=" * 92)
