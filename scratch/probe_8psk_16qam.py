"""Does the demodulator actually work on 8PSK / 16QAM if the gate let it through?

The GUI gate refuses anything that is not BPSK/QPSK, but sigma_demod.py has
8PSK and 16QAM constellations defined. This tests the demodulator directly,
bypassing the gate, to find out whether the gate is the only obstacle.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from sigma_demod import demodulate, rrc_filter

def make(mod, rs=100_000.0, fs=1_000_000, alpha=0.35, n=2000, seed=7, off=60_000.0,
         noise=0.02):
    rng = np.random.default_rng(seed)
    sps = int(round(fs / rs))
    if mod == "8PSK":
        const = np.exp(1j * 2 * np.pi * np.arange(8) / 8)
    elif mod == "16QAM":
        lv = np.array([-3, -1, 1, 3]) / np.sqrt(10)
        const = np.array([i + 1j * q for i in lv for q in lv])
    idx = rng.integers(0, len(const), n)
    up = np.zeros(n * sps, dtype=np.complex128)
    up[::sps] = const[idx]
    shaped = np.convolve(up, rrc_filter(sps, alpha), mode="same")
    t = np.arange(len(shaped)) / fs
    shaped *= np.exp(1j * 2 * np.pi * off * t)
    shaped += (rng.normal(0, noise, len(shaped)) + 1j * rng.normal(0, noise, len(shaped)))
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64), sps, idx, const

def bits_of(idx, k):
    b = np.zeros(len(idx) * k, dtype=np.uint8)
    for i, s in enumerate(idx):
        for j in range(k):
            b[i * k + j] = (s >> (k - 1 - j)) & 1
    return b

def accuracy(rec, exp):
    n = min(len(rec), len(exp))
    best = 0.0
    for shift in range(-4, 5):
        if shift >= 0:
            a, b = rec[shift:], exp[:len(rec) - shift]
        else:
            a, b = rec[:shift], exp[-shift:]
        m = min(len(a), len(b))
        if m > 0:
            best = max(best, float(np.mean(a[:m] == b[:m])))
    return best

print("Testing the demodulator DIRECTLY (bypassing the GUI gate)")
print("=" * 74)
for mod, k in (("8PSK", 3), ("16QAM", 4)):
    sig, sps, idx, const = make(mod)
    res = demodulate(sig, 1_000_000, modulation=mod, sps=sps)
    if not res.locked:
        print(f"  {mod:6s} -> NO LOCK: {res.reason}")
        continue
    exp = bits_of(idx, k)
    acc = accuracy(res.bits, exp)
    print(f"  {mod:6s} -> LOCKED  symbols={res.n_symbols:5d}  EVM={res.evm_percent:5.1f}%  "
          f"carrier={res.carrier_offset_hz:+9.0f} Hz  bit accuracy={acc * 100:6.2f}%")
