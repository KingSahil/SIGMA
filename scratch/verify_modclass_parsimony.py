"""Verify the parsimony classifier over a real sweep.

Rule under test: demodulate the capture under each supported constellation, keep
the ones whose EVM says the constellation explains the symbols, and among those
take the one with the FEWEST points.

Why parsimony: a lower-order constellation is a geometric SUBSET of a
higher-order one, so a BPSK capture fits BPSK, QPSK and 8PSK equally well. EVM
alone therefore cannot choose; fewest-points resolves the tie in favour of the
simplest explanation that fits. This is the standard ordered-search idea.

The 8/8 first measured was 4 modulations x 2 rates x 1 seed. That is not
evidence, so this sweeps rates, excess bandwidths and seeds, and reports
perfect/total plus every failure.

Also tests the refusal path: noise must not be assigned any constellation.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
import sigma_demod as sd

MODS = ("BPSK", "QPSK", "8PSK", "16QAM")
BY_SIZE = ["BPSK", "QPSK", "8PSK", "16QAM"]
FIT_EVM_PERCENT = 10.0


def classify(sig, sps, fit_evm=FIT_EVM_PERCENT):
    """Return (label, evms). label is None when nothing fits."""
    evms = {}
    for hyp in MODS:
        r = sd.demodulate(sig, FS, modulation=hyp, sps=sps)
        evms[hyp] = r.evm_percent if r.locked else float("inf")
    fitting = [m for m in BY_SIZE if evms[m] < fit_evm]
    return (fitting[0] if fitting else None), evms


RATES = (100_000, 250_000, 50_000, 200_000)
ALPHAS = (0.35, 0.20, 0.50)
SEEDS = (7, 8, 9)

print("=" * 88)
print("PARSIMONY CLASSIFIER - full sweep")
print("=" * 88)
print(f"{'true':>6} {'R_s':>7} {'alpha':>6} {'seed':>5} | {'picked':>7} "
      f"{'EVM of pick':>12} {'runner-up':>22} {'result':>8}")
print("-" * 88)

rows = []
for true_mod in MODS:
    for rate in RATES:
        for alpha in ALPHAS:
            for seed in SEEDS:
                sig, sps, idx, const = make_known(true_mod, rate,
                                                  alpha=alpha, seed=seed)
                picked, evms = classify(sig, sps)
                ok = picked == true_mod
                rows.append((true_mod, rate, alpha, seed, picked, ok, dict(evms)))

                rank = sorted(evms.items(), key=lambda kv: kv[1])
                second = next((k for k in rank if k[0] != picked), None)
                s_val = evms.get(second, float("inf")) if second else float("inf")
                pick_evm = evms.get(picked, float("inf")) if picked else float("inf")
                ru = (f"{second} {s_val:.1f}%" if second and
                      s_val != float("inf") else "none fitted")
                print(f"{true_mod:>6} {rate/1e3:>6.0f}k {alpha:>6.2f} {seed:>5} | "
                      f"{str(picked):>7} {pick_evm:>11.1f}% {ru:>22} "
                      f"{'ok' if ok else 'WRONG':>8}")

print("-" * 88)
correct = sum(1 for r in rows if r[5])
print(f"PARSIMONY CLASSIFIER: {correct}/{len(rows)} correct")

print("\nBY MODULATION")
for m in MODS:
    sub = [r for r in rows if r[0] == m]
    c = sum(1 for r in sub if r[5])
    print(f"  {m:>6}: {c}/{len(sub)}")

fails = [r for r in rows if not r[5]]
if fails:
    print("\nEVERY FAILURE, DISCLOSED:")
    for true_mod, rate, alpha, seed, picked, _, evms in fails:
        print(f"  {true_mod:>6} {rate/1e3:>5.0f}k alpha={alpha:.2f} seed={seed}"
              f"  -> picked {picked}")
        for k in BY_SIZE:
            v = evms[k]
            print(f"        {k:>6}: "
                  f"{'no lock' if v == float('inf') else f'{v:6.2f}%'}")
else:
    print("\nNo failures in this sweep.")

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("REFUSAL PATH - noise must not be assigned a constellation")
print("=" * 88)
n_refused = 0
for seed in (1, 2, 3):
    rng = np.random.default_rng(seed)
    noise = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
             * 0.05).astype(np.complex64)
    picked, evms = classify(noise, 10)
    n_refused += int(picked is None)
    shown = ", ".join(f"{k}={('--' if evms[k] == float('inf') else f'{evms[k]:.1f}%')}"
                      for k in BY_SIZE)
    print(f"  noise seed={seed}: picked {str(picked):>6}   [{shown}]")
print(f"\n  abstained on {n_refused}/3 noise captures "
      f"({'correct' if n_refused == 3 else 'PROBLEM'})")
print("=" * 88)
