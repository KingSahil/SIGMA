"""Does the parsimony classifier falsely accept signals that carry no symbols?

EVM alone is not a sufficient test. An unmodulated carrier is a single phase;
a BPSK slice can rotate that one point onto a constellation point and score
near-zero EVM, so "the constellation fits" would be reported for a signal that
carries no symbols at all. The same worry applies to an AM/ASK envelope, which
has one phase but many amplitudes.

This measures, for genuine CW / ASK / noise alongside the four real
modulations:
  - each hypothesis's EVM
  - the fraction of recovered symbols landing on the single most-used
    constellation point (a real modulation must spread across points)
so the guard can be set from data rather than guessed.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from verify_demod_all_mods import make_known, FS
import sigma_demod as sd

MODS = sd.CONSTELLATION_ORDER


def constellation(mod):
    if mod == "BPSK":
        return np.array([1 + 0j, -1 + 0j])
    if mod == "QPSK":
        return np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
    if mod == "8PSK":
        return np.exp(1j * 2 * np.pi * np.arange(8) / 8)
    lv = np.array([-3, -1, 1, 3], dtype=np.float64) / np.sqrt(10)
    return np.array([i + 1j * q for i in lv for q in lv])


def make_cw(n=20000, seed=3):
    t = np.arange(n) / FS
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * np.pi)
    return (0.9 * np.exp(1j * (2 * np.pi * 60_000 * t + ph))).astype(np.complex64)


def make_ask(n_symbols=1500, rate=100_000, seed=4):
    """Amplitude shift keying: one phase, many amplitudes."""
    rng = np.random.default_rng(seed)
    sps = int(round(FS / rate))
    amp = rng.choice([0.25, 1.0], n_symbols)
    up = np.zeros(n_symbols * sps)
    up[::sps] = amp
    h = sd.rrc_filter(sps, 0.35)
    shaped = np.convolve(up, h, mode="same")
    t = np.arange(len(shaped)) / FS
    shaped = shaped * np.exp(1j * 2 * np.pi * 60_000 * t)
    shaped += (rng.normal(0, 0.02, len(shaped))
               + 1j * rng.normal(0, 0.02, len(shaped)))
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64)


def make_noise(n=20000, seed=5):
    rng = np.random.default_rng(seed)
    return ((rng.normal(0, 1, n) + 1j * rng.normal(0, 1, n)) * 0.05).astype(np.complex64)


def concentration(res, mod):
    """Fraction of symbols landing on the single most-used constellation point."""
    if not res.locked or res.symbols is None:
        return float("nan")
    const = constellation(mod)
    idx = np.argmin(np.abs(res.symbols[:, None] - const[None, :]), axis=1)
    counts = np.bincount(idx, minlength=len(const))
    return float(counts.max() / len(idx))


SIGNALS = []
for mod in MODS:
    sig, sps, _, _ = make_known(mod, 100_000, seed=7)
    SIGNALS.append((mod, sig, sps))
SIGNALS.append(("CW", make_cw(), 10))
SIGNALS.append(("ASK", make_ask(), 10))
SIGNALS.append(("noise", make_noise(), 10))

print("=" * 100)
print("PARSIMONY CLASSIFIER vs SIGNALS WITH NO SYMBOLS")
print("=" * 100)
print(f"{'signal':>8} | " + " ".join(f"{m:>13}" for m in MODS) + " | "
      f"{'picked':>7} {'max-point share':>16}")
print("-" * 100)

for name, sig, sps in SIGNALS:
    evms = {}
    concs = {}
    for m in MODS:
        r = sd.demodulate(sig, FS, modulation=m, sps=sps)
        evms[m] = r.evm_percent if r.locked else float("inf")
        concs[m] = concentration(r, m)
    picked, _ = sd.classify_constellation(sig, FS, sps)

    cells = []
    for m in MODS:
        v = evms[m]
        if v == float("inf"):
            cells.append(f"{'--':>13}")
        else:
            c = concs[m]
            cells.append(f"{v:>6.1f}%/{c:>5.2f}" if not np.isnan(c)
                         else f"{v:>6.1f}%/{'--':>5}")
    # share of the chosen hypothesis
    if picked:
        r = sd.demodulate(sig, FS, modulation=picked, sps=sps)
        share = concentration(r, picked)
    else:
        share = float("nan")
    share_txt = "n/a" if np.isnan(share) else f"{share:.2f}"
    print(f"{name:>8} | " + " ".join(cells) + f" | {str(picked):>7} "
          f"{share_txt:>16}")

print("-" * 100)
print("Cells are 'EVM% / share of the most-used constellation point'.")
print("A REAL modulation spreads across points (share well below 1.0).")
print("CW concentrates on ONE point (share ~1.0) -- that is the guard.")
print("=" * 100)
