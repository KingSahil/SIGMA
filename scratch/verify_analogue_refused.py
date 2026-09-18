"""Would the parsimony classifier wrongly accept analogue signals?

16QAM is misclassified as "AM / ASK" by the spectral classifier because its
envelope varies, so the gate has to let AM/ASK through to the demodulator-based
classifier. That is only safe if genuine analogue signals are still refused.

The `_occupies_multiple_phases` guard should handle amplitude-only and
single-carrier signals (one phase). The worry is FM: it has a constant envelope
but a continuously varying phase, which is exactly what a PSK slicer looks for.

This tests against the REAL bundled FM/RDS capture as well as synthetic AM, ASK,
CW and audio baseband, so the decision is made on evidence.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from verify_demod_all_mods import make_known, FS
import sigma_demod as sd

MODS = sd.CONSTELLATION_ORDER


def read_iq(path, count=200_000):
    return np.fromfile(path, dtype=np.complex64, count=count)


def make_am(n=20000, seed=6):
    """Amplitude modulation: one carrier, envelope varies at a low tone."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FS
    env = 0.5 + 0.45 * np.sin(2 * np.pi * 5_000 * t)
    return (env * np.exp(1j * 2 * np.pi * 60_000 * t)).astype(np.complex64)


def make_cw(n=20000, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FS
    ph = rng.uniform(0, 2 * np.pi)
    return (0.9 * np.exp(1j * (2 * np.pi * 60_000 * t + ph))).astype(np.complex64)


def make_audio(n=20000, seed=7):
    """Real-valued baseband audio packed as complex -- a common input mistake."""
    rng = np.random.default_rng(seed)
    a = 0.5 * np.sin(2 * np.pi * 1000 * np.arange(n) / FS)
    a += 0.05 * rng.normal(0, 1, n)
    return a.astype(np.complex64)


def make_ask(n_symbols=1500, rate=100_000, seed=4):
    rng = np.random.default_rng(seed)
    sps = int(round(FS / rate))
    amp = rng.choice([0.25, 1.0], n_symbols)
    up = np.zeros(n_symbols * sps)
    up[::sps] = amp
    shaped = np.convolve(up, sd.rrc_filter(sps, 0.35), mode="same")
    t = np.arange(len(shaped)) / FS
    shaped = shaped * np.exp(1j * 2 * np.pi * 60_000 * t)
    return (shaped / np.max(np.abs(shaped)) * 0.9).astype(np.complex64)


CASES = [
    ("real FM/RDS", os.path.join(ROOT, "data", "iq", "fm_rds_250k_1Msamples.iq"), 10),
    ("synthetic AM", None, 10),
    ("synthetic ASK", None, 10),
    ("synthetic CW", None, 10),
    ("audio baseband", None, 10),
]

print("=" * 92)
print("WOULD THE CLASSIFIER ACCEPT ANALOGUE SIGNALS?")
print("=" * 92)
print(f"{'signal':>16} | " + " ".join(f"{m:>11}" for m in MODS) + " | {'picked':>8}")
print("-" * 92)

makers = {"synthetic AM": make_am, "synthetic ASK": make_ask,
          "synthetic CW": make_cw, "audio baseband": make_audio}

bad = []
for name, path, sps in CASES:
    if path and os.path.exists(path):
        sig = read_iq(path)
    elif path:
        print(f"{name:>16} | SKIPPED (missing {os.path.basename(path)})")
        continue
    else:
        sig = makers[name]()

    evms = {}
    for m in MODS:
        r = sd.demodulate(sig, FS, modulation=m, sps=sps)
        if r.locked and sd._occupies_multiple_phases(r, sd.constellation_for(m)):
            evms[m] = r.evm_percent
        else:
            evms[m] = float("inf")

    picked, _ = sd.classify_constellation(sig, FS, sps)
    cells = [("--" if evms[m] == float("inf") else f"{evms[m]:.1f}%")
             for m in MODS]
    print(f"{name:>16} | " + " ".join(f"{c:>11}" for c in cells)
          + f" | {str(picked):>8}")
    if picked is not None:
        bad.append((name, picked))

print("-" * 92)
if bad:
    print("ACCEPTED AS DIGITAL (these are false positives):")
    for name, picked in bad:
        print(f"  {name} -> {picked}")
else:
    print("Every analogue signal was correctly REFUSED.")
print("=" * 92)

# And the four real modulations must still be identified.
print()
print("=" * 92)
print("CONTROL - the four real modulations must still be identified")
print("=" * 92)
for mod in MODS:
    sig, sps, _, _ = make_known(mod, 100_000, seed=11)
    picked, _ = sd.classify_constellation(sig, FS, sps)
    ok = picked == mod
    if not ok:
        bad.append((mod, picked))
    print(f"  {'ok  ' if ok else 'FAIL'} {mod:>6} -> {picked}")
print("=" * 92)
sys.exit(1 if bad else 0)
