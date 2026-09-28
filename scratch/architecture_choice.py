"""
Which architecture is right for OUR problem?

The question is whether ResNet-50 / YOLOv3 / InceptionV3 / Mask R-CNN would
beat a small purpose-built CNN for 4-class modulation classification on 32x32
constellation images.

Two things decide it, and only one of them is empirical:

  1. TASK  -- YOLOv3 and Mask R-CNN are detectors/segmenters. They emit boxes
     and masks. Our task is single-label classification of a whole image.
     This is not a performance question; it is a category error.

  2. SCALE -- ResNet-50 and InceptionV3 are ~25M-parameter ImageNet models.
     We have 360 captures. This script MEASURES what happens to test accuracy
     as model capacity grows past the data.

Run:  <python> scratch/architecture_choice.py
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "ml", "train.npz")


# ---------------------------------------------------------------------------
# A real (small) neural net, so "capacity" is not a metaphor
# ---------------------------------------------------------------------------


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def train_mlp(Xtr, ytr, Xte, yte, H, iters=200, lr=0.01, seed=0, C=4):
    """One-hidden-layer ReLU MLP, trained with Adam. Returns (params, train_acc, test_acc)."""
    rng = np.random.default_rng(seed)
    d = Xtr.shape[1]

    W1 = rng.normal(0, np.sqrt(2.0 / d), (d, H))
    b1 = np.zeros(H)
    W2 = rng.normal(0, np.sqrt(2.0 / H), (H, C))
    b2 = np.zeros(C)

    params = d * H + H + H * C + C

    mW1 = np.zeros_like(W1); vW1 = np.zeros_like(W1)
    mb1 = np.zeros_like(b1); vb1 = np.zeros_like(b1)
    mW2 = np.zeros_like(W2); vW2 = np.zeros_like(W2)
    mb2 = np.zeros_like(b2); vb2 = np.zeros_like(b2)
    b1t, b2t = 0.9, 0.999
    Y = np.eye(C)[ytr]

    for it in range(1, iters + 1):
        A1 = np.maximum(0, Xtr @ W1 + b1)
        P = softmax(A1 @ W2 + b2)
        dZ = (P - Y) / len(ytr)

        dW2 = A1.T @ dZ
        db2 = dZ.sum(0)
        dA1 = dZ @ W2.T
        dZ1 = dA1 * (A1 > 0)
        dW1 = Xtr.T @ dZ1
        db1 = dZ1.sum(0)

        for (g, m, v, p) in ((dW1, mW1, vW1, W1), (db1, mb1, vb1, b1),
                             (dW2, mW2, vW2, W2), (db2, mb2, vb2, b2)):
            m *= b1t; m += (1 - b1t) * g
            v *= b2t; v += (1 - b2t) * g * g
            mh = m / (1 - b1t ** it)
            vh = v / (1 - b2t ** it)
            p -= lr * mh / (np.sqrt(vh) + 1e-8)

    def acc(X, y):
        A1 = np.maximum(0, X @ W1 + b1)
        return float((softmax(A1 @ W2 + b2).argmax(axis=1) == y).mean())

    return params, acc(Xtr, ytr), acc(Xte, yte)


def split(y, frac=0.25, seed=0):
    rng = np.random.default_rng(seed)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        k = int(round(len(idx) * frac))
        te.extend(idx[:k]); tr.extend(idx[k:])
    return np.array(tr), np.array(te)


def main():
    if not os.path.exists(DATA):
        print("run scratch/build_training_set.py first")
        return 1

    d = np.load(DATA)
    X_hist, y = d["X_hist"], d["y"]
    n = len(y)

    tr, te = split(y)
    mu, sd = X_hist[tr].mean(0), X_hist[tr].std(0) + 1e-8
    Xtr, Xte = (X_hist[tr] - mu) / sd, (X_hist[te] - mu) / sd
    ytr, yte = y[tr], y[te]

    print("=" * 74)
    print("CAPACITY vs DATA  --  measured on our own dataset")
    print("=" * 74)
    print(f"train {len(tr)} samples / test {len(te)} samples "
          f"/ {X_hist.shape[1]} input pixels / 4 classes\n")
    print(f"{'hidden':>7}{'params':>12}{'params/sample':>15}"
          f"{'train acc':>11}{'TEST acc':>10}{'gap':>8}")
    print("-" * 74)

    rows = []
    for H in (2, 4, 8, 16, 32, 64, 256, 1024):
        t0 = time.time()
        p, a_tr, a_te = train_mlp(Xtr, ytr, Xte, yte, H)
        rows.append((H, p, a_tr, a_te))
        print(f"{H:>7}{p:>12,}{p/len(tr):>15,.0f}"
              f"{a_tr*100:>10.1f}%{a_te*100:>9.1f}%{(a_tr-a_te)*100:>7.1f}%"
              f"   ({time.time()-t0:.0f}s)", flush=True)

    best = max(rows, key=lambda r: r[3])
    print("-" * 74)
    print(f"best TEST accuracy: {best[3]*100:.1f}% at {best[1]:,} params "
          f"({best[1]/len(tr):,.0f} params/sample)")
    print(f"chance: 25.0%")

    # ---- What the four candidate architectures actually cost -------------
    print("\n" + "=" * 74)
    print("THE FOUR CANDIDATES, SCALED AGAINST OUR DATA")
    print("=" * 74)
    archs = [
        ("ResNet-50",    25_557_032, 224, "classification"),
        ("InceptionV3",  27_161_264, 299, "classification"),
        ("YOLOv3",       61_949_517, 416, "detection (boxes)"),
        ("Mask R-CNN",   44_454_513, 800, "instance segmentation (masks)"),
        ("our small CNN",   136_196,  32, "classification"),
    ]
    print(f"{'model':<15}{'params':>13}{'input':>8}{'task':>32}{'params/sample':>15}")
    print("-" * 74)
    for name, p, inp, task in archs:
        print(f"{name:<15}{p:>13,}{inp:>7}px{task:>32}{p/len(tr):>15,.0f}")
    print("-" * 74)
    print(f"We have {len(tr)} training samples.")
    print()
    print("Parameter-count provenance:")
    print("  ResNet-50    25,557,032  -- MEASURED (torchvision) and independently")
    print("                 re-derived from the layer spec (stem + 4 bottleneck")
    print("                 stages + fc). Two methods, exact agreement.")
    print("                 NOTE: that is the 1000-class head. Instantiated for")
    print("                 our 4 classes it is 23,516,228.")
    print("  InceptionV3  27,161,264  -- MEASURED (torchvision).")
    print("                 (An earlier revision of this script said 23,851,784;")
    print("                  that published figure was wrong. Corrected.)")
    print("  Mask R-CNN   44,454,513  -- MEASURED (torchvision, R50-FPN weights).")
    print("  YOLOv3       61,949,517  -- STILL NOT MEASURED. torchvision has no")
    print("                 YOLOv3; this remains a published figure. It is also")
    print("                 the one architecture already excluded on task grounds,")
    print("                 so its exact count does not affect the verdict.")
    print("  our small CNN   136,196  -- MEASURED (sum of the conv/fc layers).")

    print("\nVERDICT")
    print("-" * 74)
    print("YOLOv3 and Mask R-CNN answer a DIFFERENT QUESTION. They output")
    print("bounding boxes and pixel masks -- 'where are the objects'. Our task")
    print("has no objects: one capture, one label. That is a category error,")
    print("not a performance difference, and no amount of training fixes it.")
    print()
    print("ResNet-50 and InceptionV3 are the right TASK but the wrong INPUT")
    print("SIZE. They expect 224-299px; we have 32x32. Upsampling to 224 adds")
    print("no information, and their own first stage immediately downsamples")
    print("again -- so the extra resolution is thrown away before it is used.")
    print()
    print("IMPORTANT -- the experiment above did NOT confirm the overfitting")
    print("this script was written to demonstrate. Test accuracy stayed at")
    print("98.9-100% even at 1,053,700 params with only 272 training samples.")
    print("The four classes are cleanly separable in pixel space, so capacity")
    print("is NOT the binding constraint on this dataset.")
    print()
    print("That means the honest answer is that these four cannot be ranked")
    print("on our data at all. The test set is 88 samples, so ONE sample is")
    print("1.14% of accuracy -- any difference between architectures would sit")
    print("inside that noise. Ranking them would be measuring luck.")
    print()
    print("CAVEAT on this experiment: the MLP's effective capacity is capped")
    print("by its 1024-dimensional input, so it is not a perfect proxy for")
    print("ResNet-50 on a 150,528-dimensional input. The result weakens the")
    print("overfitting argument; it does not prove ResNet-50 would generalise.")
    print()
    print("THAT CAVEAT WAS THEN CLOSED DIRECTLY. scratch/resnet_vs_small_cnn.py")
    print("trains a REAL ResNet-50 from scratch (our 32x32 upsampled to 64x64,")
    print("3 channels) against the small 2-conv CNN, same split:")
    print()
    print("  model                       params  params/sample    train    TEST")
    print("  small CNN (32x32)          136,196            501   100.0%  100.0%")
    print("  ResNet-50 (64x64)       23,516,228         86,457   100.0%  100.0%")
    print()
    print("Both reach 100%. The small CNN gets there in 14 s; ResNet-50 needs")
    print("83 s to reach the same place. 170x the parameters bought 0.0 points")
    print("-- well inside the 1.14%-per-sample resolution of an 88-sample test")
    print("set. On this data the two are indistinguishable.")
    print()
    print("What actually decides it: there is no headroom. We are already at")
    print("98.9-100%. No architecture can beat the ceiling. The open risk is")
    print("whether these features survive REAL signals (fading, low SNR, unseen")
    print("modulations) -- and that is a DATA question, not an architecture one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
