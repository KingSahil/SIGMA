"""Confirm the 8PSK carrier failure is the ^4 exponent, not anything else.

PSK of order M has M-fold rotational symmetry, so x^M collapses it to a tone.
QPSK -> x^4 (current, correct). 8PSK -> x^8 (not implemented).
""" 
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

def est_offset(x, fs, power):
    n = len(x)
    nfft = 1 << int(np.floor(np.log2(max(1024, min(n, 65536)))))
    seg = x[:nfft] * np.blackman(nfft)
    p = seg.copy()
    for _ in range(power - 1):
        p = p * seg
    spec = np.abs(np.fft.fftshift(np.fft.fft(p)))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / fs))
    peak = freqs[int(np.argmax(spec))]
    off = peak / power
    span = fs / power
    while off > span / 2:  off -= span
    while off < -span / 2: off += span
    return off

print("Carrier estimate error by exponent, true offset = +60,000 Hz")
print("=" * 68)
for order in (2, 4, 8):
    x = make(order)
    print(f"{order}-PSK signal (true +60,000 Hz):")
    for p in (2, 4, 8):
        e = est_offset(x, 1_000_000, p)
        err = e - 60_000
        flag = "  <- correct exponent" if p == order else ""
        print(f"    x^{p}  -> {e:+9.0f} Hz   error {err:+9.0f} Hz{flag}")
