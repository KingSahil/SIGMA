"""Score the SHIPPED FSK estimator and demodulator against known bits.

WHY THIS EXISTS
---------------
`scratch/probe_fsk_snr_realistic.py` established that a two-tone goodness-of-fit
separates 2-FSK from every other modulation with no overlap at this project's
operating point. That was a PROBE: it measured a statistic and proposed a
threshold. It did not prove the shipped code works.

This scores `src/sigma_demod.py` directly -- `estimate_fsk` and
`demodulate_fsk` -- the same discipline as `verify_demod_all_mods.py` scoring
the real `demodulate` rather than a scratch copy. A probe proves what the fix
WOULD do; only this proves what the module DOES.

WHAT IS SCORED
--------------
1. Detection: is a 2-FSK called two-tone, and is everything else NOT?
   The second half is the one that matters -- a detector that says yes to
   everything is worthless. This is the control that killed three earlier
   attempts, so it is scored first and hardest.
2. Bit accuracy: recovered bits against the TRANSMITTED bits, over a sweep of
   rate x modulation index x seed, with the constellation-phase ambiguity
   resolved by trying both tone-to-bit conventions (see `score_bits`).
3. The refusal path: noise, CW and each PSK/QAM must be DECLINED by
   `demodulate_fsk`, not decoded into plausible bits.
4. The separation reported versus the separation actually present.

HONEST LIMITS, STATED UP FRONT
------------------------------
The amplitude generator cannot produce phase-discontinuous FSK with a
controlled envelope, so the burst-discontinuity case is tested by generating it
a different way (`make_fsk_discrete`). And the demodulator assumes the tone
ordering maps to bit 1/0 in ONE convention; a real system carries that
convention out of band. `score_bits` searches both, and reports the search --
without it a correct demodulator scores ~50% and looks broken.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/verify_fsk_demod.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
from probe_fsk_vs_bpsk import make_fsk
from sigma_demod import estimate_fsk, demodulate_fsk

# The generators apply a 60 kHz carrier offset, so the two tones sit at
# 60 kHz +- dev/2 -- NOT at +-dev/2 around zero. Diagnostics that forget this
# pick up a constant bias of 2*pi*60000/FS = 0.377 rad/sample, which is large
# enough to make a working demodulator look broken. Measured: an earlier
# diagnostic reported a uniform 0.377 error at EVERY sample offset within the
# symbol, which is the signature of a missing constant, not of a timing
# problem.
CARRIER_OFFSET_RAD = 2 * np.pi * 60_000.0 / FS


def make_fsk_discrete(symbol_rate, deviation_hz, alpha=0.35, n_symbols=1500,
                      seed=7, carrier_offset=60_000.0, noise=0.02):
    """2-FSK with ABRUPT tone switching, so the estimator is not tuned to the
    phase-continuous case only.

    Returns (samples, sps, bits) so the transmitted bits are known.
    """
    rng = np.random.default_rng(seed)
    sps = int(round(FS / symbol_rate))
    bits = rng.integers(0, 2, n_symbols)
    freqs = np.where(bits == 1, +deviation_hz / 2.0, -deviation_hz / 2.0)
    t = np.arange(n_symbols * sps) / FS
    tone = np.repeat(freqs, sps)
    out = np.exp(1j * 2 * np.pi * tone * t)
    out = out * np.exp(1j * 2 * np.pi * carrier_offset * t)
    out = out + (rng.normal(0, noise, len(out))
                 + 1j * rng.normal(0, noise, len(out)))
    return (out / np.max(np.abs(out)) * 0.9).astype(np.complex64), sps, bits


def make_fsk_with_bits(symbol_rate, deviation_hz, seed=7, **kw):
    """Continuous-phase 2-FSK WITH the transmitted bits returned.

    `probe_fsk_vs_bpsk.make_fsk` does not return its bits, and bit accuracy
    cannot be scored without them. Rather than modify the probe (which is a
    frozen failure record for another experiment), the generator is repeated
    here with the same recipe and the bits exposed.
    """
    rng = np.random.default_rng(seed)
    sps = int(round(FS / symbol_rate))
    bits = rng.integers(0, 2, 1500)
    freqs = np.where(bits == 1, +deviation_hz / 2.0, -deviation_hz / 2.0)
    inst = np.repeat(freqs, sps)
    phase = 2 * np.pi * np.cumsum(inst) / FS
    out = np.exp(1j * phase)
    t = np.arange(len(out)) / FS
    out = out * np.exp(1j * 2 * np.pi * 60_000.0 * t)
    noise = kw.get("noise", 0.02)
    out = out + (rng.normal(0, noise, len(out))
                 + 1j * rng.normal(0, noise, len(out)))
    return (out / np.max(np.abs(out)) * 0.9).astype(np.complex64), sps, bits


def score_bits(recovered, transmitted, max_shift=8):
    """Best bit accuracy over the tone-to-bit convention and a small offset.

    A 2-FSK receiver cannot know from the signal alone which tone means 1;
    that convention is carried out of band (in a standard, or a preamble).
    Scoring without allowing for it would measure the missing convention
    rather than the demodulator. Both conventions are tried and the better is
    reported, exactly as the PSK scorer searches the rotational symmetry.

    An inverted bitstream is a correct demodulation with the wrong convention,
    so `inverted` is reported separately rather than silently folded in.
    """
    r = np.asarray(recovered, dtype=np.uint8).ravel()
    t = np.asarray(transmitted, dtype=np.uint8).ravel()
    if r.size == 0:
        return 0.0, False, 0
    best = (0.0, False, 0)
    for invert in (False, True):
        cand = (1 - r) if invert else r
        for shift in range(max_shift + 1):
            n = min(cand.size - shift, t.size)
            if n < 150:
                continue
            acc = float(np.mean(cand[shift:shift + n] == t[:n]))
            if acc > best[0]:
                best = (acc, invert, shift)
    return best


print("=" * 96)
print("SHIPPED FSK DEMODULATOR -- scored against known transmitted bits")
print("=" * 96)
print("Uses src/sigma_demod.py: estimate_fsk() and demodulate_fsk().")
print()

# ---------------------------------------------------------------------------
print("-" * 96)
print("TEST 1. DETECTION -- 2-FSK must be accepted, everything else REFUSED")
print("-" * 96)
print("This is the control that killed three earlier feature attempts. A")
print("detector that accepts a PSK capture is worthless however well it finds")
print("2-FSK, so the false-positive side is scored first.")
print()
print(f"{'signal':>24} {'R_s':>7} {'h':>5} | {'is_two_tone':>12} "
      f"{'unexplained':>12} {'verdict':>10}")
print("-" * 96)

false_pos = []
true_pos = 0
total_fsk = 0

for rate in (50_000, 100_000, 200_000):
    for h in (1.0, 2.0, 4.0):
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        sig, sps, _ = make_fsk_with_bits(rate, dev, seed=7)
        est = estimate_fsk(sig)
        total_fsk += 1
        true_pos += int(est["is_two_tone"])
        v = "accepted" if est["is_two_tone"] else "MISSED"
        print(f"{'2-FSK cts':>24} {rate/1e3:>5.0f}k {h:>5.1f} | "
              f"{str(est['is_two_tone']):>12} {est['unexplained']:>12.4f} "
              f"{v:>10}")

for rate in (50_000, 100_000, 200_000):
    for h in (1.0, 2.0):
        dev = h * rate / 2.0
        sig, sps, _ = make_fsk_discrete(rate, dev, seed=7)
        est = estimate_fsk(sig)
        total_fsk += 1
        true_pos += int(est["is_two_tone"])
        v = "accepted" if est["is_two_tone"] else "MISSED"
        print(f"{'2-FSK disc':>24} {rate/1e3:>5.0f}k {h:>5.1f} | "
              f"{str(est['is_two_tone']):>12} {est['unexplained']:>12.4f} "
              f"{v:>10}")

print()
print(f"  2-FSK accepted: {true_pos}/{total_fsk}")
print()
print("  Controls (each MUST come back is_two_tone=False):")
for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    for rate in (50_000, 100_000, 200_000):
        sig, sps, _, _ = make_known(mod, rate, seed=7)
        est = estimate_fsk(sig)
        if est["is_two_tone"]:
            false_pos.append((mod, rate, est))
        flag = "FALSE POSITIVE" if est["is_two_tone"] else "correctly refused"
        print(f"{mod:>24} {rate/1e3:>5.0f}k {'-':>5} | "
              f"{str(est['is_two_tone']):>12} {est['unexplained']:>12.4f} "
              f"{flag:>17}")

t = np.arange(20000) / FS
cw = (0.9 * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)
est = estimate_fsk(cw)
if est["is_two_tone"]:
    false_pos.append(("CW", 0, est))
print(f"{'CW':>24} {'-':>7} {'-':>5} | {str(est['is_two_tone']):>12} "
      f"{est['unexplained']:>12.4f} "
      f"{('FALSE POSITIVE' if est['is_two_tone'] else 'correctly refused'):>17}")

rng = np.random.default_rng(11)
noise = ((rng.normal(0, 1, 20000) + 1j * rng.normal(0, 1, 20000))
         * 0.05).astype(np.complex64)
est = estimate_fsk(noise)
if est["is_two_tone"]:
    false_pos.append(("noise", 0, est))
print(f"{'noise':>24} {'-':>7} {'-':>5} | {str(est['is_two_tone']):>12} "
      f"{est['unexplained']:>12.4f} "
      f"{('FALSE POSITIVE' if est['is_two_tone'] else 'correctly refused'):>17}")

print()
print(f"  FALSE POSITIVES: {len(false_pos)} "
      f"({'clean' if not false_pos else 'PROBLEM -- ' + str(false_pos)})")

# ---------------------------------------------------------------------------
print()
print("=" * 96)
print("TEST 2. BIT ACCURACY -- recovered bits vs transmitted bits")
print("=" * 96)
print("The tone-to-bit convention is unknown from the signal alone, so both")
print("are searched and the better reported. An inverted bitstream is a")
print("correct demodulation with the opposite convention.")
print()
print(f"{'R_s':>7} {'h':>5} {'dev':>8} {'kind':>6} | {'sps':>4} {'sym':>5} "
      f"{'bits':>5} {'accuracy':>9} {'inverted':>9} {'margin':>7}")
print("-" * 96)

rows = []
for rate in (50_000, 100_000, 200_000, 400_000):
    for h in (1.0, 2.0, 4.0):
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        for kind, gen in (("cts", make_fsk_with_bits),
                          ("disc", make_fsk_discrete)):
            if kind == "disc" and h > 2.0:
                continue
            sig, sps, tx_bits = gen(rate, dev, seed=7)
            est = estimate_fsk(sig)
            r = demodulate_fsk(sig, FS, fsk=est, sps=sps)
            if not r.locked:
                rows.append((rate, h, kind, None, None, r.reason))
                print(f"{rate/1e3:>5.0f}k {h:>5.1f} {dev/1e3:>7.0f}k {kind:>6} | "
                      f"{sps:>4} {'--':>5} {'--':>5} {'NO LOCK':>9} "
                      f"{'--':>9} {'--':>7}")
                continue
            acc, inverted, shift = score_bits(r.bits, tx_bits)
            margin = 100.0 - r.evm_percent
            rows.append((rate, h, kind, acc, r, None))
            print(f"{rate/1e3:>5.0f}k {h:>5.1f} {dev/1e3:>7.0f}k {kind:>6} | "
                  f"{sps:>4} {r.n_symbols:>5} {len(r.bits):>5} "
                  f"{acc*100:>8.2f}% {str(inverted):>9} {margin:>6.1f}%")

print("-" * 96)
got = [r for r in rows if r[3] is not None]
if got:
    accs = [r[3] for r in got]
    perfect = sum(1 for a in accs if a >= 0.9999)
    print(f"  Demodulated {len(got)}/{len(rows)} cases; "
          f"{perfect} perfectly; mean {np.mean(accs)*100:.2f}%; "
          f"worst {np.min(accs)*100:.2f}%")
    weak = [(r, ) for r in got if r[3] < 0.9999]
    if weak:
        print("\n  NOT PERFECT (disclosed, not hidden):")
        for (rate, h, kind, acc, res, _), in weak:
            print(f"    {rate/1e3:>5.0f}k h={h:<5.1f} {kind:>4}  "
                  f"{acc*100:6.2f}%  ({res.reason})")
    else:
        print("  Every demodulated case recovered the transmitted bits exactly.")
refused = [r for r in rows if r[3] is None]
if refused:
    print("\n  REFUSED (declining is correct when it cannot decide):")
    for rate, h, kind, _, _, reason in refused:
        print(f"    {rate/1e3:>5.0f}k h={h:<5.1f} {kind:>4}  {reason}")

# ---------------------------------------------------------------------------
print()
print("=" * 96)
print("TEST 3. THE REFUSAL PATH -- must DECLINE, not decode")
print("=" * 96)
print("A demodulator that produces plausible bits from noise is the exact")
print("failure this module exists to avoid.")
print()
declined = 0
total_ref = 0
for name, sig, sps in (
        ("noise", noise, 10),
        ("CW", cw, 10),
        *[(m, make_known(m, 100_000, seed=7)[0], 10)
          for m in ("BPSK", "QPSK", "8PSK", "16QAM")]):
    r = demodulate_fsk(sig, FS, sps=sps)
    total_ref += 1
    declined += int(not r.locked)
    verdict = "declined" if not r.locked else f"LOCKED {len(r.bits)} bits"
    print(f"  {name:>6}: {verdict}")
    if not r.locked:
        print(f"          reason: {r.reason}")
print()
print(f"  Declined {declined}/{total_ref} "
      f"({'correct' if declined == total_ref else 'PROBLEM'})")

# ---------------------------------------------------------------------------
print()
print("=" * 96)
print("TEST 4. DOES THE REPORTED SPACING MATCH THE TRUE SPACING?")
print("=" * 96)
print("The estimator's other output is the tone deviation the demodulator")
print("needs, so it is not enough for it to detect -- the NUMBER must be right.")
print()
print(f"{'R_s':>7} {'h':>5} | {'true sep':>10} {'reported':>10} {'error':>10} "
      f"{'relerr':>9}")
print("-" * 96)
sep_errs = []
for rate in (50_000, 100_000, 200_000, 400_000):
    for h in (1.0, 2.0, 4.0):
        dev = h * rate / 2.0
        if dev > 0.45 * FS:
            continue
        expected = 2 * np.pi * dev / FS
        sig, sps, _ = make_fsk_with_bits(rate, dev, seed=7)
        est = estimate_fsk(sig)
        got_sep = est["separation"]
        err = got_sep - expected
        sep_errs.append(abs(err))
        print(f"{rate/1e3:>5.0f}k {h:>5.1f} | {expected:>10.4f} "
              f"{got_sep:>10.4f} {err:>+10.4f} "
              f"{abs(err)/expected*100:>8.2f}%")
print("-" * 96)
print(f"  Mean absolute error: {np.mean(sep_errs):.5f} rad/sample  "
      f"(max {np.max(sep_errs):.5f})")
print("=" * 96)
