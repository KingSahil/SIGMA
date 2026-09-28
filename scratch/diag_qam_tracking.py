"""Why does frequency tracking raise 16QAM EVM while lowering it for PSK?

Hypothesis: the M-th power nonlinearity is exact for PSK but not for square
16QAM. Raising 16QAM to the 4th power does NOT map all 16 points onto one
phase -- the 16 points land in several distinct phase clusters -- so the
"residual frequency" read off its phase slope is a mixture, and the correction
drifts the constellation.

This measures the actual x^M phase clusters per constellation, then reports the
residual the tracker estimates against the residual that is really there.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import constellation, make_known, score, FS, CARRIER_OFFSET
import sigma_demod as sd

print("=" * 78)
print("PART 1 - does x^M collapse the constellation to ONE phase?")
print("=" * 78)
for mod, M in (("BPSK", 2), ("QPSK", 4), ("8PSK", 8), ("16QAM", 4)):
    const = constellation(mod)
    z = const.copy()
    for _ in range(M - 1):
        z = z * const
    # Cluster the resulting phases: how many distinct groups are there?
    ph = np.sort(np.degrees(np.angle(z)) % 360.0)
    # count clusters separated by more than 1 degree
    gaps = np.diff(ph)
    n_clusters = 1 + int(np.sum(gaps > 1.0))
    spread = float(np.max(ph) - np.min(ph))
    print(f"  {mod:>6}  x^{M}:  {n_clusters} distinct phase cluster(s), "
          f"spread {spread:7.2f} deg")
    if n_clusters > 1:
        uniq = []
        for p in ph:
            if not uniq or abs(p - uniq[-1]) > 1.0:
                uniq.append(p)
        print(f"          cluster centres: "
              f"{', '.join(f'{u:.1f}' for u in uniq)} deg")
        print(f"          -> x^{M} does NOT collapse this constellation to a "
              f"single tone")

print()
print("=" * 78)
print("PART 2 - what residual does the tracker estimate vs what is really there?")
print("=" * 78)
print(f"{'mod':>6} {'R_s':>7} | {'carr err':>9} {'true resid':>11} "
      f"{'EVM':>7} {'acc':>9} {'tracked':>9}")
print("-" * 78)

# Monkeypatch to capture the residual the tracker computed, and to also learn
# the true residual: carrier_offset_hz is the estimate, true is CARRIER_OFFSET.
captured = {}
_real_demod = sd.demodulate


def demod_capture(x, samp_rate, modulation="BPSK", sps=None, alpha=0.35):
    r = _real_demod(x, samp_rate, modulation=modulation, sps=sps, alpha=alpha)
    captured[modulation] = getattr(r, "residual_freq_hz", None)
    return r


sd.demodulate = demod_capture

for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    k_bits = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}[mod]
    for rate in (250_000, 100_000):
        sig, sps, exp_idx, const = make_known(mod, rate, alpha=0.35, seed=7)
        res = sd.demodulate(sig, FS, modulation=mod, sps=sps)
        if not res.locked:
            print(f"{mod:>6} {rate/1e3:>6.0f}k | NO LOCK")
            continue
        acc, _, _ = score(res.symbols, const, exp_idx, k_bits)
        cerr = res.carrier_offset_hz - CARRIER_OFFSET
        true_resid = -cerr   # what remains after correcting by `offset`
        print(f"{mod:>6} {rate/1e3:>6.0f}k | {cerr:>+8.1f} {true_resid:>+10.1f} "
              f"{res.evm_percent:>6.1f}% {acc*100:>8.2f}% "
              f"{captured.get(mod, float('nan')):>+8.1f}")

sd.demodulate = _real_demod

print("-" * 78)
print("If 'tracked' is close to 'true resid', the tracker is measuring the")
print("right thing. If it is far off, the nonlinearity is misreporting it.")
print("=" * 78)
