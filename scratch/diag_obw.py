"""Why is OBW/Rs wrong? Look at the actual spectrum for two cases."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from make_ground_truth import make_signal

FS = 1_000_000.0

def psd_of(x, fs, nfft=16384):
    win = np.hanning(nfft)
    step = nfft // 2
    acc, cnt = None, 0
    for s in range(0, len(x) - nfft + 1, step):
        seg = x[s:s+nfft] * win
        sp = np.abs(np.fft.fft(seg)) ** 2
        acc = sp if acc is None else acc + sp
        cnt += 1
    psd = acc / cnt
    f = np.fft.fftfreq(nfft, d=1.0/fs)
    o = np.argsort(f)
    return f[o], psd[o]

for rs, alpha in ((25_000, 0.35), (100_000, 0.35), (250_000, 0.35)):
    sig, sps = make_signal(rs, "bpsk", alpha=alpha, n_symbols=6000, seed=7)
    f, p = psd_of(sig, FS)
    p_db = 10*np.log10(np.maximum(p, 1e-20))
    peak = p_db.max()
    # find where the signal actually sits (above -20 dB of peak)
    above = np.where(p_db > peak - 20)[0]
    lo_f, hi_f = f[above[0]], f[above[-1]]
    c = np.cumsum(p); c /= c[-1]
    o5, o995 = f[np.searchsorted(c, 0.005)], f[np.searchsorted(c, 0.995)]
    print(f"Rs={rs/1e3:6.0f}k alpha={alpha}  true SPS={sps}")
    print(f"   true occupied band   = {rs*(1+alpha)/1e3:7.1f} kHz")
    print(f"   -20dB extent         = {lo_f/1e3:7.1f} .. {hi_f/1e3:7.1f} kHz  "
          f"(width {(hi_f-lo_f)/1e3:.1f} kHz)")
    print(f"   99% OBW from cumsum  = {o5/1e3:7.1f} .. {o995/1e3:7.1f} kHz  "
          f"(width {abs(o995-o5)/1e3:.1f} kHz)")
    print(f"   noise floor / peak   = {p_db.min()-peak:.1f} dB")
    print()
