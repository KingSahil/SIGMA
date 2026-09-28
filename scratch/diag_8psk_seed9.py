"""Why does 8PSK jump from ~3.5% EVM to ~20% on seed 9?

Seeds 7 and 8 give EVM 3.2-4.6% and 100% bit accuracy across every rate and
excess bandwidth. Seed 9 gives ~20%. Either the demodulation genuinely degrades
(and the classifier is right to abstain) or the bits are still correct and only
the reported EVM is pessimistic (and the fit threshold is too strict).

Reports bit accuracy alongside EVM, because those are the two things that
distinguish those cases, plus the carrier/residual/phase values so a wrong
estimate is visible rather than inferred.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, score, FS, CARRIER_OFFSET
import sigma_demod as sd

CASES = [
    ("8PSK", 100_000, 0.20, 7),
    ("8PSK", 100_000, 0.20, 8),
    ("8PSK", 100_000, 0.20, 9),
    ("8PSK", 250_000, 0.35, 8),
    ("8PSK", 250_000, 0.35, 9),
    ("8PSK", 200_000, 0.20, 9),
    ("8PSK", 100_000, 0.35, 9),
    ("8PSK", 250_000, 0.20, 9),
]

print("=" * 96)
print("8PSK seed sweep - EVM vs BIT ACCURACY")
print("=" * 96)
print(f"{'R_s':>7} {'alpha':>6} {'seed':>5} | {'EVM':>7} {'acc':>9} {'bits':>6} "
      f"| {'carr err':>9} {'residual':>9} {'phase':>8} {'n_sym':>6}")
print("-" * 96)

for mod, rate, alpha, seed in CASES:
    sig, sps, exp_idx, const = make_known(mod, rate, alpha=alpha, seed=seed)
    r = sd.demodulate(sig, FS, modulation=mod, sps=sps)

    if not r.locked:
        print(f"{rate/1e3:>6.0f}k {alpha:>6.2f} {seed:>5} | NO LOCK: {r.reason[:40]}")
        continue

    acc, _, _ = score(r.symbols, const, exp_idx, 3)
    cerr = r.carrier_offset_hz - CARRIER_OFFSET
    print(f"{rate/1e3:>6.0f}k {alpha:>6.2f} {seed:>5} | {r.evm_percent:>6.1f}% "
          f"{acc*100:>8.2f}% {len(r.bits):>6} | {cerr:>+8.1f} "
          f"{r.residual_freq_hz:>+8.1f} {r.phase_correction_deg:>+7.1f}d "
          f"{r.n_symbols:>6}")

print("-" * 96)
print("If acc stays 100% while EVM is ~20%, the demodulation is CORRECT and the")
print("10% fit threshold is simply too strict for 8PSK. If acc drops, the")
print("demodulation genuinely failed and abstaining was right.")
print("=" * 96)

# How much does the EVM vary with seed at all? Is seed 9 an outlier or the norm?
print()
print("=" * 96)
print("EVM distribution over 12 seeds (is seed 9 special?)")
print("=" * 96)
for rate in (100_000, 250_000):
    evms, accs = [], []
    for seed in range(1, 13):
        sig, sps, exp_idx, const = make_known("8PSK", rate, alpha=0.35, seed=seed)
        r = sd.demodulate(sig, FS, modulation="8PSK", sps=sps)
        if not r.locked:
            evms.append(float("nan")); accs.append(0.0)
            continue
        a, _, _ = score(r.symbols, const, exp_idx, 3)
        evms.append(r.evm_percent); accs.append(a * 100)
    e = np.array(evms)
    print(f"  R_s={rate/1e3:.0f}k  EVM min {np.nanmin(e):.1f}%  "
          f"median {np.nanmedian(e):.1f}%  max {np.nanmax(e):.1f}%   "
          f"min acc {np.min(accs):.2f}%")
    print(f"          per-seed EVM: "
          f"{', '.join(f'{v:.1f}' for v in e)}")
    print(f"          per-seed acc: "
          f"{', '.join(f'{v:.0f}' for v in accs)}")
print("=" * 96)
