"""PROBE (not a verification suite): why the phase-domain clock fallback fails.

    *** THE CODE MEASURED HERE IS NOT IN THE SHIPPED MODULE. ***
    `_clock_from_phase` / `_welch` / `_refine_peak` below are a LOCAL COPY of a
    fallback that was written for src/sigma_symbol_rate.py, measured, found to
    produce confident WRONG answers, and REVERTED (git: the file is back to its
    committed state). They are reproduced here only so the failure stays
    reproducible. Do not copy them into src/ without reading
    probe_phase_clock3.py first -- it shows the peak is not at R_s at all.

The fallback failed like this: three of four 2-FSK cases stayed unlocked and
one locked at 8723 Hz against a true 50000 Hz -- a WRONG answer, which is worse
than a refusal.

Before touching the code again, measure the statistic at the point where it is
built, so the failure is localised rather than guessed at:

  1. Does the squared-phase sequence actually contain a line at R_s?
     -> take the Welch spectrum of m2 and print the top few peaks in the band,
        with the true R_s marked. If R_s is not among them, the statistic is
        wrong, not the threshold.
  2. What does the line power look like versus the noise floor?
     -> the reported "prominence" is peak/median. If the true line sits BELOW
        other peaks, prominence is real but measures the wrong peak.

Every number here is printed, not summarised.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.sigma_symbol_rate import estimate_symbol_rate

FS_HI = 1_000_000.0


# ---------------------------------------------------------------------------
# Local copy of the REVERTED fallback. Not imported from src/, because it is
# not in src/ any more.
# ---------------------------------------------------------------------------
def _welch(signal, nfft, samp_rate):
    sig = np.asarray(signal, dtype=np.float64).ravel()
    if sig.size < nfft:
        return None, None
    win = np.hanning(nfft)
    step = nfft // 2
    acc, count = None, 0
    for start in range(0, len(sig) - nfft + 1, step):
        seg = sig[start:start + nfft]
        seg = seg - np.mean(seg)
        spec = np.abs(np.fft.rfft(seg * win)) ** 2
        acc = spec if acc is None else acc + spec
        count += 1
    if acc is None or count == 0:
        return None, None
    freqs = np.fft.rfftfreq(nfft, 1.0 / samp_rate)
    return acc / count, freqs


def _clock_from_phase(x, samp_rate, nfft=16384):
    """The reverted statistic, verbatim: detrend |d_phase|, square it, Welch."""
    x = np.asarray(x, dtype=np.complex128).ravel()
    if x.size < 1024:
        return 0.0, 0.0
    d = np.angle(x[1:] * np.conj(x[:-1]))
    m = np.abs(d)
    m = m - np.mean(m)
    m2 = m * m
    m2 = m2 - np.mean(m2)
    spec, freqs = _welch(m2, nfft, samp_rate)
    if spec is None:
        return 0.0, 0.0
    band = (freqs > samp_rate * 1e-3) & (freqs < samp_rate * 0.45)
    if not band.any():
        return 0.0, 0.0
    band_spec = spec[band]
    band_freqs = freqs[band]
    peak_idx = int(np.argmax(band_spec))
    floor = float(np.median(band_spec))
    if floor <= 1e-30:
        return 0.0, 0.0
    prominence_db = 10.0 * np.log10(float(band_spec[peak_idx]) / floor)
    return float(band_freqs[peak_idx]), prominence_db


def make_fsk(n_symbols, sps, dev_hz, fs, seed=0):
    """Discrete-deviation 2-FSK: each symbol is one of two exact tones."""
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n_symbols)
    tones = np.where(bits == 1, +dev_hz, -dev_hz)
    phase = np.repeat(tones, sps) * (2.0 * np.pi / fs)
    return np.exp(1j * np.cumsum(phase)).astype(np.complex128), bits


def top_peaks(spec, freqs, n=6, lo_frac=1e-3, hi_frac=0.45, fs=1.0):
    band = (freqs > fs * lo_frac) & (freqs < fs * hi_frac)
    bs, bf = spec[band], freqs[band]
    floor = float(np.median(bs))
    order = np.argsort(bs)[::-1]
    out = []
    for i in order[:n]:
        out.append((float(bf[i]), 10.0 * np.log10(float(bs[i]) / floor)))
    return out, floor


CASES = [
    ("2-FSK h=2 @100k (fs=1M, sps=10)", FS_HI, 10, 50_000.0, 100_000.0),
    ("2-FSK h=4 @100k (fs=1M, sps=10)", FS_HI, 10, 100_000.0, 100_000.0),
    ("2-FSK h=2 @200k (fs=1M, sps=5) ", FS_HI, 5, 80_000.0, 200_000.0),
    ("2-FSK h=4 @50k  (fs=200k,sps=4)", 200_000.0, 4, 100_000.0, 50_000.0),
]

print("=" * 78)
print("A. Does the squared-phase statistic contain a line at R_s ?")
print("=" * 78)
for name, fs, sps, dev, rs in CASES:
    n_sym = 4000
    x, bits = make_fsk(n_sym, sps, dev, fs, seed=1)

    d = np.angle(x[1:] * np.conj(x[:-1]))
    m = np.abs(d)
    m_centred = m - np.mean(m)
    m2 = m_centred * m_centred
    m2 = m2 - np.mean(m2)

    nfft = 16384
    while nfft > len(m2) // 2 and nfft > 1024:
        nfft //= 2
    spec, freqs = _welch(m2, nfft, fs)
    peaks, floor = top_peaks(spec, freqs, n=8, fs=fs)

    print(f"\n{name}")
    print(f"  R_s true = {rs:>9.0f} Hz   nfft={nfft}  bin={fs/nfft:.2f} Hz"
          f"  R_s is bin {rs/(fs/nfft):.1f}")
    print(f"  top peaks (freq Hz, dB over median floor):")
    for f, db in peaks:
        tag = "  <-- TRUE R_s" if abs(f - rs) < fs / nfft * 3 else ""
        print(f"    {f:>10.1f}  {db:>7.2f} dB{tag}")
    idx = int(np.argmin(np.abs(freqs - rs)))
    near = float(spec[idx])
    print(f"  bin at R_s      : {10.0*np.log10(near/floor):>7.2f} dB over floor")
    print(f"  median floor    : (absolute {floor:.3e})")
    f_rep, db_rep = _clock_from_phase(x, fs)
    print(f"  _clock_from_phase -> {f_rep:.1f} Hz  {db_rep:.2f} dB")

print()
print("=" * 78)
print("B. Is the discriminator magnitude even a two-level signal here?")
print("=" * 78)
for name, fs, sps, dev, rs in CASES:
    x, bits = make_fsk(4000, sps, dev, fs, seed=1)
    d = np.angle(x[1:] * np.conj(x[:-1]))
    m = np.abs(d)
    interior = m[(sps - 1) // 2::sps]
    print(f"\n{name}")
    print(f"  |d_phase| overall  : mean {np.mean(m):.4f} std {np.std(m):.4f}")
    print(f"  |d_phase| interior : mean {np.mean(interior):.4f} "
          f"std {np.std(interior):.4f} "
          f"min {np.min(interior):.4f} max {np.max(interior):.4f}")
    print(f"  expected tone |dev|: {2*np.pi*dev/fs:.4f} rad/sample x2 tones "
          f"-> separation {4*np.pi*dev/fs:.4f}")

print()
print("=" * 78)
print("C. What the SHIPPED estimator reports end to end")
print("=" * 78)
for name, fs, sps, dev, rs in CASES:
    x, bits = make_fsk(4000, sps, dev, fs, seed=1)
    r = estimate_symbol_rate(x, fs)
    print(f"  {name}: locked={r['locked']} R_s={r['symbol_rate_hz']:.0f} "
          f"(true {rs:.0f}) conf={r['confidence_label']} "
          f"{r['prominence_db']:.1f}dB")
