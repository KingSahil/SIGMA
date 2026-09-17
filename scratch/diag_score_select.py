"""
Decide the question: can we select the symbol rate by scoring spectrum
candidates with a SINGLE (mult=1) ISI contrast test, and does that beat
picking the strongest bin?

Key change vs the failed attempt: no mult in (1,2,3) -- test only the period
itself. Testing multiples triples the false-positive rate.
"""
import numpy as np, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from make_ground_truth import make_signal, FS
from sigma_symbol_rate import _isi_contrast

def envelope_spectrum(sig, n=16384):
    env = np.abs(sig) ** 2
    while n > len(env) // 2 and n > 1024:
        n //= 2
    w = np.hanning(n); step = n // 2
    acc = None; cnt = 0
    for s0 in range(0, len(env) - n + 1, step):
        seg = env[s0:s0 + n] - np.mean(env[s0:s0 + n])
        sp = np.abs(np.fft.rfft(seg * w)) ** 2
        acc = sp if acc is None else acc + sp
        cnt += 1
    spec = acc / cnt
    fr = np.fft.rfftfreq(n, 1.0 / FS)
    band = (fr > FS * 1e-3) & (fr < FS * 0.45)
    return spec[band], fr[band]

print("Single-test (mult=1) contrast score for top-24 spectral candidates.")
print("Reports: rank of the accepted candidate, and whether it is the true rate.")
print()
print(f"{'R_s':>7} {'mod':>5} {'a':>5} | {'top-bin':>8} {'true-rank':>9} "
      f"| {'scored-pick':>11} {'ok':>3} | {'strongest-pick':>14} {'ok':>3}")
print("-" * 90)
n_ok_score = n_ok_power = n_tot = 0
for rate in [25_000, 50_000, 100_000, 200_000, 250_000]:
    for mod in ["bpsk", "qpsk"]:
        for alpha in [0.20, 0.35]:
            sig, _ = make_signal(rate, mod, alpha=alpha, n_symbols=600, seed=7)
            bs, bf = envelope_spectrum(sig)
            order = np.argsort(bs)[::-1]

            # strongest-bin pick
            pick_power = float(bf[order[0]])

            # contrast-scored pick over top-24 unique
            tested = []; best_c = None; pick_score = None
            for idx in order:
                if len(tested) >= 24: break
                c = float(bf[idx])
                if any(abs(c - t) < 500.0 for t in tested): continue
                tested.append(c)
                cc = _isi_contrast(sig, FS / c)
                if cc is not None and (best_c is None or cc > best_c):
                    best_c = cc; pick_score = c

            itrue = int(np.argmin(np.abs(bf - rate)))
            rank = 1 + int((bs > bs[itrue]).sum())

            def near(a, b): return abs(a - b) / b < 0.03
            ok_s = near(pick_score, rate) if pick_score else False
            ok_p = near(pick_power, rate)
            n_tot += 1; n_ok_score += ok_s; n_ok_power += ok_p
            print(f"{rate/1e3:>6.0f}k {mod:>5} {alpha:>5.2f} | "
                  f"{pick_power/1e3:>7.1f}k {rank:>9} | "
                  f"{(pick_score/1e3 if pick_score else 0):>10.2f}k {str(ok_s):>5} | "
                  f"{pick_power/1e3:>13.1f}k {str(ok_p):>5}")
print("-" * 90)
print(f"contrast-scored pick correct: {n_ok_score}/{n_tot}   "
      f"strongest-bin correct: {n_ok_power}/{n_tot}")
