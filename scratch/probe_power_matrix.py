"""Full matrix: which exponent gives each constellation a correct carrier fix?"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from sigma_demod import rrc_filter

def make(order, rs=100_000.0, fs=1_000_000, alpha=0.35, n=2000, seed=7, off=60_000.0,
         noise=0.02):
    rng = np.random.default_rng(seed)
    sps = int(round(fs / rs))
    const = np.exp(1j * 2 * np.pi * np.arange(order) / order)
    idx = rng.integers(0, order, n)
    up = np.zeros(n * sps, dtype=np.complex128); up[::sps] = const[idx]
    shaped = np.convolve(up, rrc_filter(sps, alpha), mode="same")
    t = np.arange(len(shaped)) / fs
    shaped *= np.exp(1j * 2 * np.pi * off * t)
    shaped += (rng.normal(0, noise, len(shaped)) + 1j * rng.normal(0, noise, len(shaped)))
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64)

def est(x, fs, power):
    n = len(x)
    nfft = 1 << int(np.floor(np.log2(max(1024, min(n, 65536)))))
    seg = x[:nfft] * np.blackman(nfft)
    p = seg.copy()
    for _ in range(power - 1):
        p = p * seg
    spec = np.abs(np.fft.fftshift(np.fft.fft(p)))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / fs))
    off = freqs[int(np.argmax(spec))] / power
    span = fs / power
    while off > span / 2:  off -= span
    while off < -span / 2: off += span
    return off

print("Carrier-offset error (Hz) by constellation and exponent. True offset +60,000.")
print("The exponent must equal the constellation's rotational symmetry order.")
print("-" * 72)
print(f"{'signal':>8} | " + " | ".join(f"{'x^'+str(p):>9}" for p in (1, 2, 4, 8)))
print("-" * 72)
for order in (2, 4, 8):
    row = []
    x = make(order)
    for p in (1, 2, 4, 8):
        e = est(x, 1_000_000, p) if p > 1 else 0.0
        row.append(f"{e - 60_000:+9.0f}" if p > 1 else "     n/a ")
    print(f"{order}-PSK{'':>3} | " + " | ".join(row))
print("-" * 72)
print("Conclusion: x^1 x^2 x^4 x^8 -> correct exponent is 1 (none), 2, 4, 8 respectively.")
