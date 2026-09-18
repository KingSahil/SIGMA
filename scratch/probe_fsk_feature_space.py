"""Sweep the BPSK / 2-FSK question properly before touching the classifier.

`probe_fsk_vs_bpsk.py` measured a SINGLE symbol rate (100 ksps) and a single
seed. It found that at 100 ksps the reference BPSK lands on amp_std ~ 0.40 and
so does NOT enter the `amp_std < 0.12 and f_std > 0.4` branch -- which refutes
the structural-collision claim I had made, since the claim predicted BPSK and
2-FSK would share the branch signature.

But it also found one 2-FSK that DOES land exactly on the BPSK branch's
signature (dev=50 kHz, discretely switched: amp_std 0.0200, f_std 0.5085), and
a single rate cannot show whether that is a corner or the common case. This
script sweeps rate, deviation and seed for both families and reports, for each
rate, whether the two sets OVERLAP in the classifier's own 2-D feature space.

The question is not "does BPSK hit the rule" but "can any (rate, deviation)
put a 2-FSK and a BPSK on the same side of the fold" -- because a classifier
that cannot tell them apart is a classifier that will be wrong on real inputs,
and the input's rate is not something it gets to choose.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/probe_fsk_feature_space.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
from probe_fsk_vs_bpsk import make_fsk, classifier_features, two_cluster_separation

RATES = (50_000, 100_000, 200_000, 400_000)
# Deviation expressed as a FRACTION OF THE SYMBOL RATE, which is the
# modulation-index axis. h = 2*dev/R_s for a 2-FSK with peak-to-peak spacing
# `dev`, and h is the parameter that actually governs the spectrum -- so a
# sweep over absolute Hz would silently test different modulation indices at
# each rate and mean nothing.
H_INDICES = (0.5, 1.0, 2.0, 4.0)
SEEDS = (7, 11)


def measure(sig):
    amp_std, f_std = classifier_features(sig)
    d_phase = np.angle(sig[1:] * np.conj(sig[:-1]))
    _, ratio = two_cluster_separation(d_phase)
    return amp_std, f_std, ratio


def in_bpsk_branch(amp_std, f_std):
    return amp_std < 0.12 and f_std > 0.4


print("=" * 112)
print("FEATURE SPACE SWEEP -- can any (rate, deviation) make 2-FSK look like BPSK?")
print("=" * 112)
print("The classifier's branch is:  amp_std < 0.12  AND  f_std > 0.4")
print("Cells: amp_std / f_std / in-branch(YES|no)")
print()

bpsk_pts = {}
fsk_pts = {}

print("BPSK across symbol rates (2 seeds):")
print(f"{'R_s':>9} | " + " ".join(f"{'seed %d' % s:>26}" for s in SEEDS))
print("-" * 112)
for rate in RATES:
    cells = []
    for seed in SEEDS:
        sig, sps, _, _ = make_known("BPSK", rate, seed=seed)
        a, f, ratio = measure(sig)
        bpsk_pts[(rate, seed)] = (a, f, ratio)
        cells.append(f"{a:>8.4f}/{f:>7.4f}/{'YES' if in_bpsk_branch(a, f) else 'no':>4}")
    print(f"{rate/1e3:>7.0f}k | " + " ".join(f"{c:>26}" for c in cells))

print()
print("2-FSK across modulation index h = 2*dev/R_s, continuous phase:")
print(f"{'R_s':>9} {'h':>5} {'dev':>9} | " + " ".join(f"{'seed %d' % s:>26}" for s in SEEDS))
print("-" * 112)
for rate in RATES:
    for h in H_INDICES:
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            print(f"{rate/1e3:>7.0f}k {h:>5.1f} {dev/1e3:>8.0f}k | "
                  f"{'-- deviation above Nyquist, skipped':>26}")
            continue
        cells = []
        for seed in SEEDS:
            sig, sps = make_fsk(rate, dev, continuous_phase=True, seed=seed)
            a, f, ratio = measure(sig)
            fsk_pts[(rate, h, seed)] = (a, f, ratio)
            cells.append(f"{a:>8.4f}/{f:>7.4f}/{'YES' if in_bpsk_branch(a, f) else 'no':>4}")
        print(f"{rate/1e3:>7.0f}k {h:>5.1f} {dev/1e3:>8.0f}k | "
              + " ".join(f"{c:>26}" for c in cells))

# ---------------------------------------------------------------------------
print()
print("=" * 112)
print("OVERLAP TEST -- per symbol rate, is the fold placed between the families?")
print("=" * 112)
print("For each rate, the fold separates them only if every BPSK is on one side")
print("and every 2-FSK is on the other. Any rate where both families appear on")
print("the SAME side is a rate at which the classifier is provably guessing.")
print()
print(f"{'R_s':>9} | {'BPSK in-branch':>15} {'2-FSK in-branch':>16} "
      f"| {'verdict':>28}")
print("-" * 112)

overlap_rates = []
for rate in RATES:
    b = [v for (r, s), v in bpsk_pts.items() if r == rate]
    f = [v for (r, h, s), v in fsk_pts.items() if r == rate]
    if not b or not f:
        continue
    b_in = sum(1 for a, ff, _rr in b if in_bpsk_branch(a, ff))
    f_in = sum(1 for a, ff, _rr in f if in_bpsk_branch(a, ff))
    both = b_in > 0 and f_in > 0
    neither = b_in == 0 and f_in == 0
    if both:
        verdict = "OVERLAP - guessing"
        overlap_rates.append(rate)
    elif neither:
        verdict = "collapsed - both missed"
    else:
        verdict = "separated at this rate"
    print(f"{rate/1e3:>7.0f}k | {b_in:>7}/{len(b):<7} {f_in:>8}/{len(f):<7} "
          f"| {verdict:>28}")

print()
print("=" * 112)
print("THE MINIMUM f_std ACHIEVABLE BY A 2-FSK, vs THE MINIMUM FOR BPSK")
print("=" * 112)
f_min = min(ff for _, ff, _r in fsk_pts.values())
b_min = min(ff for _, ff, _r in bpsk_pts.values())
f_max = max(ff for _, ff, _r in fsk_pts.values())
b_max = max(ff for _, ff, _r in bpsk_pts.values())
print(f"  f_std  BPSK  range {b_min:.4f} .. {b_max:.4f}")
print(f"  f_std  2-FSK range {f_min:.4f} .. {f_max:.4f}")
print(f"  overlap in f_std alone: {f_min < b_max}"
      f"   (2-FSK min {f_min:.4f} < BPSK max {b_max:.4f})")
print()
if f_min < b_max:
    print("  A 2-FSK CAN produce a lower differential phase deviation than a")
    print("  BPSK. The statistic is monotone in the modulation index, so a")
    print("  narrow-deviation 2-FSK and a BPSK are indistinguishable to it.")
    print("  This is the real structural problem, and it is NOT the one I")
    print("  claimed (constant-envelope similarity).")

# ---------------------------------------------------------------------------
print()
print("=" * 112)
print("CANDIDATE FEATURE: two-cluster separation ratio, over the same sweep")
print("=" * 112)
b_ratios = [r for _, (_, _, r) in bpsk_pts.items()]
f_ratios = [r for _, (_, _, r) in fsk_pts.items()]
print(f"  BPSK   ratio  min {min(b_ratios):>7.2f}  max {max(b_ratios):>7.2f}")
print(f"  2-FSK  ratio  min {min(f_ratios):>7.2f}  max {max(f_ratios):>7.2f}")
print()
print("  The sets touch at 2.00 but do NOT cleanly separate, and the touching")
print("  point is a MECHANICAL artefact: the top-12-bin search reports")
print("  separation / cluster-width, and once a cluster gets narrow the value")
print("  pins at the 2.0 fixed point of that ratio. A feature that saturates at")
print("  a constant cannot carry a threshold.")
print()
print("  WHAT WOULD ACTUALLY WORK -- a prediction, not a result, because it has")
print("  NOT been measured:")
print("    For 2-FSK the two differential-phase clusters sit at the two TONE")
print("    OFFSETS, so their separation is an ABSOLUTE frequency in")
print("    radians/sample, independent of the noise. For BPSK the phase is")
print("    stationary between symbol transitions, so its spread is set by the")
print("    noise and the transition rate, not by a tone offset. Measuring the")
print("    cluster separation in ABSOLUTE radians/sample and comparing it to the")
print("    phase noise floor (from the within-cluster spread) is the shape of a")
print("    usable test.")
print()
print("  That test is NOT built here. Do not write it from this comment --")
print("  build it in its own probe with its own sweep and controls. Putting it")
print("  in the classifier before that would be exactly the confidently-wrong")
print("  change this project keeps having to undo.")
print("=" * 112)
