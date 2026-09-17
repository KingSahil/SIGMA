"""Can occupied bandwidth (measured in Hz, which needs f_s) let us RECOVER f_s?

The idea: OBW for an RRC-shaped signal is approximately R_s * (1 + alpha).
That is a *physical* relationship independent of what sample rate we assume.
If we assume a wrong f_s, we measure a wrong OBW -- and a wrong OBW/R_s ratio.
The ratio is scale-INVARIANT though: SPS = f_s/R_s is measured from the
envelope spectrum, so we can solve the system.

This script measures, for known ground truth, whether
    (measured OBW / measured R_s)  ==  (1 + alpha)
holds tightly enough to invert. Run before writing any estimator.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from make_ground_truth import make_signal
from sigma_symbol_rate import estimate_symbol_rate

FS = 1_000_000.0

def measure_obw(x, fs, frac_lo=0.005, frac_hi=0.995):
    """99% occupied bandwidth using a Welch-averaged periodogram."""
    nfft = 16384
    if len(x) < nfft:
        nfft = 1 << int(np.floor(np.log2(len(x))))
    win = np.hanning(nfft)
    step = nfft // 2
    acc, cnt = None, 0
    for s in range(0, len(x) - nfft + 1, step):
        seg = x[s:s + nfft] * win
        sp = np.abs(np.fft.fft(seg)) ** 2
        acc = sp if acc is None else acc + sp
        cnt += 1
    if acc is None:
        return None
    psd = acc / cnt
    freqs = np.fft.fftfreq(nfft, d=1.0 / fs)
    order = np.argsort(freqs)
    psd, freqs = psd[order], freqs[order]
    c = np.cumsum(psd)
    c /= c[-1]
    lo = freqs[np.searchsorted(c, frac_lo)]
    hi = freqs[np.searchsorted(c, frac_hi)]
    return abs(hi - lo)

print(f"{'true Rs':>9} {'mod':>5} {'alpha':>6} | {'meas Rs':>9} {'meas OBW':>9} "
      f"{'OBW/Rs':>7} {'1+a':>5} {'ratio err':>9}")
print("-" * 76)

rows = []
for rs in (25_000, 50_000, 100_000, 200_000, 250_000):
    for mod in ("BPSK", "QPSK"):
        for alpha in (0.20, 0.35, 0.50):
            sig, _true_sps = make_signal(rs, mod.lower(), alpha=alpha, n_symbols=6000, seed=7)
            sr = estimate_symbol_rate(sig, FS)
            obw = measure_obw(sig, FS)
            if not sr.get("locked") or obw is None:
                print(f"{rs/1e3:8.0f}k {mod:>5} {alpha:6.2f} |   (no lock)")
                continue
            mr = sr["symbol_rate_hz"]
            ideal = 1.0 + alpha
            ratio = obw / mr
            err = (ratio - ideal) / ideal * 100.0
            rows.append((rs, mod, alpha, mr, obw, ratio, ideal, err))
            print(f"{rs/1e3:8.0f}k {mod:>5} {alpha:6.2f} | {mr/1e3:8.2f}k {obw/1e3:8.1f}k "
                  f"{ratio:7.3f} {ideal:5.2f} {err:+8.1f}%")

if rows:
    errs = np.array([r[7] for r in rows])
    print("-" * 76)
    print(f"cases {len(rows)}   mean ratio error {errs.mean():+.1f}%   "
          f"std {errs.std():.1f}%   min {errs.min():+.1f}%   max {errs.max():+.1f}%")
