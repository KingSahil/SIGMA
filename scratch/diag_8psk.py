"""Why does 8PSK report a wrong carrier offset? Sweep the true offset."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from sigma_demod import demodulate, rrc_filter, estimate_carrier_offset

def make(mod="8PSK", rs=100_000.0, fs=1_000_000, alpha=0.35, n=2000, seed=7,
         off=60_000.0, noise=0.02):
    rng = np.random.default_rng(seed)
    sps = int(round(fs / rs))
    const = np.exp(1j * 2 * np.pi * np.arange(8) / 8)
    idx = rng.integers(0, 8, n)
    up = np.zeros(n * sps, dtype=np.complex128); up[::sps] = const[idx]
    shaped = np.convolve(up, rrc_filter(sps, alpha), mode="same")
    t = np.arange(len(shaped)) / fs
    shaped *= np.exp(1j * 2 * np.pi * off * t)
    shaped += (rng.normal(0, noise, len(shaped)) + 1j * rng.normal(0, noise, len(shaped)))
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64), sps

print("8PSK carrier recovery: true offset vs measured")
print("(the 4th-power method assumes QPSK symmetry; 8PSK has 8-fold symmetry)")
print("-" * 66)
for off in (0.0, 25_000.0, 50_000.0, 100_000.0, 150_000.0, 200_000.0):
    sig, sps = make(off=off)
    est = estimate_carrier_offset(sig, 1_000_000)
    r = demodulate(sig, 1_000_000, modulation="8PSK", sps=sps)
    print(f"  true {off:+9.0f} Hz  ->  est {est:+9.0f} Hz  "
          f"| locked={str(r.locked):5s} EVM {r.evm_percent:5.1f}%")
