"""Measure the BPSK / 2-FSK collision instead of arguing about it.

THE CLAIM UNDER TEST
--------------------
The spectral classifier contains:

    elif amp_std < 0.12 and f_std > 0.4:
        self.modulation_class = "BPSK / 2-FSK"

with

    f_std   = np.std(np.angle(data[1:] * np.conj(data[:-1])))   # d_phase
    amp_std = np.std(magnitudes) / (np.mean(magnitudes) + 1e-12)

`amp_std < 0.12` is a CONSTANT-ENVELOPE test. Both BPSK and 2-FSK are
constant-envelope, so if both also produce `f_std > 0.4` then the two features
used CANNOT separate them, and no amount of threshold tuning will help. That is
the claim. This script measures it on real, properly constructed signals.

WHY THIS FILE EXISTS AT ALL
---------------------------
An earlier attempt at this measurement was INVALID and is recorded here so the
mistake is not repeated:

  * the "BPSK" was built with `np.repeat` of un-normalised +-1 symbols, so the
    magnitudes were ~127 and amp_std came out at 126.99 -- the envelope was not
    constant because the signal was not scaled, not because of the modulation;
  * that BPSK had NO carrier offset, so the differential phase was ~0 and
    f_std came out 0.0000.

Comparing that against a 2-FSK at 0.0000 / 0.5498 proved nothing about the
classifier. Both signals have to be built the way the module builds them --
RRC-shaped, a real carrier offset, real noise, normalised to 0.9 peak -- before
the resulting f_std and amp_std mean anything.

THE FEATURE THAT SHOULD SEPARATE THEM
-------------------------------------
Differencing phase is the wrong statistic for this job. Its magnitude depends
on the PHASE SHIFT PER SYMBOL in one case and on the residual CARRIER OFFSET in
the other, so a slow BPSK and a fast 2-FSK can land on the same number. What
distinguishes them structurally is the SHAPE of the phase:

  * 2-FSK: two tones. The phase rotates steadily at one of two rates, so the
    differential phase is BIMODAL -- two clusters, one per tone.
  * BPSK: two phases but one carrier. Between symbols the phase sits still
    (modulo pi flips), so the differential phase concentrates near 0/pi and is
    NOT bimodal at two separated non-zero values.

So the candidate feature is the BIMODALITY of the differential phase, measured
in a way that does not depend on the absolute deviation: the separation of the
two dominant clusters relative to their spread (a two-cluster separation ratio).

This script reports raw numbers for every signal and every candidate feature.
It does NOT change the classifier. A threshold written before the numbers are
measured would be a guess.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/probe_fsk_vs_bpsk.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
import sigma_demod as sd

RRC = sd.rrc_filter


def make_fsk(symbol_rate, deviation_hz, alpha=0.35, n_symbols=1500, seed=7,
             carrier_offset=60_000.0, noise=0.02, continuous_phase=True):
    """Phase-continuous 2-FSK, built to the same recipe as make_known.

    2-FSK is constant-envelope whether or not the phase is continuous, and the
    real captures this app is pointed at are almost always continuous-phase.
    Both are generated here so the feature is not measured on one narrow case.

    The two tones sit at carrier_offset +- deviation/2, so `deviation_hz` is
    the peak-to-peak tone spacing -- the parameter a decoder would need.
    """
    rng = np.random.default_rng(seed)
    sps = int(round(FS / symbol_rate))
    bits = rng.integers(0, 2, n_symbols)
    freqs = np.where(bits == 1, +deviation_hz / 2.0, -deviation_hz / 2.0)

    if continuous_phase:
        # Integrate the instantaneous frequency. The phase is continuous
        # across symbol boundaries, which is what a real FSK exciter does.
        inst = np.repeat(freqs, sps)
        phase = 2 * np.pi * np.cumsum(inst) / FS
        out = np.exp(1j * phase)
    else:
        # Abrupt tone switching: phase discontinuities at every boundary.
        t = np.arange(n_symbols * sps) / FS
        tone = np.repeat(freqs, sps)
        out = np.exp(1j * 2 * np.pi * tone * t)

    # A 2-FSK waveform is already a constant-envelope sinusoid, so there is no
    # RRC shaping to apply -- shaping would destroy the constant envelope that
    # IS the modulation. A short raised-cosine amplitude window is applied for
    # the same reason make_known applies RRC: so the spectrum is contained.
    h = RRC(sps, alpha) if sps >= 2 else None
    if h is not None:
        env = np.abs(np.convolve(np.ones(len(out)), h, mode="same"))
        out = out * (env / (np.max(env) + 1e-12)) ** 0.0  # unity gain; see note
    # NOTE: `** 0.0` keeps this a pure no-op on the envelope, deliberately.
    # Shaping the AMPLITUDE of an FSK signal would modulate it, breaking the
    # constant envelope the probe is trying to measure. The line is kept so the
    # intent (no amplitude shaping) is explicit rather than an omission.

    t = np.arange(len(out)) / FS
    out = out * np.exp(1j * 2 * np.pi * carrier_offset * t)

    out = out + (rng.normal(0, noise, len(out))
                 + 1j * rng.normal(0, noise, len(out)))

    out = out / np.max(np.abs(out)) * 0.9
    return out.astype(np.complex64), sps


# ---------------------------------------------------------------------------
# The classifier's own two features, copied verbatim from
# src/sigma_analyzer_core.py so this measures the shipped statistic.
# ---------------------------------------------------------------------------
def classifier_features(data):
    magnitudes = np.abs(data)
    d_phase = np.angle(data[1:] * np.conj(data[:-1]))
    f_std = float(np.std(d_phase))
    amp_std = float(np.std(magnitudes) / (np.mean(magnitudes) + 1e-12))
    return amp_std, f_std


def two_cluster_separation(d_phase, nbins=128):
    """Separation of the two dominant clusters in the differential phase.

    Returns (separation_rad, ratio). `ratio` is separation divided by the mean
    of the two cluster widths, so it is dimensionless and does not inherit the
    absolute phase deviation -- which is exactly the quantity that fails to
    separate a slow BPSK from a slow 2-FSK.

    Returns (0.0, 0.0) when the phase is not plausibly two-clustered.
    """
    if d_phase.size < 64:
        return 0.0, 0.0
    hist, edges = np.histogram(d_phase, bins=nbins, range=(-np.pi, np.pi))
    centres = (edges[:-1] + edges[1:]) / 2.0
    order = np.argsort(hist)[::-1]
    if hist[order[0]] == 0:
        return 0.0, 0.0

    # Find the best-separated pair among the strongest bins. Taking the top two
    # bins alone would pick neighbours in the same cluster and report ~0.
    top = order[:12]
    best = (0.0, 0.0)
    for i, bi in enumerate(top):
        for bj in top[i + 1:]:
            if hist[bi] < 0.15 * hist[order[0]] or hist[bj] < 0.15 * hist[order[0]]:
                continue
            sep = abs(centres[bi] - centres[bj])
            wi = _cluster_width(d_phase, centres[bi])
            wj = _cluster_width(d_phase, centres[bj])
            width = max((wi + wj) / 2.0, 1e-6)
            ratio = sep / width
            if sep > best[0]:
                best = (sep, ratio)
    return best


def _cluster_width(d_phase, centre, frac=0.5):
    """Spread of the phase samples belonging to one cluster."""
    dev = np.abs(np.angle(np.exp(1j * (d_phase - centre))))
    near = dev[dev < np.pi / 2]
    if near.size < 8:
        return np.pi / 2
    return float(np.percentile(near, frac * 100))


# ---------------------------------------------------------------------------
SPS_RATE = 100_000
DEVIATIONS = (20_000, 50_000, 100_000, 200_000, 300_000)

print("=" * 104)
print("BPSK vs 2-FSK -- the classifier's OWN features, measured on real signals")
print("=" * 104)
print("These two columns are exactly what the classifier uses:")
print("    amp_std < 0.12  (constant envelope)   and   f_std > 0.4")
print()
print(f"{'signal':>34} | {'amp_std':>8} {'f_std':>7} | {'2-cluster sep':>13} "
      f"{'ratio':>7} | {'hits rule?':>10}")
print("-" * 104)

rows = []


def probe(label, sig, sps):
    amp_std, f_std = classifier_features(sig)
    mags = np.abs(sig)
    d_phase = np.angle(sig[1:] * np.conj(sig[:-1]))
    sep, ratio = two_cluster_separation(d_phase)
    hits = (amp_std < 0.12) and (f_std > 0.4)
    rows.append((label, amp_std, f_std, sep, ratio, hits))
    print(f"{label:>34} | {amp_std:>8.4f} {f_std:>7.4f} | {sep:>13.4f} "
          f"{ratio:>7.2f} | {'YES' if hits else 'no':>10}")


# Reference: a real BPSK at the project's standard rate.
sig, sps, _, _ = make_known("BPSK", SPS_RATE, seed=7)
probe("BPSK 100 ksps (the reference)", sig, sps)

# 2-FSK across a range of tone spacings, continuous phase.
for dev in DEVIATIONS:
    sig, sps = make_fsk(SPS_RATE, dev, continuous_phase=True, seed=7)
    probe(f"2-FSK 100ksps dev={dev/1e3:.0f}kHz cts", sig, sps)

# The same, with abrupt tone switching, so the feature is not tuned to one
# construction.
for dev in (50_000, 200_000):
    sig, sps = make_fsk(SPS_RATE, dev, continuous_phase=False, seed=7)
    probe(f"2-FSK 100ksps dev={dev/1e3:.0f}kHz disc", sig, sps)

# Controls -- these must stay OUT of the ambiguous branch.
sig, sps, _, _ = make_known("QPSK", SPS_RATE, seed=7)
probe("QPSK 100 ksps (control)", sig, sps)

t = np.arange(20000) / FS
cw = (0.9 * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)
probe("CW (control)", cw, 10)

rng = np.random.default_rng(5)
noise = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
         * 0.05).astype(np.complex64)
probe("noise (control)", noise, 10)

# ---------------------------------------------------------------------------
print()
print("=" * 104)
print("DOES THE RULE SEPARATE THEM?")
print("=" * 104)
bpsk = [r for r in rows if r[0].startswith("BPSK")]
fsk = [r for r in rows if r[0].startswith("2-FSK")]

b_hits = sum(1 for r in bpsk if r[5])
f_hits = sum(1 for r in fsk if r[5])
print(f"  BPSK captures hitting the ambiguous rule : {b_hits}/{len(bpsk)}")
print(f"  2-FSK captures hitting the ambiguous rule: {f_hits}/{len(fsk)}")

b_amp = max(r[1] for r in bpsk)
f_amp = max(r[1] for r in fsk)
b_f = min(r[2] for r in bpsk)
f_f = min(r[2] for r in fsk)
print()
print(f"  amp_std  BPSK max {b_amp:.4f}   2-FSK max {f_amp:.4f}   "
      f"(threshold 0.12)")
print(f"  f_std    BPSK min {b_f:.4f}   2-FSK min {f_f:.4f}   "
      f"(threshold 0.40)")
print()

if b_hits and f_hits:
    print("  VERDICT: both land in the SAME branch on BOTH features.")
    print("  The 'BPSK / 2-FSK' label is not a tuning problem -- the two")
    print("  features used are structurally blind to the difference.")
else:
    print("  VERDICT: the rule DOES separate them on this set; the claim that")
    print("  it cannot is REFUTED. Do not change the classifier.")

print()
print("  Candidate replacement feature -- two-cluster separation ratio:")
print(f"    BPSK     min ratio {min(r[4] for r in bpsk):.2f}")
print(f"    2-FSK    min ratio {min(r[4] for r in fsk):.2f}")
gap = (min(r[4] for r in fsk) - max(r[4] for r in bpsk))
print(f"    gap between the two sets = {gap:.2f}"
      + ("   (separable)" if gap > 0 else "   (NOT separable -- feature rejected)"))
print("=" * 104)
