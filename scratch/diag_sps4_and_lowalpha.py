"""Run down the two failures the full sweep exposed.

Q1. BPSK at SPS=4 refuses with EVM 61.9%. Did my exponent change (4 -> 2 for
    BPSK) cause that, or is it pre-existing? Answered by monkeypatching the
    estimator back to the old hardcoded power=4 and re-running the same case
    through the REAL demodulate().

Q2. Where exactly does BPSK break as SPS falls? Sweep SPS at fixed rate.

Q3. 8PSK at alpha=0.20 scores 71%. Is the carrier estimate wrong, or is the
    eye closed by ISI? Report the carrier error and EVM together.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import sigma_demod as sd
from sigma_demod import demodulate, rrc_filter, SYMMETRY_ORDER

FS = 1_000_000
TRUE_OFFSET = 60_000.0


def constellation(mod):
    if mod == "BPSK":
        return np.array([1 + 0j, -1 + 0j])
    if mod == "QPSK":
        return np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
    if mod == "8PSK":
        return np.exp(1j * 2 * np.pi * np.arange(8) / 8)
    if mod == "16QAM":
        lv = np.array([-3, -1, 1, 3], dtype=np.float64) / np.sqrt(10)
        return np.array([i + 1j * q for i in lv for q in lv])
    raise ValueError(mod)


def make_known(mod, symbol_rate, alpha=0.35, n_symbols=1500, seed=7, noise=0.02):
    rng = np.random.default_rng(seed)
    sps = int(round(FS / symbol_rate))
    const = constellation(mod)
    idx = rng.integers(0, len(const), n_symbols)
    up = np.zeros(n_symbols * sps, dtype=np.complex128)
    up[::sps] = const[idx]
    shaped = np.convolve(up, rrc_filter(sps, alpha), mode="same")
    t = np.arange(len(shaped)) / FS
    shaped = shaped * np.exp(1j * 2 * np.pi * TRUE_OFFSET * t)
    shaped += (rng.normal(0, noise, len(shaped))
               + 1j * rng.normal(0, noise, len(shaped)))
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64), sps, idx, const


print("=" * 78)
print("Q1. BPSK at SPS=4 -- is the refusal caused by my exponent change?")
print("=" * 78)
sig, sps, idx, const = make_known("BPSK", 250_000)

real_est = sd.estimate_carrier_offset
print(f"  new (power=2, what the fix does): "
      f"{real_est(sig, FS, power=2):+9.1f} Hz   "
      f"error {real_est(sig, FS, power=2) - TRUE_OFFSET:+8.1f} Hz")
print(f"  old (power=4, hardcoded before): "
      f"{real_est(sig, FS, power=4):+9.1f} Hz   "
      f"error {real_est(sig, FS, power=4) - TRUE_OFFSET:+8.1f} Hz")
print()

r_new = demodulate(sig, FS, modulation="BPSK", sps=sps)
print(f"  demod with power=2 : locked={r_new.locked}  "
      f"EVM={r_new.evm_percent if r_new.evm_percent else float('nan'):.1f}%  "
      f"reason={r_new.reason[:50]}")

# Simulate the OLD behaviour: force power=4 regardless of modulation.
def forced_power(x, samp_rate, power=4):
    return real_est(x, samp_rate, power=4)

sd.estimate_carrier_offset = forced_power
r_old = demodulate(sig, FS, modulation="BPSK", sps=sps)
sd.estimate_carrier_offset = real_est
print(f"  demod with power=4 : locked={r_old.locked}  "
      f"EVM={r_old.evm_percent if r_old.evm_percent else float('nan'):.1f}%  "
      f"reason={r_old.reason[:50]}")

if (not r_new.locked) and (not r_old.locked):
    print("\n  VERDICT: pre-existing. Both exponents refuse, so the SPS=4 BPSK")
    print("           failure is NOT a regression from the exponent change.")
elif r_old.locked and not r_new.locked:
    print("\n  VERDICT: REGRESSION. power=4 worked and power=2 does not.")
else:
    print("\n  VERDICT: no regression; the fix is at least as good.")

print()
print("=" * 78)
print("Q2. BPSK failure onset vs SPS (alpha=0.35, seed=7)")
print("=" * 78)
print(f"{'R_s':>9} {'SPS':>5} {'locked':>8} {'EVM':>8} {'carrier err':>12}")
print("-" * 78)
for rate in (500_000, 400_000, 333_333, 250_000, 200_000, 125_000, 100_000):
    sps_i = int(round(FS / rate))
    sig_i, sps_used, _, _ = make_known("BPSK", rate)
    r = demodulate(sig_i, FS, modulation="BPSK", sps=sps_used)
    evm = f"{r.evm_percent:.1f}%" if r.evm_percent is not None else "--"
    cerr = (f"{r.carrier_offset_hz - TRUE_OFFSET:+.0f}"
            if r.carrier_offset_hz is not None else "--")
    print(f"{rate/1e3:>8.0f}k {sps_i:>5} {str(r.locked):>8} {evm:>8} {cerr:>12}")

print()
print("=" * 78)
print("Q3. 8PSK at alpha=0.20 -- carrier error or closed eye?")
print("=" * 78)
print(f"{'alpha':>6} {'locked':>8} {'EVM':>8} {'carrier err':>12} {'n_sym':>7}")
print("-" * 78)
for alpha in (0.50, 0.35, 0.30, 0.25, 0.20, 0.15):
    sig_a, sps_a, _, _ = make_known("8PSK", 100_000, alpha=alpha)
    r = demodulate(sig_a, FS, modulation="8PSK", sps=sps_a)
    evm = f"{r.evm_percent:.1f}%" if r.evm_percent is not None else "--"
    cerr = (f"{r.carrier_offset_hz - TRUE_OFFSET:+.0f}"
            if r.carrier_offset_hz is not None else "--")
    print(f"{alpha:>6.2f} {str(r.locked):>8} {evm:>8} {cerr:>12} "
          f"{r.n_symbols:>7}")

print()
print("  Note: for 8PSK the carrier exponent is 8, so the unambiguous span is")
print("  fs/8 = 125 kHz and a +60 kHz offset folds to +60 kHz (no fold).")
print("=" * 78)
