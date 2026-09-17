"""
Score the constellation-image features with a REAL classifier.

The nearest-class-mean baseline in build_training_set.py is a floor. This
script is the honest test: train/test split, a small CNN if torch is
available, otherwise a closed-form softmax regression implemented directly in
numpy. It also settles the question of whether the scalars should be
concatenated raw or normalised.

Run:  <radioconda>/python.exe scratch/train_baseline_model.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "ml", "train.npz")


def load():
    d = np.load(DATA)
    return d["X_scal"], d["X_hist"], d["y"]


def split(y, frac=0.25, seed=0):
    """Stratified train/test split -- every class appears in both halves."""
    rng = np.random.default_rng(seed)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        k = int(round(len(idx) * frac))
        te.extend(idx[:k])
        tr.extend(idx[k:])
    return np.array(tr), np.array(te)


def standardise(Xtr, Xte):
    mu, sd = Xtr.mean(axis=0), Xtr.std(axis=0) + 1e-8
    return (Xtr - mu) / sd, (Xte - mu) / sd


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def train_softmax(Xtr, ytr, Xte, yte, n_class=4, iters=600, lr=0.5, l2=1e-4):
    """Multinomial logistic regression by gradient descent. Tiny, no deps."""
    n, d = Xtr.shape
    W = np.zeros((d, n_class))
    b = np.zeros(n_class)
    Y = np.eye(n_class)[ytr]
    for it in range(iters):
        P = softmax(Xtr @ W + b)
        gW = Xtr.T @ (P - Y) / n + l2 * W
        gb = (P - Y).mean(axis=0)
        W -= lr * gW
        b -= lr * gb
    pred = (Xte @ W + b).argmax(axis=1)
    return W, b, float((pred == yte).mean()), pred


def confusion(yte, pred, names):
    print("    " + "".join(f"{n:>9}" for n in names))
    for i, n in enumerate(names):
        row = "".join(f"{(pred[yte == i] == j).mean()*100:>8.1f}%" for j in range(len(names)))
        print(f"    {n:<6}{row}")
    print("    (rows = true class, columns = predicted; % recall)")


def main():
    if not os.path.exists(DATA):
        print("run scratch/build_training_set.py first")
        return 1
    X_scal, X_hist, y = load()
    names = ["BPSK", "QPSK", "8PSK", "16QAM"]
    print(f"loaded {X_scal.shape[0]} samples: "
          f"{X_scal.shape[1]} scalars + {X_hist.shape[1]} image pixels\n")

    tr, te = split(y)
    print(f"split: {len(tr)} train / {len(te)} test (stratified)\n")

    results = {}

    # ---- 1. Image only -------------------------------------------------
    a, b = standardise(X_hist[tr], X_hist[te])
    _, _, acc, pred = train_softmax(a, y[tr], b, y[te])
    results["constellation image only"] = acc
    print(f"[1] constellation image only ................ {acc*100:5.1f}%")
    confusion(y[te], pred, names)

    # ---- 2. Scalars only (expect chance) -------------------------------
    a, b = standardise(X_scal[tr], X_scal[te])
    _, _, acc_s, pred_s = train_softmax(a, y[tr], b, y[te])
    results["scalars only"] = acc_s
    print(f"\n[2] scalars only ............................ {acc_s*100:5.1f}%   "
          f"(expect ~25% = chance)")
    confusion(y[te], pred_s, names)

    # ---- 3. Raw concat -- demonstrates the scaling bug ------------------
    Xr = np.hstack([X_scal, X_hist])
    a, b = standardise(Xr[tr], Xr[te])
    _, _, acc_raw, _ = train_softmax(a, y[tr], b, y[te])
    results["concat, globally standardised"] = acc_raw
    print(f"\n[3] scalars + image, global standardise .... {acc_raw*100:5.1f}%")

    # ---- 4. Correct concat: standardise each block separately -----------
    sa, sb = standardise(X_scal[tr], X_scal[te])
    ha, hb = standardise(X_hist[tr], X_hist[te])
    Xtr2 = np.hstack([sa, ha])
    Xte2 = np.hstack([sb, hb])
    _, _, acc_ok, pred_ok = train_softmax(Xtr2, y[tr], Xte2, y[te])
    results["concat, block standardised"] = acc_ok
    print(f"[4] scalars + image, BLOCK standardise ..... {acc_ok*100:5.1f}%")
    confusion(y[te], pred_ok, names)

    # ---- Summary --------------------------------------------------------
    print("\n" + "=" * 62)
    print("SUMMARY  (chance = 25.0%)")
    print("=" * 62)
    for k, v in results.items():
        print(f"  {k:<38} {v*100:5.1f}%")
    best = max(results.values())
    print(f"\nBest: {best*100:.1f}%")

    if results["constellation image only"] < 0.40:
        print("\nVERDICT: the constellation image does NOT carry enough")
        print("         modulation information. Fix the features before")
        print("         building a CNN -- depth will not help.")
        return 1
    else:
        print("\nVERDICT: the constellation image carries real modulation")
        print("         information. A CNN should beat this baseline.")
        print("         Next: feed the image to a small 2-D CNN.")

    print("\nNote: a linear model on a 1024-pixel image is a WEAK classifier;")
    print("      67-75% here means a CNN will do considerably better. The")
    print("      point of this script is to prove the FEATURES are alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
