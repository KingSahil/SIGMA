"""Does the PHASE-HISTOGRAM BIMODALITY separate 2-FSK from BPSK?

WHERE THIS COMES FROM
---------------------
Two earlier probes narrowed the problem and are worth reading first:

  probe_fsk_vs_bpsk.py        single rate; refuted my first claim
  probe_fsk_feature_space.py  rate x index x seed sweep; found the real one

What they established, measured rather than argued:

  1. The `amp_std < 0.12 and f_std > 0.4` branch does NOT fire on a BPSK
     built the way this project builds signals. BPSK's amp_std measured
     0.40-0.51, well clear of the 0.12 gate. So my claim that BPSK and
     2-FSK share the branch signature was WRONG.

  2. `f_std` alone cannot separate them. Measured ranges:
          BPSK   f_std 0.4656 .. 1.3831
          2-FSK  f_std 0.0483 .. 1.2570
     A narrow-deviation 2-FSK produces a SMALLER phase deviation than any
     BPSK, and a wide one a larger. The statistic is monotone in the
     modulation index, so it mixes the two families across its whole range.
     This is the real structural problem.

  3. A 2-FSK with a sufficiently steep modulation index lands in the BPSK
     branch anyway (measured: h=4 at 100/200/400 ksps -> amp_std 0.020,
     f_std 0.63-1.26 -> YES), because 2-FSK is constant-envelope and a wide
     deviation drives f_std up. So the branch is reachable by BOTH -- which
     is what makes its "BPSK / 2-FSK" label honest, and also why the label
     cannot be resolved without a new feature.

  4. The separation/cluster-WIDTH ratio is unusable: it saturates at 2.00.

THE HYPOTHESIS UNDER TEST HERE
------------------------------
The right statistic is the ABSOLUTE separation of the two differential-phase
clusters, measured against the phase NOISE floor.

  * 2-FSK transmits ONE OF TWO TONES. The differential phase between adjacent
    samples is one of two CONSTANTS (the two tone offsets, in radians/sample).
    Noise spreads each constant into a narrow cluster. So: two clusters, each
    narrow, separated by a fixed frequency offset that is INDEPENDENT of SNR.
  * BPSK transmits ONE CARRIER with two phases. The differential phase is ~0
    within a symbol (plus carrier offset) and jumps by pi at a transition. The
    phase is stationary, so what looks like a "cluster" is the noise itself:
    separation and spread carry no frequency information and are both set by
    the noise bandwidth.

The discriminating measurement is therefore the two-cluster separation in
radians per SAMPLE -- an actual tone spacing -- together with whether that
separation survives as SNR degrades. A real tone offset is invariant to noise;
a noise-driven statistic is not.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not change the classifier, and it does not propose a threshold unless
the measured sets are actually separable. If they overlap, the honest output is
"overlap" -- the same discipline that produced the 0/12-vs-12/12 control in
scratch/fec_scheme_search.py.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/probe_fsk_phase_shape.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
from probe_fsk_vs_bpsk import make_fsk, classifier_features

RATES = (50_000, 100_000, 200_000, 400_000)
H_INDICES = (0.5, 1.0, 2.0, 4.0)
SEEDS = (7, 11)
NOISES = (0.02, 0.10, 0.25)


def tone_cluster_stats(d_phase, nbins=200):
    """Two-cluster separation in RADIANS PER SAMPLE, plus each cluster width.

    Two-tone structure is found by autocorrelating the phase histogram: a real
    two-tone signal produces two peaks separated by a definite offset, whereas
    a stationary phase produces one broad hump. Using the histogram's own
    second moment (variance) is not enough -- BPSK's noise hump can have a
    larger variance than a narrow 2-FSK's offset, which is failure mode (2)
    above restated in a new place.

    Returns (separation_rad_per_sample, min_width, ratio) or (0, inf, 0).
    """
    if d_phase.size < 256:
        return 0.0, float("inf"), 0.0

    hist, edges = np.histogram(d_phase, bins=nbins, range=(-np.pi, np.pi))
    centres = (edges[:-1] + edges[1:]) / 2.0
    binw = float(edges[1] - edges[0])
    hist = hist.astype(np.float64)
    if hist.sum() <= 0:
        return 0.0, float("inf"), 0.0

    # Smooth before peak-picking: an unsmoothed histogram of a narrow cluster
    # is a comb, and the top-2 bins of a comb are neighbours in one cluster.
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0])
    k /= k.sum()
    sm = np.convolve(hist, k, mode="same")

    peak = int(np.argmax(sm))
    if sm[peak] <= 0:
        return 0.0, float("inf"), 0.0

    # Second cluster = strongest peak at least 0.15 rad away from the first,
    # i.e. genuinely a different tone rather than the shoulder of the same one.
    min_sep_bins = max(2, int(round(0.15 / binw)))
    cand = [i for i in range(nbins)
            if abs(i - peak) >= min_sep_bins and sm[i] > 0.25 * sm[peak]]
    if not cand:
        # Single cluster: measure its width and report zero separation. This is
        # the BPSK / CW / noise case and it must come back as "not two-tone".
        return 0.0, _width(hist, centres, centres[peak]), 0.0

    peak2 = max(cand, key=lambda i: sm[i])
    sep = abs(float(centres[peak] - centres[peak2]))
    w1 = _width(hist, centres, centres[peak])
    w2 = _width(hist, centres, centres[peak2])
    wmin = min(w1, w2)
    ratio = sep / wmin if wmin > 0 else float("inf")
    return sep, wmin, ratio


def _width(hist, centres, centre, frac=0.68):
    """Half-width of the cluster at `centre`, as a standard deviation."""
    near = np.abs(np.angle(np.exp(1j * (centres - centre)))) < np.pi / 2
    w = hist[near]
    if w.sum() <= 0:
        return float("inf")
    c = centres[near]
    mu = float(np.sum(c * w) / np.sum(w))
    var = float(np.sum(((c - mu) ** 2) * w) / np.sum(w))
    return float(np.sqrt(max(var, 0.0)))


def features(sig):
    """Everything the classifier would need, measured from the signal alone."""
    amp_std, f_std = classifier_features(sig)
    d_phase = np.angle(sig[1:] * np.conj(sig[:-1]))
    sep, wmin, ratio = tone_cluster_stats(d_phase)
    return amp_std, f_std, sep, wmin, ratio


print("=" * 118)
print("PHASE-SHAPE TEST -- absolute tone separation vs phase noise floor")
print("=" * 118)
print("Columns:  amp_std / f_std / cluster separation (rad/sample) /")
print("          min cluster width (rad/sample) / separation-to-width ratio")
print()
print("A REAL 2-FSK should show separation >> width. A BPSK should show")
print("separation ~ 0 (one stationary phase, not two tones).")
print()

print("-" * 118)
print("BPSK -- one carrier, so there must be NO two-tone structure")
print("-" * 118)
print(f"{'R_s':>8} {'noise':>6} | {'amp_std':>8} {'f_std':>7} "
      f"{'sep':>8} {'width':>8} {'sep/width':>10}")
print("-" * 118)
bpsk_rows = []
for rate in RATES:
    for noise in NOISES:
        acc = []
        for seed in SEEDS:
            sig, sps, _, _ = make_known("BPSK", rate, seed=seed, noise=noise)
            acc.append(features(sig))
        a = float(np.mean([x[0] for x in acc]))
        f = float(np.mean([x[1] for x in acc]))
        s = float(np.mean([x[2] for x in acc]))
        w = float(np.mean([x[3] for x in acc]))
        r = float(np.mean([x[4] for x in acc]))
        bpsk_rows.append((rate, noise, s, r))
        print(f"{rate/1e3:>6.0f}k {noise:>6.2f} | {a:>8.4f} {f:>7.4f} "
              f"{s:>8.4f} {w:>8.4f} {r:>10.2f}")

print()
print("-" * 118)
print("2-FSK -- two tones, so there MUST be two-tone structure")
print("-" * 118)
print(f"{'R_s':>8} {'h':>4} {'dev':>7} {'noise':>6} | {'sep':>8} {'width':>8} "
      f"{'sep/width':>10} {'expected':>10}")
print("-" * 118)
fsk_rows = []
for rate in RATES:
    for h in H_INDICES:
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        # The expected differential phase per sample for a tone at dev/2:
        # omega = 2*pi*f/FS, and the spacing between the two tones is `dev`.
        expected = 2 * np.pi * dev / FS
        for noise in NOISES:
            acc = []
            for seed in SEEDS:
                sig, sps = make_fsk(rate, dev, continuous_phase=True,
                                    seed=seed, noise=noise)
                acc.append(features(sig))
            s = float(np.mean([x[2] for x in acc]))
            w = float(np.mean([x[3] for x in acc]))
            r = float(np.mean([x[4] for x in acc]))
            fsk_rows.append((rate, h, noise, s, r))
            print(f"{rate/1e3:>6.0f}k {h:>4.1f} {dev/1e3:>6.0f}k {noise:>6.2f} | "
                  f"{s:>8.4f} {w:>8.4f} {r:>10.2f} {expected:>10.4f}")

# ---------------------------------------------------------------------------
print()
print("=" * 118)
print("SEPARABILITY -- is there a threshold that puts every 2-FSK above and every")
print("BPSK below, across ALL rates, indices and noise levels?")
print("=" * 118)
b_sep = [x[2] for x in bpsk_rows]
f_sep = [x[3] for x in fsk_rows]
b_ratio = [x[3] for x in bpsk_rows]
f_ratio = [x[4] for x in fsk_rows]

print(f"  cluster separation   BPSK max {max(b_sep):>8.4f}   "
      f"2-FSK min {min(f_sep):>8.4f}   "
      f"gap {'>0 SEPARABLE' if min(f_sep) > max(b_sep) else '<=0 OVERLAP'}")
print(f"  separation/width     BPSK max {max(b_ratio):>8.2f}   "
      f"2-FSK min {min(f_ratio):>8.2f}   "
      f"gap {'>0 SEPARABLE' if min(f_ratio) > max(b_ratio) else '<=0 OVERLAP'}")

print()
print("  Per-noise-level breakdown, separation only (rad/sample):")
print(f"  {'noise':>6} | {'BPSK max':>10} | {'2-FSK min':>10} | verdict")
print("  " + "-" * 56)
for noise in NOISES:
    b = [x[2] for x in bpsk_rows if abs(x[1] - noise) < 1e-9]
    f = [x[3] for x in fsk_rows if abs(x[2] - noise) < 1e-9]
    if not b or not f:
        continue
    ok = min(f) > max(b)
    print(f"  {noise:>6.2f} | {max(b):>10.4f} | {min(f):>10.4f} | "
          f"{'separated' if ok else 'OVERLAP - not separable at this noise'}")

print()
print("  Per-rate breakdown, separation only (rad/sample):")
print(f"  {'R_s':>8} | {'BPSK max':>10} | {'2-FSK min':>10} | verdict")
print("  " + "-" * 56)
for rate in RATES:
    b = [x[2] for x in bpsk_rows if x[0] == rate]
    f = [x[3] for x in fsk_rows if x[0] == rate]
    if not b or not f:
        continue
    ok = min(f) > max(b)
    print(f"  {rate/1e3:>6.0f}k | {max(b):>10.4f} | {min(f):>10.4f} | "
          f"{'separated' if ok else 'OVERLAP - not separable at this rate'}")

print()
print("=" * 118)
print("CONTROLS -- a statistic that fires on everything is worthless")
print("=" * 118)
t = np.arange(20000) / FS
cw = (0.9 * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)
rng = np.random.default_rng(5)
noise = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
         * 0.05).astype(np.complex64)
sig_q, _, _, _ = make_known("QPSK", 100_000, seed=7)
for name, sig in (("CW", cw), ("noise", noise), ("QPSK", sig_q)):
    a, f, s, w, r = features(sig)
    print(f"  {name:>8}: sep {s:>7.4f}  width {w:>7.4f}  sep/width {r:>7.2f}  "
          f"amp_std {a:>6.4f}  f_std {f:>6.4f}")
print()
print("  CW correctly shows sep 0 (single tone). QPSK must NOT be separable")
print("  from BPSK by a two-tone test -- it is not 2-FSK.")
print("=" * 118)
