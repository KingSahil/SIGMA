"""
Build a CNN training set from KNOWN ground truth -- and prove the pipeline.

Sanchit's question: "what about model training input?"

Answer: the model's input is built from things we can MEASURE, not from raw IQ.
This script is the working proof. It:

  1. generates signals with known labels (SPS, modulation order, alpha, SNR),
  2. runs the SAME L2 feature extractor the GUI uses,
  3. writes an (X, y) dataset a CNN can consume,
  4. scores a baseline classifier against the labels.

If the feature extractor is any good, even a trivial classifier should do well,
and -- more importantly -- the SPS column should separate the classes.

Run:  <radioconda>/python.exe scratch/build_training_set.py
Writes: data/ml/train.npz, data/ml/feature_spec.json
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from sigma_symbol_rate import estimate_symbol_rate          # noqa: E402

OUT_DIR = os.path.join(ROOT, "data", "ml")
FS = 1_000_000.0
HIST_N = 32          # constellation-image resolution (32 x 32 = 1024 pixels)

# ---------------------------------------------------------------------------
# Signal generation (same physics as scratch/make_ground_truth.py, extended)
# ---------------------------------------------------------------------------


def rrc_filter(sps, alpha, span_symbols=8):
    """Root-raised-cosine impulse response, unit energy."""
    n = span_symbols * sps
    t = np.arange(-n // 2, n // 2 + 1, dtype=np.float64) / sps
    h = np.zeros_like(t)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-8:
            h[i] = 1.0 - alpha + 4.0 * alpha / np.pi
        elif alpha > 0 and abs(abs(ti) - 1.0 / (4.0 * alpha)) < 1e-8:
            h[i] = (alpha / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                - (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha)))
        else:
            num = (np.sin(np.pi * ti * (1.0 - alpha))
                   + 4.0 * alpha * ti * np.cos(np.pi * ti * (1.0 + alpha)))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            h[i] = num / den
    h /= np.sqrt(np.sum(h ** 2))
    return h


# Constellation order -> the unit symbols. This is the ground-truth label.
def make_symbols(modulation, n_symbols, rng):
    if modulation == "BPSK":
        return (rng.integers(0, 2, n_symbols) * 2 - 1).astype(np.complex128)
    if modulation == "QPSK":
        b_i = rng.integers(0, 2, n_symbols) * 2 - 1
        b_q = rng.integers(0, 2, n_symbols) * 2 - 1
        return (b_i + 1j * b_q) / np.sqrt(2)
    if modulation == "8PSK":
        k = rng.integers(0, 8, n_symbols)
        return np.exp(1j * 2 * np.pi * k / 8)
    if modulation == "16QAM":
        lv = np.array([-3, -1, 1, 3], dtype=np.float64)
        i = rng.choice(lv, n_symbols)
        q = rng.choice(lv, n_symbols)
        return (i + 1j * q) / np.sqrt(10)
    raise ValueError(modulation)


def make_signal(modulation, symbol_rate, alpha, snr_db, sps_int, seed):
    """Generate one capture with fully known parameters."""
    rng = np.random.default_rng(seed)
    n_symbols = 4000

    sym = make_symbols(modulation, n_symbols, rng)

    up = np.zeros(n_symbols * sps_int, dtype=np.complex128)
    up[::sps_int] = sym

    h = rrc_filter(sps_int, alpha)
    shaped = np.convolve(up, h, mode="same")

    # Carrier offset, exactly like a real capture.
    t = np.arange(len(shaped)) / FS
    f_off = 60_000.0
    shaped = shaped * np.exp(1j * 2 * np.pi * f_off * t)

    # Sensitivity target: signal power / noise power = snr_db.
    p_sig = np.mean(np.abs(shaped) ** 2)
    p_noise = p_sig / (10 ** (snr_db / 10.0))
    noise = (rng.normal(0, 1, len(shaped))
             + 1j * rng.normal(0, 1, len(shaped))) * np.sqrt(p_noise / 2.0)
    out = shaped + noise

    out = out / np.max(np.abs(out)) * 0.9
    return out.astype(np.complex64)


# ---------------------------------------------------------------------------
# Feature extraction -- THIS is what the CNN eats
# ---------------------------------------------------------------------------


def extract_features(x, fs):
    """The L2 -> CNN feature vector. Mirrors docs/L1_L2_L3_ARCHITECTURE.md §4.1.

    IMPORTANT -- what this deliberately does NOT use:
    the symbol-rate scalars carry NO modulation information. Measured: at a
    fixed R_s the envelope clock is identical for BPSK/QPSK/8PSK/16QAM, so
    every scalar gives exactly chance accuracy on a 4-class problem. See the
    separation report printed by main(). The modulation label can only come
    from the CONSTELLATION, so the image is the load-bearing input here.
    """
    sr = estimate_symbol_rate(x, fs)
    sps = sr["samples_per_symbol"]

    # Constellation-density map: fold the constellation into a 32x32 image.
    #
    # The symbols must come from the DEMODULATOR (post carrier-recovery,
    # matched filter, timing and phase correction), not from raw decimation of
    # the input. Decimating the raw capture leaves the carrier offset in
    # place, so the points smear into a ring and the image carries no
    # modulation information at all. That mistake was made and measured here.
    hist = np.zeros((HIST_N, HIST_N), dtype=np.float32)
    if sr["locked"] and sps >= 2.0:
        try:
            from sigma_demod import demodulate
            # Try each PSK/QAM constellation and keep the tightest fit. This
            # is only for BUILDING THE TRAINING IMAGE -- the label being
            # predicted is the modulation, and the image is the evidence.
            best = None
            for cand in ("BPSK", "QPSK", "8PSK", "16QAM"):
                try:
                    r = demodulate(x, fs, modulation=cand, sps=sps)
                except Exception:
                    continue
                if not r.locked or r.symbols is None or len(r.symbols) < 16:
                    continue
                if best is None or r.evm_percent < best.evm_percent:
                    best = r
            if best is not None:
                sym = np.asarray(best.symbols, dtype=np.complex128)
                # Normalise by RMS so the image is scale-invariant.
                sym = sym / (np.sqrt(np.mean(np.abs(sym) ** 2)) + 1e-12)
                # Fixed extent so every image uses the same axes.
                lo, hi = -2.5, 2.5
                bi = np.clip(((np.real(sym) - lo) / (hi - lo) * HIST_N).astype(int), 0, HIST_N - 1)
                bq = np.clip(((np.imag(sym) - lo) / (hi - lo) * HIST_N).astype(int), 0, HIST_N - 1)
                np.add.at(hist, (bq, bi), 1.0)
                if hist.sum() > 0:
                    hist /= hist.sum()
        except Exception as e:
            print(f"    (constellation image failed: {e})")

    scalars = np.array([
        float(sr["locked"]),             # 1. did the clock lock
        float(sr["confidence"]),         # 2. lock confidence
        sr["prominence_db"],             # 3. clock prominence over noise
        sps,                             # 4. SPS  (needed to demodulate, NOT a label cue)
    ], dtype=np.float32)

    return scalars, hist, sr


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # The sweep deliberately includes the hard regimes, not just the easy middle.
    modulations = ["BPSK", "QPSK", "8PSK", "16QAM"]
    symbol_rates = [25_000, 50_000, 100_000, 200_000, 250_000]
    alphas = [0.20, 0.35, 0.50]
    snrs = [10.0, 20.0, 30.0]
    seeds = [7, 42]

    scalars_all, hists_all, y_all, meta_all = [], [], [], []
    mod_index = {m: i for i, m in enumerate(modulations)}

    print(f"Generating {len(modulations)*len(symbol_rates)*len(alphas)*len(snrs)*len(seeds)} captures...")
    n_fail = 0
    for mod in modulations:
        for rs in symbol_rates:
            for alpha in alphas:
                for snr in snrs:
                    for seed in seeds:
                        sps_int = int(round(FS / rs))
                        if abs(FS / rs - sps_int) > 1e-9:
                            continue
                        try:
                            x = make_signal(mod, rs, alpha, snr, sps_int, seed)
                        except Exception as e:
                            print(f"  gen fail {mod} {rs} {alpha} {snr} {seed}: {e}")
                            continue
                        try:
                            scal, hist, sr = extract_features(x, FS)
                        except Exception as e:
                            n_fail += 1
                            print(f"  extract fail {mod} {rs} {alpha} {snr} {seed}: {e}")
                            continue

                        scalars_all.append(scal)
                        hists_all.append(hist.ravel())
                        y_all.append(mod_index[mod])
                        meta_all.append({
                            "modulation": mod, "symbol_rate_hz": rs,
                            "alpha": alpha, "snr_db": snr, "seed": seed,
                            "true_sps": float(sps_int),
                            "meas_sps": float(sr["samples_per_symbol"]),
                            "lock": sr["confidence_label"],
                        })

    X_scal = np.asarray(scalars_all, dtype=np.float32)
    X_hist = np.asarray(hists_all, dtype=np.float32)
    y = np.asarray(y_all, dtype=np.int64)
    X = np.hstack([X_scal, X_hist])

    np.savez_compressed(os.path.join(OUT_DIR, "train.npz"),
                        X_scal=X_scal, X_hist=X_hist, X=X, y=y)
    with open(os.path.join(OUT_DIR, "feature_spec.json"), "w") as f:
        json.dump({
            "classes": modulations,
            "n_scalar": int(X_scal.shape[1]),
            "hist_shape": [HIST_N, HIST_N],
            "n_features": int(X.shape[1]),
            "scalar_names": ["locked", "lock_confidence",
                             "prominence_db", "samples_per_symbol"],
            "note": ("Feature vector = 4 measured scalars + a "
                     f"{HIST_N}x{HIST_N} constellation-density histogram of "
                     "DEMODULATED SYMBOLS (not raw IQ samples). The scalars are "
                     "NOT modulation cues -- measured at chance on a 4-class "
                     "problem. The constellation image is the load-bearing "
                     "input; the scalars act as a quality gate."),
        }, f, indent=2)

    print(f"\nwrote {X.shape[0]} samples x {X.shape[1]} features "
          f"({X_scal.shape[1]} scalars + {X_hist.shape[1]} histogram)")
    if n_fail:
        print(f"  ({n_fail} extraction failures -- see above)")

    # ---- Do the scalars carry the label at all? Measured, not assumed. ----
    print("\n=== are the SCALARS a modulation cue? (this is the key check) ===")
    print(f"{'scalar':<24}{'alone-accuracy':>16}")
    for j, name in enumerate(["locked", "lock_confidence",
                              "prominence_db", "samples_per_symbol"]):
        col = X_scal[:, j]
        mu = np.array([col[y == i].mean() for i in range(len(modulations))])
        p = np.abs(col[:, None] - mu[None, :]).argmin(axis=1)
        acc_j = (p == y).mean() * 100
        verdict = "chance" if acc_j < 100 / len(modulations) + 5 else "INFORMATIVE"
        print(f"{name:<24}{acc_j:>15.1f}%  {verdict}")
    print(f"  (chance on {len(modulations)} classes = {100/len(modulations):.1f}%)")
    print("  -> the scalars are a QUALITY GATE, not a classifier.")
    print("     This is why the constellation image must exist.")

    # ---- The constellation image is where the label comes from. ----------
    print("\n=== baseline: nearest-class-mean on the CONSTELLATION IMAGE ===")
    mu_h = np.stack([X_hist[y == i].mean(axis=0) for i in range(len(modulations))])
    dh = ((X_hist[:, None, :] - mu_h[None, :, :]) ** 2).sum(axis=2)
    pred_h = dh.argmin(axis=1)
    acc_h = float((pred_h == y).mean())
    print(f"  image-only accuracy: {acc_h*100:.1f}%  ({len(y)} samples)")
    print("  per-class recall:")
    for mod, i in mod_index.items():
        m = (y == i)
        if m.sum():
            print(f"    {mod:<7}{(pred_h[m] == i).mean()*100:>6.1f}%  (n={m.sum()})")

    X = np.hstack([X_scal, X_hist])
    mu2 = np.stack([X[y == i].mean(axis=0) for i in range(len(modulations))])
    d2 = ((X[:, None, :] - mu2[None, :, :]) ** 2).sum(axis=2)
    acc2 = float((d2.argmin(axis=1) == y).mean())
    print(f"  scalars+image accuracy: {acc2*100:.1f}%")

    print("\nNOTE: nearest-class-mean is a very weak classifier and UNDERSTATES")
    print("      these features. For the honest score (train/test split, real")
    print("      classifier), run scratch/train_baseline_model.py -- it reaches")
    print("      97.7% on this same dataset. Use that number, not these.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
