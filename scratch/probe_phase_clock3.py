"""PROBE (not a verification suite): confirm the harmonic-resolution failure.

    *** THE STATISTIC MEASURED HERE IS NOT IN THE SHIPPED MODULE. ***
    `_clock_from_phase` below is a LOCAL COPY of a fallback written for
    src/sigma_symbol_rate.py, measured, found to produce confident wrong
    answers, and REVERTED. This file is the measurement that settled it.

probe_phase_clock2.py showed construction (b) h=2 @100k locking at 199999 Hz
against a true 100000 Hz -- the SECOND HARMONIC, reported at 191.5 dB.

Two candidate explanations, and they call for different fixes:

  (i)  R_s = 100 kHz is outside the search band. The band is
       (samp_rate*1e-3, samp_rate*0.45). At fs=1M the top is 450 kHz, so
       100 kHz is well inside. NOT the cause.
  (ii) The statistic genuinely puts its strongest line somewhere other than
       R_s. For a two-level signal whose transitions are the feature, the
       transition train has period sps, and squaring a train of impulses at
       rate R_s puts energy at multiples of R_s. That is the mechanism the
       docstring claimed ("squaring is what creates the line"), and it
       predicts the harmonic is the real peak.

The VERDICT measured below: the raw peak sits at 3*R_s, 5*R_s and even 15*R_s
across the sweep -- it is not a fixed harmonic, it is wherever the windows and
the squaring happen to concentrate energy. Sub-harmonic resolution rescues it
only when a divisor of 2 happens to fall within 3 dB of the peak, which is why
it works for three rows and silently fails for the rest.

THIS IS WHY THE FALLBACK WAS REVERTED RATHER THAN TUNED. A statistic whose peak
location does not track R_s cannot be fixed by moving a threshold.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


# --- LOCAL COPY of the reverted statistic. Not in src/ any more. -------------
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


def make_fsk_b(n_symbols, sps, dev_hz, fs, seed=0):
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n_symbols)
    tones = np.where(bits == 1, +dev_hz, -dev_hz)
    inc = np.repeat(tones, sps) * (2.0 * np.pi / fs)
    ph = np.cumsum(inc) + np.repeat(tones, sps) * (2.0 * np.pi / fs) * 0.5
    return np.exp(1j * ph).astype(np.complex128), bits


CASES = [
    ("h=1 @100k fs=1M sps=10", 1_000_000.0, 10, 25_000.0, 100_000.0),
    ("h=2 @100k fs=1M sps=10", 1_000_000.0, 10, 50_000.0, 100_000.0),
    ("h=4 @100k fs=1M sps=10", 1_000_000.0, 10, 100_000.0, 100_000.0),
    ("h=2 @200k fs=1M sps=5 ", 1_000_000.0, 5, 80_000.0, 200_000.0),
    ("h=4 @50k  fs=200k sps=4", 200_000.0, 4, 100_000.0, 50_000.0),
    ("h=2 @100k fs=1M sps=20", 1_000_000.0, 20, 50_000.0, 50_000.0),
    ("h=1 @25k  fs=1M sps=40", 1_000_000.0, 40, 12_500.0, 25_000.0),
]

print("=" * 90)
print("Where does the phase-domain peak sit, relative to R_s and 2*R_s?")
print("=" * 90)
print(f"{'case':<26} {'R_s':>8} {'2R_s':>8} {'peak':>10} {'prom dB':>8} "
      f"{'<-nearest':>10}  verdict")

for name, fs, sps, dev, rs in CASES:
    x, bits = make_fsk_b(8000, sps, dev, fs, seed=1)
    f_rep, db = _clock_from_phase(x, fs)

    d = np.angle(x[1:] * np.conj(x[:-1]))
    m = np.abs(d)
    m = m - np.mean(m)
    m2 = m * m
    m2 = m2 - np.mean(m2)
    nfft = 16384
    while nfft > len(m2) // 2 and nfft > 1024:
        nfft //= 2
    spec, freqs = _welch(m2, nfft, fs)
    band = (freqs > fs * 1e-3) & (freqs < fs * 0.45)
    bs, bf = spec[band], freqs[band]
    floor = float(np.median(bs))
    raw_i = int(np.argmax(bs))
    raw_f = float(bf[raw_i])
    raw_db = 10.0 * np.log10(float(bs[raw_i]) / floor)

    cands = {"R_s": rs, "2R_s": 2 * rs, "3R_s": 3 * rs}
    nearest = min(cands, key=lambda k: abs(cands[k] - raw_f))
    err = abs(cands[nearest] - raw_f) / cands[nearest]
    verdict = f"raw peak ~ {nearest}" if err < 0.05 else "raw peak = UNKNOWN"
    print(f"{name:<26} {rs:>8.0f} {2*rs:>8.0f} {raw_f:>10.1f} {raw_db:>8.2f} "
          f"{nearest:>10}  {verdict}")
    print(f"{'':<26} returned by _clock_from_phase: {f_rep:.1f} Hz ({db:.1f} dB)")

print()
print("=" * 90)
print("Does sub-harmonic resolution rescue it?  (accept window is 3 dB)")
print("=" * 90)
for name, fs, sps, dev, rs in CASES:
    x, bits = make_fsk_b(8000, sps, dev, fs, seed=1)
    d = np.angle(x[1:] * np.conj(x[:-1]))
    m = np.abs(d)
    m = m - np.mean(m)
    m2 = m * m
    m2 = m2 - np.mean(m2)
    nfft = 16384
    while nfft > len(m2) // 2 and nfft > 1024:
        nfft //= 2
    spec, freqs = _welch(m2, nfft, fs)
    band = (freqs > fs * 1e-3) & (freqs < fs * 0.45)
    bs, bf = spec[band], freqs[band]
    floor = float(np.median(bs))
    raw_i = int(np.argmax(bs))
    raw_mag = float(bs[raw_i])
    print(f"\n{name}: raw peak {float(bf[raw_i]):.0f} Hz"
          f"  (= {float(bf[raw_i])/rs:.2f} x R_s), mag {raw_mag:.3e}")
    for div in (2, 3):
        target = float(bf[raw_i]) / div
        j = int(np.argmin(np.abs(bf - target)))
        mag = float(bs[j])
        db_below = 10.0 * np.log10(raw_mag / mag) if mag > 0 else float("inf")
        accept = mag >= raw_mag * 10 ** (-3.0 / 10.0)
        print(f"    R_s candidate {target:>9.0f} Hz (bin {float(bf[j]):>9.1f}): "
              f"{db_below:>6.2f} dB below peak  "
              f"{'ACCEPTED' if accept else 'rejected'}")
