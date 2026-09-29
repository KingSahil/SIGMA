"""PROBE (not a verification suite): which FSK construction does the fallback
actually serve, and does it ever produce a WRONG lock?

    *** THE STATISTIC MEASURED HERE IS NOT IN THE SHIPPED MODULE. ***
    `_clock_from_phase` below is a LOCAL COPY of a fallback written for
    src/sigma_symbol_rate.py, measured, found to produce confident wrong
    answers, and REVERTED. It is reproduced only to keep the failure
    reproducible. See probe_phase_clock3.py for the measurement that settled it.

The first probe found |d_phase| std = 0.0000 on every case, which is impossible
for a signal that changes frequency. The cause: that probe built 2-FSK by
integrating a per-sample phase increment chosen once per symbol, which creates
an EXACT two-tone signal with NO transition sample. The discriminator is then a
perfect two-level constant, its mean-subtracted square is identically zero, and
the spectrum is numerical noise.

That construction is not what a real 2-FSK transmitter emits. A real one is
CONTINUOUS-PHASE: the phase runs continuously across the symbol boundary, so
the transition sample carries a value between the two tones. There are two
common constructions, and they differ exactly at that one sample:

  (a) phase = cumsum(repeat(tones, sps)) -- phase continuous, and the sample
      at index k*sps is ALREADY the new tone. Transition samples therefore sit
      at index k*sps, and the discriminator at that index shows a partial step.
  (b) the project's own make_fsk -- a 0.5-sps phase offset, so the transition
      sample is exactly halfway between the two tones.

Both are legitimate; they are not the same signal. This probe measures both
rather than assuming, and separately checks the thing that actually matters:

    DOES THE FALLBACK EVER RETURN A CONFIDENT WRONG ANSWER?

A wrong lock is worse than a refusal, so that is scored first.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.sigma_symbol_rate import estimate_symbol_rate


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


def make_fsk_a(n_symbols, sps, dev_hz, fs, seed=0):
    """(a) continuous phase, transition sample already at the new tone."""
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n_symbols)
    tones = np.where(bits == 1, +dev_hz, -dev_hz)
    inc = np.repeat(tones, sps) * (2.0 * np.pi / fs)
    return np.exp(1j * np.cumsum(inc)).astype(np.complex128), bits


def make_fsk_b(n_symbols, sps, dev_hz, fs, seed=0):
    """(b) the project's own construction: 0.5-sps phase offset."""
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n_symbols)
    tones = np.where(bits == 1, +dev_hz, -dev_hz)
    inc = np.repeat(tones, sps) * (2.0 * np.pi / fs)
    ph = np.cumsum(inc)
    ph = ph + np.repeat(tones, sps) * (2.0 * np.pi / fs) * 0.5
    return np.exp(1j * ph).astype(np.complex128), bits


CASES = [
    ("h=2 @100k fs=1M sps=10", 1_000_000.0, 10, 50_000.0, 100_000.0),
    ("h=4 @100k fs=1M sps=10", 1_000_000.0, 10, 100_000.0, 100_000.0),
    ("h=2 @200k fs=1M sps=5 ", 1_000_000.0, 5, 80_000.0, 200_000.0),
    ("h=4 @50k  fs=200k sps=4", 200_000.0, 4, 100_000.0, 50_000.0),
    ("h=1 @100k fs=1M sps=10", 1_000_000.0, 10, 25_000.0, 100_000.0),
]

for tag, maker in (("(a) cumsum", make_fsk_a), ("(b) half-sps lead", make_fsk_b)):
    print("=" * 78)
    print(f"Construction {tag}")
    print("=" * 78)
    for name, fs, sps, dev, rs in CASES:
        x, bits = maker(4000, sps, dev, fs, seed=1)
        d = np.angle(x[1:] * np.conj(x[:-1]))
        m = np.abs(d)
        interior = m[(sps - 1) // 2::sps]
        r = estimate_symbol_rate(x, fs)
        alt_f, alt_db = _clock_from_phase(x, fs)
        wrong = r["locked"] and abs(r["symbol_rate_hz"] - rs) > 0.05 * rs
        flag = "  *** WRONG LOCK ***" if wrong else ""
        print(f"  {name}: locked={str(r['locked']):5s} "
              f"R_s={r['symbol_rate_hz']:>9.0f} (true {rs:>7.0f}) "
              f"conf={r['confidence_label']:5s} {r['prominence_db']:>5.1f}dB"
              f"  | interior std={np.std(interior):.4f} "
              f"overall std={np.std(m):.4f}{flag}")
    print()

print("=" * 78)
print("C. Where is the clock line for construction (b), which has transitions?")
print("=" * 78)
for name, fs, sps, dev, rs in CASES[:4]:
    x, bits = make_fsk_b(4000, sps, dev, fs, seed=1)
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
    idx_rs = int(np.argmin(np.abs(bf - rs)))
    order = np.argsort(bs)[::-1]
    top = [(float(bf[i]), 10.0 * np.log10(float(bs[i]) / floor)) for i in order[:4]]
    print(f"\n  {name}  nfft={nfft} bin={fs/nfft:.1f} Hz  true R_s={rs:.0f}")
    print(f"    dB at true R_s bin : {10.0*np.log10(float(bs[idx_rs])/floor):.2f}")
    for f, db in top:
        tag = "  <-- R_s" if abs(f - rs) < fs / nfft * 3 else ""
        print(f"    peak {f:>10.1f} Hz  {db:>6.2f} dB{tag}")
