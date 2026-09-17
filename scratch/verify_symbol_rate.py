"""Verify the symbol rate estimator against known ground truth.

Generates signals with known symbol rates, runs the estimator, reports the
actual measurement error. This is the only way to know if it works.
"""
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sigma_symbol_rate import estimate_symbol_rate, format_symbol_rate, format_sps

sys.path.insert(0, os.path.dirname(__file__))
from make_ground_truth import make_signal

FS = 1_000_000

CASES = [
    (100_000, "bpsk", 0.35),
    (50_000, "qpsk", 0.35),
    (200_000, "bpsk", 0.35),
    (25_000, "qpsk", 0.35),
    (125_000, "bpsk", 0.35),
    (250_000, "qpsk", 0.35),
    (100_000, "bpsk", 0.20),
    (100_000, "bpsk", 0.50),
    (100_000, "qpsk", 0.15),
    (500_000, "bpsk", 0.35),
]

print("=" * 78)
print("SYMBOL RATE ESTIMATOR - VERIFICATION AGAINST GROUND TRUTH")
print("=" * 78)
print(f"{'true R_s':>10} {'mod':>6} {'alpha':>6} | {'measured':>11} "
      f"{'error':>8} {'SPS':>7} {'prom dB':>8} {'conf':>6}")
print("-" * 78)

errors = []
for true_rate, mod, alpha in CASES:
    sig, sps = make_signal(true_rate, mod, alpha=alpha, n_symbols=4000)
    res = estimate_symbol_rate(sig, FS)

    if res["locked"]:
        meas = res["symbol_rate_hz"]
        err_pct = (meas - true_rate) / true_rate * 100.0
        errors.append(abs(err_pct))
        print(f"{true_rate/1e3:>9.1f}k {mod:>6} {alpha:>6.2f} | "
              f"{format_symbol_rate(res):>11} {err_pct:>+7.2f}% "
              f"{format_sps(res):>7} {res['prominence_db']:>7.1f} "
              f"{res['confidence_label']:>6}")
    else:
        errors.append(None)
        print(f"{true_rate/1e3:>9.1f}k {mod:>6} {alpha:>6.2f} | "
              f"{'NO LOCK':>11} {'--':>8} {'--':>7} "
              f"{res['prominence_db']:>7.1f} {'NONE':>6}")

print("-" * 78)
good = [e for e in errors if e is not None]
if good:
    print(f"locked: {len(good)}/{len(errors)}   "
          f"mean |error|: {np.mean(good):.2f}%   "
          f"max |error|: {np.max(good):.2f}%")
else:
    print("NOTHING LOCKED - estimator is not working")
print("=" * 78)

# Now check behaviour on the real project files, where we have no ground truth
print("\n" + "=" * 78)
print("REAL PROJECT FILES (no ground truth available)")
print("=" * 78)
D = os.path.join(os.path.dirname(__file__), "..", "data", "iq")
for name in ["signal.iq", "bpsk_modulated_1msps.iq", "qpsk_modulated_1msps.iq"]:
    p = os.path.join(D, name)
    if not os.path.exists(p):
        continue
    x = np.fromfile(p, dtype=np.complex64)
    res = estimate_symbol_rate(x, FS)
    status = (f"{format_symbol_rate(res):>11}  SPS={format_sps(res):>7}  "
              f"{res['confidence_label']}"
              if res["locked"] else "NO LOCK")
    print(f"  {name:<32} {status}")
