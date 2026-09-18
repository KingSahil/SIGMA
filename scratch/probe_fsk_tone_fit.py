"""Can FSK be identified the SAME way 8PSK and 16QAM already are -- by EVM?

STOP AND READ THIS FIRST
------------------------
Three probes have now tried to separate BPSK from 2-FSK with a bespoke phase
statistic, and all three FAILED. The record, so it does not get retried:

  probe_fsk_vs_bpsk.py        claimed BPSK and 2-FSK share the classifier's
                              branch signature. REFUTED: a properly built BPSK
                              has amp_std 0.40-0.51, far from the 0.12 gate.

  probe_fsk_feature_space.py  swept rate x index x seed. Found the real
                              problem: `f_std` ranges overlap completely
                              (BPSK 0.47..1.38, 2-FSK 0.05..1.26) because it is
                              monotone in the modulation index.

  probe_fsk_phase_shape.py    tried absolute two-tone separation vs the phase
                              noise floor. FAILED in two distinct ways:
                                (a) OVERLAP at every rate and every noise level
                                    (BPSK max 0.39 >= 2-FSK min 0.00);
                                (b) the "measurement" was quantised to the
                                    histogram bin width -- it reported
                                    0.1571 / 0.3142 / 0.6283, i.e. exactly
                                    pi/20, pi/10, pi/5, which are the bin
                                    centres of a 200-bin histogram over
                                    (-pi, pi]. A statistic that can only take
                                    multiples of its own bin size is not
                                    measuring the signal.

WHY THE BESPOKE APPROACH KEEPS FAILING
--------------------------------------
Every one of them reduced the signal to a scalar and then looked for a gap in
that scalar. The gap is not there, because the underlying quantity -- tone
spacing -- is a CONTINUOUS parameter that ranges from 0 (a CW carrier, which is
2-FSK with zero deviation) through every value up to Nyquist. Any scalar
derived from it has a continuous range that BPSK's own statistics will sit
inside. This is not a tuning failure; it is a property of asking the wrong
question.

THE QUESTION THAT MIGHT WORK
----------------------------
This module already solves an equivalent problem for PSK/QAM without a
bespoke statistic: `classify_constellation` demodulates under EACH hypothesis
and keeps the one whose EVM says it explains the symbols. It is verified
144/144 with noise refused. There is no reason FSK has to be solved
differently -- an FSK demodulator can be run the same way, and its EVM compared
against BPSK's on the same samples.

The catch is that an FSK demodulator needs the tone spacing, which is the thing
being sought. That is a search, not a threshold: for each candidate spacing,
demodulate and score. This is the same shape as the FEC code search in
scratch/fec_scheme_search.py, including its central lesson -- a search over
candidates ALWAYS returns a winner, so a threshold and an explicit refusal are
what make the answer mean anything.

THE ESTIMATOR TESTED HERE (no demodulator required)
---------------------------------------------------
The instantaneous frequency of a 2-FSK takes exactly TWO values. A BPSK takes
one value (plus pi-radian phase jumps, which are AMPLITUDE sign changes, not
frequency changes). So:

  * For 2-FSK, the histogram of the instantaneous frequency is two narrow
    spikes, and the SPACING of those spikes is a real tone offset.
  * For BPSK, the instantaneous frequency is one narrow spike at the carrier
    offset.

The two-spike structure is assessed on the frequency axis, and the spread of
all nonzero occupancy around the pair is the third, less-used level. This is
reported as a three-level occupancy statistic rather than the binary
"two clusters or not" of the failed probe, so a BPSK cannot score well by
accident.

This script MEASURES. It does not modify the classifier and it does not assert
a threshold. If the sets overlap again, the output says so.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
from probe_fsk_vs_bpsk import make_fsk

RATES = (50_000, 100_000, 200_000)
H_INDICES = (1.0, 2.0, 4.0)
SEEDS = (7, 11)
NOISES = (0.02, 0.10, 0.25)


def inst_freq(sig):
    """Instantaneous frequency, in radians per sample.

    This is NOT the histogram of the same quantity the failed probe used. The
    difference matters and is the whole point of the retry: that probe took the
    histogram of the differential phase and looked for two clusters in it,
    which for a noise-driven phase produces a broad hump whose "clusters" move
    with the noise. Here the same samples are treated as a FREQUENCY axis and
    the question is how many distinct TONES are present and how far apart they
    are -- a property of the modulation, not of the noise, whenever the tones
    are far enough apart to resolve.
    """
    d = np.angle(sig[1:] * np.conj(sig[:-1]))
    return d


def tone_report(sig, nbins=512):
    """Fit a two-tone model to the instantaneous-frequency distribution.

    Returns (omega1, omega2, spacing, level3_share, resolvable).

    `level3_share` is the fraction of samples NOT explained by either of the
    two dominant tones. A clean 2-FSK drives it toward 0. A BPSK -- whose
    "frequency" is one tone plus pi-radian phase jumps, and those jumps smear
    the distribution -- leaves a large share in the tail, so a two-tone model
    fits it badly. That asymmetry is the discriminator; it is a GOODNESS OF FIT
    rather than a raw statistic, which is why it is not subject to the
    monotone-in-the-parameter failure of the previous three attempts.
    """
    if sig.size < 512:
        return 0.0, 0.0, 0.0, 1.0, False
    d = inst_freq(sig)
    hist, edges = np.histogram(d, bins=nbins, range=(-np.pi, np.pi))
    centres = (edges[:-1] + edges[1:]) / 2.0
    binw = float(edges[1] - edges[0])

    order = np.argsort(hist)[::-1]
    if hist[order[0]] == 0:
        return 0.0, 0.0, 0.0, 1.0, False

    i1 = int(order[0])
    # Second tone must be a real, separate peak: at least 4 bins away and
    # holding a meaningful share of the samples.
    i2 = None
    for i in order[1:]:
        if abs(i - i1) >= 4 and hist[i] >= 0.10 * hist[i1]:
            i2 = int(i)
            break
    if i2 is None:
        # One tone. That is CW or BPSK -- both single-tone in this view.
        return float(centres[i1]), float(centres[i1]), 0.0, 1.0, False

    # Assign every sample to the nearer of the two tones and count what is left
    # over. A genuine two-tone signal leaves almost nothing.
    o1, o2 = float(centres[i1]), float(centres[i2])
    dist1 = np.abs(np.angle(np.exp(1j * (d - o1))))
    dist2 = np.abs(np.angle(np.exp(1j * (d - o2))))
    near1 = dist1 <= dist2
    # A sample only counts as "explained" if it is within a small window of its
    # tone. The window is a fraction of the tone spacing, floored at 3 bins so
    # a very narrow spacing is still allowed to explain its own samples.
    spacing = abs(o1 - o2)
    window = max(3.0 * binw, 0.25 * spacing)
    explained = np.where(near1, dist1, dist2) <= window
    level3 = 1.0 - float(np.mean(explained))
    resolvable = spacing >= 4.0 * binw
    return o1, o2, spacing, level3, resolvable


print("=" * 116)
print("TWO-TONE GOODNESS-OF-FIT -- can an FSK hypothesis be SCORED, not thresholded?")
print("=" * 116)
print("A 2-FSK is two tones and nothing else, so its unexplained share must be")
print("near zero. A BPSK is one tone plus pi phase jumps, so a two-tone model")
print("fits it badly and leaves a large unexplained share.")
print()
print(f"{'signal':>30} {'R_s':>7} {'h':>4} {'noise':>6} | {'tone sep':>9} "
      f"{'unexplained':>12} {'expected dev':>13}")
print("-" * 116)


def expected_dev(dev):
    return 2 * np.pi * dev / FS


rows_bpsk = []
rows_fsk = []

for rate in RATES:
    for noise in NOISES:
        acc = [tone_report(make_known("BPSK", rate, seed=s, noise=noise)[0])
               for s in SEEDS]
        sep = float(np.mean([a[2] for a in acc]))
        lvl3 = float(np.mean([a[3] for a in acc]))
        rows_bpsk.append((rate, noise, sep, lvl3))
        print(f"{'BPSK':>30} {rate/1e3:>5.0f}k {'-':>4} {noise:>6.2f} | "
              f"{sep:>9.4f} {lvl3:>12.4f} {'0 (one tone)':>13}")

for rate in RATES:
    for h in H_INDICES:
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        for noise in NOISES:
            acc = [tone_report(make_fsk(rate, dev, continuous_phase=True,
                                        seed=s, noise=noise)[0])
                   for s in SEEDS]
            sep = float(np.mean([a[2] for a in acc]))
            lvl3 = float(np.mean([a[3] for a in acc]))
            rows_fsk.append((rate, h, noise, sep, lvl3))
            print(f"{'2-FSK cts':>30} {rate/1e3:>5.0f}k {h:>4.1f} {noise:>6.2f} | "
                  f"{sep:>9.4f} {lvl3:>12.4f} {expected_dev(dev):>13.4f}")

# ---------------------------------------------------------------------------
print()
print("=" * 116)
print("SEPARABILITY ON 'UNEXPLAINED SHARE' -- lower means 'better explained by two tones'")
print("=" * 116)
b = [r[3] for r in rows_bpsk]
f = [r[4] for r in rows_fsk]
print(f"  BPSK  unexplained share: min {min(b):.4f}  max {max(b):.4f}")
print(f"  2-FSK unexplained share: min {min(f):.4f}  max {max(f):.4f}")
gap = max(b) - min(f)
if min(f) > max(b):
    print(f"  -> SEPARABLE, gap {gap:.4f}. Every 2-FSK below every BPSK.")
else:
    print(f"  -> OVERLAP by {abs(gap):.4f}. Not separable by this statistic either.")

print()
print("  Per-rate:")
print(f"  {'R_s':>8} | {'BPSK max':>10} | {'2-FSK min':>10} | verdict")
print("  " + "-" * 56)
for rate in RATES:
    bb = [r[3] for r in rows_bpsk if r[0] == rate]
    ff = [r[4] for r in rows_fsk if r[0] == rate]
    if not bb or not ff:
        continue
    ok = min(ff) > max(bb)
    print(f"  {rate/1e3:>6.0f}k | {max(bb):>10.4f} | {min(ff):>10.4f} | "
          f"{'separated' if ok else 'OVERLAP'}")

print()
print("  Per-noise-level:")
print(f"  {'noise':>8} | {'BPSK max':>10} | {'2-FSK min':>10} | verdict")
print("  " + "-" * 56)
for noise in NOISES:
    bb = [r[3] for r in rows_bpsk if abs(r[1] - noise) < 1e-9]
    ff = [r[4] for r in rows_fsk if abs(r[2] - noise) < 1e-9]
    if not bb or not ff:
        continue
    ok = min(ff) > max(bb)
    print(f"  {noise:>8.2f} | {max(bb):>10.4f} | {min(ff):>10.4f} | "
          f"{'separated' if ok else 'OVERLAP'}")

# ---------------------------------------------------------------------------
print()
print("=" * 116)
print("CONTROLS -- the statistic must not fire on things that are not 2-FSK")
print("=" * 116)
t = np.arange(20000) / FS
cw = (0.9 * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)
rng = np.random.default_rng(5)
noise_only = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
              * 0.05).astype(np.complex64)
q, _, _, _ = make_known("QPSK", 100_000, seed=7)
o8, _, _, _ = make_known("8PSK", 100_000, seed=7)
q16, _, _, _ = make_known("16QAM", 100_000, seed=7)
for name, sig in (("CW", cw), ("noise", noise_only), ("QPSK", q),
                  ("8PSK", o8), ("16QAM", q16)):
    o1, o2, sep, lvl3, res = tone_report(sig)
    verdict = "would be called 2-FSK" if (lvl3 < max(b)) and res else "not 2-FSK"
    print(f"  {name:>8}: tone sep {sep:>7.4f}  unexplained {lvl3:>7.4f}  "
          f"resolvable {str(res):>5}  -> {verdict}")
print()
print("  These controls matter as much as the sweep: a statistic that calls QPSK")
print("  a two-tone signal is useless however well it separates BPSK from 2-FSK.")
print("=" * 116)
