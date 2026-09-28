"""Where does the +22 Hz 8PSK carrier error come from?

The rotation/frequency iteration cannot fix 8PSK seed 9 because the failure is
upstream: the tracker is decision-directed, and with a 22 Hz residual the
rotation lands on +103.5 degrees, which is not a multiple of 8PSK's 45-degree
symmetry -- so the decisions it slices against are wrong and the slope it reads
is meaningless.

So the carrier ESTIMATE itself must be examined. This reports, for the failing
seed against a working seed:
  - the estimate with and without the sub-bin refinement
  - the x^8 spectrum's top peaks and their levels
  - the line-to-floor ratio, which is what the refinement maximises
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
import sigma_demod as sd

TRUE = 60_000.0


def probe(mod, rate, alpha, seed):
    sig, sps, idx, const = make_known(mod, rate, alpha=alpha, seed=seed)
    power = sd.SYMMETRY_ORDER[mod]

    est_coarse = sd.estimate_carrier_offset(sig, FS, power=power, refine=False)
    est_refined = sd.estimate_carrier_offset(sig, FS, power=power, refine=True)

    n = len(sig)
    nfft = 1 << int(np.floor(np.log2(max(1024, min(n, 65536)))))
    if nfft > n:
        nfft = 1 << int(np.floor(np.log2(max(n, 2))))
    seg = sig[:nfft] * np.blackman(nfft)
    raised = seg.copy()
    for _ in range(power - 1):
        raised = raised * seg
    spec = np.abs(np.fft.fftshift(np.fft.fft(raised)))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / FS))

    order = np.argsort(spec)[::-1]
    top = []
    used = []
    for i in order:
        f = freqs[i]
        if any(abs(f - u) < 3.0 * FS / nfft for u in used):
            continue
        used.append(f)
        top.append((f, spec[i]))
        if len(top) == 4:
            break

    print(f"  {mod} {rate/1e3:.0f}k alpha={alpha:.2f} seed={seed}  "
          f"(n={n}, nfft={nfft}, bin={FS/nfft:.1f} Hz, power={power})")
    print(f"    coarse  : {est_coarse:>+10.1f} Hz   error {est_coarse-TRUE:>+8.1f}")
    print(f"    refined : {est_refined:>+10.1f} Hz   error {est_refined-TRUE:>+8.1f}")
    print(f"    x^{power} spectrum top peaks (line freq -> implied offset):")
    for f, lv in top:
        print(f"        {f:>+11.1f} Hz -> {f/power:>+9.1f} Hz   level {lv:>10.1f}")
    floor = float(np.median(spec))
    print(f"    line-to-floor of the strongest peak: "
          f"{10*np.log10(top[0][1]/floor):.1f} dB")


print("=" * 88)
print("8PSK CARRIER ESTIMATE - working seed vs failing seed")
print("=" * 88)
probe("8PSK", 100_000, 0.20, 7)
print()
probe("8PSK", 100_000, 0.20, 8)
print()
probe("8PSK", 100_000, 0.20, 9)
print()
probe("8PSK", 250_000, 0.35, 8)
print()
probe("8PSK", 250_000, 0.35, 9)
print("=" * 88)
