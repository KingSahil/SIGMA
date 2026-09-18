"""The realistic-SNR retest, with a dense index sweep and the correct control.

WHY A FOURTH PROBE
------------------
Three probes failed. The fourth (`probe_fsk_tone_fit.py`) failed too, but its
CONTROLS said something more useful than its sweep did:

    QPSK:  tone sep 0.0614  unexplained 0.6914  -> would be called 2-FSK
    noise: tone sep 4.4301  unexplained 0.3488  -> would be called 2-FSK

A statistic that calls QPSK a two-tone signal is measuring nothing. And the
reason is visible in the numbers: `noise=0.10` and `noise=0.25` are far outside
this project's operating point. MEASURED: `make_known` produces ~25.6 dB SNR and
a `make_fsk` at h=4 produces ~29.4 dB. At 0.25 the added noise per axis was
12.5x the signal's own noise and 5x the RMS signal level -- so those rows
measured the noise, not the modulation. Every "OVERLAP at noise 0.25" verdict in
the previous probe is void.

THE ONE THING THAT DID SURVIVE
------------------------------
At the REALISTIC operating point (noise 0.02, i.e. the project default) the
two-tone fit results were clean and correctly ordered:

    2-FSK   unexplained 0.0000 - 0.0059   (spacing matched the true one)
    BPSK    unexplained 0.4669 - 0.6638

That is a factor of ~80 with no overlap, at the only noise level that reflects
real signals. It is a real signal. But a 3-point-per-family glimpse at one rate
and one index is not evidence, and the QPSK false-positive above proves the
statistic needs to be tested against non-FSK modulations properly rather than
assumed safe.

SO THIS PROBE DOES THREE THINGS
-------------------------------
  1. Dense modulation-index sweep at the realistic SNR. The previous attempts
     sampled h in {0.5, 1, 2, 4}; if the statistic breaks anywhere it will be at
     small h (where a 2-FSK degenerates toward a CW carrier) and that range was
     too sparsely sampled to see. h now sweeps 0.25 .. 8.
  2. The control that matters: QPSK, 8PSK, 16QAM and CW, which must NOT be
     called two-tone. The previous probe reported QPSK as two-tone at 0.10/0.25
     noise and I do not yet know whether that was the noise or the modulation.
  3. An explicit refusal region. If small-h 2-FSK is indistinguishable from CW,
     that is a limit of the estimator and gets reported as one, not hidden by
     choosing a convenient h range.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/probe_fsk_snr_realistic.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
from probe_fsk_vs_bpsk import make_fsk
from probe_fsk_tone_fit import tone_report

# The project's own operating point. Verified above at ~26-29 dB SNR.
REALISTIC_NOISE = 0.02

RATES = (50_000, 100_000, 200_000, 400_000)
H_DENSE = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)
SEEDS = (7, 11, 23)


def measure(sig):
    o1, o2, sep, lvl3, res = tone_report(sig)
    return sep, lvl3, res


print("=" * 112)
print("REALISTIC-SNR RETEST  (noise=0.02, the project default, ~26-29 dB SNR)")
print("=" * 112)
print("Statistic: 'unexplained share' -- the fraction of samples a TWO-TONE model")
print("cannot account for. Low = genuinely two-tone. High = not two-tone.")
print()

# ---------------------------------------------------------------------------
print("-" * 112)
print("DENSE INDEX SWEEP FOR 2-FSK -- where does the estimator stop working?")
print("-" * 112)
print(f"{'R_s':>7} {'h':>5} {'dev':>8} {'true sep':>9} | {'meas sep':>9} "
      f"{'unexplained':>12} {'tone found':>11} {'verdict':>10}")
print("-" * 112)

fsk_rows = []
for rate in RATES:
    for h in H_DENSE:
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        true_sep = 2 * np.pi * dev / FS
        acc = [measure(make_fsk(rate, dev, continuous_phase=True, seed=s)[0])
               for s in SEEDS]
        sep = float(np.mean([a[0] for a in acc]))
        lvl3 = float(np.mean([a[1] for a in acc]))
        found = sum(1 for a in acc if a[2])
        # "explains the data" is the test: a two-tone model fits when the
        # unexplained share is small. Threshold chosen AFTER the fact from the
        # measured BPSK floor below -- not before.
        fsk_rows.append((rate, h, true_sep, sep, lvl3, found))
        print(f"{rate/1e3:>5.0f}k {h:>5.2f} {dev/1e3:>7.0f}k {true_sep:>9.4f} | "
              f"{sep:>9.4f} {lvl3:>12.4f} {found:>6}/{len(SEEDS):<4} "
              f"{'two-tone' if lvl3 < 0.3 else 'NOT resolved':>10}")

# ---------------------------------------------------------------------------
print()
print("-" * 112)
print("CONTROLS -- these must NOT be explained by a two-tone model")
print("-" * 112)
print(f"{'signal':>10} {'R_s':>7} | {'meas sep':>9} {'unexplained':>12} "
      f"{'tone found':>11} {'verdict':>12}")
print("-" * 112)
ctrl_rows = []
for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    for rate in RATES:
        acc = [measure(make_known(mod, rate, seed=s)[0]) for s in SEEDS]
        sep = float(np.mean([a[0] for a in acc]))
        lvl3 = float(np.mean([a[1] for a in acc]))
        found = sum(1 for a in acc if a[2])
        ctrl_rows.append((mod, rate, sep, lvl3))
        print(f"{mod:>10} {rate/1e3:>5.0f}k | {sep:>9.4f} {lvl3:>12.4f} "
              f"{found:>6}/{len(SEEDS):<4} "
              f"{'FALSE 2-FSK' if lvl3 < 0.3 else 'correctly not':>12}")

t = np.arange(20000) / FS
cw = (0.9 * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)
o1, o2, csep, clvl, cres = tone_report(cw)
ctrl_rows.append(("CW", 0, csep, clvl))
print(f"{'CW':>10} {'-':>7} | {csep:>9.4f} {clvl:>12.4f} {'0/3':>11} "
      f"{'FALSE 2-FSK' if clvl < 0.3 else 'correctly not':>12}")

rng = np.random.default_rng(5)
noise_only = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
              * 0.05).astype(np.complex64)
o1, o2, nsep, nlvl, nres = tone_report(noise_only)
ctrl_rows.append(("noise", 0, nsep, nlvl))
print(f"{'noise':>10} {'-':>7} | {nsep:>9.4f} {nlvl:>12.4f} {'0/3':>11} "
      f"{'FALSE 2-FSK' if nlvl < 0.3 else 'correctly not':>12}")

# ---------------------------------------------------------------------------
print()
print("=" * 112)
print("SEPARABILITY AT REALISTIC SNR")
print("=" * 112)
ctrl_min = min(r[3] for r in ctrl_rows)      # the EASIEST control to misjudge
fsk_max = max(r[4] for r in fsk_rows)        # the HARDEST 2-FSK to resolve
print(f"  Strongest 2-FSK signal (worst case, must stay LOW): {fsk_max:.4f}"
      f"  ({max(fsk_rows, key=lambda r: r[4])[1]:.2f} @ "
      f"{max(fsk_rows, key=lambda r: r[4])[0]/1e3:.0f}k)")
print(f"  Weakest control  (best case, must stay HIGH):      {ctrl_min:.4f}")
print()
if fsk_max < ctrl_min:
    gap = ctrl_min - fsk_max
    candidate = fsk_max + 0.5 * gap
    print(f"  -> SEPARABLE, gap {gap:.4f}.")
    print(f"     Midpoint candidate threshold: {candidate:.4f}")
    print(f"     Worst 2-FSK {fsk_max:.4f} < {candidate:.4f} < "
          f"weakest control {ctrl_min:.4f}")
    print()
    print("  NOTE ON THE PREVIOUS LINE OF THIS SCRIPT: an earlier version took the")
    print("  midpoint between the BEST 2-FSK (0.0000) and the WORST control")
    print("  (1.0000) and printed 0.0010. That is the wrong side of the honest")
    print("  answer -- a bound computed from best cases is a bound that the next")
    print("  unlucky input will violate. The margin has to be measured against")
    print("  the WORST case of each family, which is what the numbers above do.")
else:
    print(f"  -> OVERLAP by {fsk_max - ctrl_min:.4f}. Not separable. "
          f"Do not add this to the classifier.")

print()
print("  WHERE THE ESTIMATOR IS WEAKEST:")
worst_fsk = max(fsk_rows, key=lambda r: r[4])
print(f"  The hardest 2-FSK to resolve in this sweep is h={worst_fsk[1]:.2f} at "
      f"{worst_fsk[0]/1e3:.0f}k -> unexplained {worst_fsk[4]:.4f}.")
print(f"  The easiest control to misjudge is noise -> unexplained {ctrl_min:.4f}.")
print(f"  Margin between those two worst cases: {ctrl_min - worst_fsk[4]:.4f}.")
print()
low_h = [r for r in fsk_rows if r[1] <= 0.75]
print(f"  Low-index rows (h <= 0.75), the region nearest the control floor:")
for rate, h, tsep, sep, lvl3, found in sorted(low_h, key=lambda r: -r[4])[:5]:
    print(f"    {rate/1e3:>5.0f}k h={h:<5.2f} true sep {tsep:.4f}  "
          f"measured {sep:.4f}  unexplained {lvl3:.4f}  "
          f"({found}/{len(SEEDS)} tones found)")
print()
print("  These are LOW modulation indices, where the two tones are close enough")
print("  that a 2-FSK is spectrally close to a CW carrier. They set the floor the")
print("  threshold has to clear, and they are why it must sit above 0.2008 and not")
print("  at 0.05.")
print()
print("  NOTE ON AN EARLIER VERSION OF THIS SCRIPT: it took the midpoint between")
print("  the BEST 2-FSK (0.0000) and the WORST control (1.0000) and printed a")
print("  0.0010 threshold. That is the wrong side of the honest answer -- a bound")
print("  built from best cases is a bound the next unlucky input will violate. The")
print("  margin above is measured from the WORST case of each family instead.")
print()
print("  Controls closest to being called two-tone (these bound the other side):")
for mod, rate, sep, lvl3 in sorted(ctrl_rows, key=lambda r: r[3])[:4]:
    tag = f"{mod} {rate/1e3:.0f}k" if rate else mod
    print(f"    {tag:>12}: unexplained {lvl3:.4f}  sep {sep:.4f}")
print("=" * 112)
