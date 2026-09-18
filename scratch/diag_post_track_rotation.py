"""After frequency tracking, is the remaining EVM just a stale constant rotation?

The rotation search runs BEFORE the frequency correction. Removing a linear
phase ramp shifts the best constant rotation, so the rotation chosen earlier can
be stale. If that is the whole story, a small rotation applied to res.symbols
should collapse the distance to the constellation.

This measures the rms distance to the nearest constellation point as a function
of applied rotation, on the REAL res.symbols returned by demodulate().
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import constellation, make_known, score, FS
import sigma_demod as sd


def rms_dist(symbols, const):
    d = np.abs(symbols[:, None] - const[None, :])
    return float(np.sqrt(np.mean(np.min(d, axis=1) ** 2)))


print("=" * 82)
print("Is the post-tracking EVM removable by a constant rotation?")
print("=" * 82)
print(f"{'mod':>6} {'R_s':>7} | {'EVM as returned':>16} {'best EVM over rot':>18} "
      f"{'best rot':>9} {'improvement':>12}")
print("-" * 82)

for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    k_bits = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}[mod]
    for rate in (250_000, 100_000):
        sig, sps, exp_idx, const = make_known(mod, rate, alpha=0.35, seed=7)
        res = sd.demodulate(sig, FS, modulation=mod, sps=sps)
        if not res.locked:
            print(f"{mod:>6} {rate/1e3:>6.0f}k | NO LOCK")
            continue

        rms_ref = np.sqrt(np.mean(np.abs(const) ** 2))
        evm_as_is = res.evm_percent

        best_evm, best_rot = evm_as_is, 0.0
        for rot_deg in np.arange(-30.0, 30.01, 1.0):
            test = res.symbols * np.exp(1j * np.radians(rot_deg))
            e = rms_dist(test, const) / rms_ref * 100.0
            if e < best_evm:
                best_evm, best_rot = e, rot_deg

        acc, _, _ = score(res.symbols, const, exp_idx, k_bits)
        print(f"{mod:>6} {rate/1e3:>6.0f}k | {evm_as_is:>15.1f}% "
              f"{best_evm:>17.1f}% {best_rot:>+8.1f}d "
              f"{evm_as_is - best_evm:>+11.1f}pt   (acc {acc*100:.2f}%)")

print("-" * 82)
print("A large improvement means the rotation chosen before tracking is stale,")
print("and the rotation search must be re-run after the frequency correction.")
print("=" * 82)
