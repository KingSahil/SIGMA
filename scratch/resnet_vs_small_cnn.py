"""
Does a real 25M-parameter ImageNet backbone beat a small purpose-built CNN
on OUR data? The MLP sweep in architecture_choice.py could not answer this,
because its effective capacity was capped by its 1024-dimensional input.

This trains an actual ResNet-50 from scratch on our 360 constellation images
and compares it against a small 2-conv CNN under the identical split.

Run:  ~/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe \
          scratch/resnet_vs_small_cnn.py
"""
import os
import sys
import time

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torchvision.models
except ImportError as e:
    print(f"torch/torchvision not importable in this interpreter: {e}")
    print()
    print("This script needs the interpreter that has torch installed:")
    print("  C:/Users/<user>/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe")
    sys.exit(2)

torch.set_num_threads(max(1, (os.cpu_count() or 4)))
torch.manual_seed(0)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "ml", "train.npz")


def n_params(m):
    return sum(p.numel() for p in m.parameters())


def split(y, frac=0.25, seed=0):
    rng = np.random.default_rng(seed)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        k = int(round(len(idx) * frac))
        te.extend(idx[:k]); tr.extend(idx[k:])
    return np.array(tr), np.array(te)


class SmallCNN(nn.Module):
    """The architecture recommended in docs/CNN_INPUT_AND_TRAINING.md section 3."""

    def __init__(self, n_class=4):
        super().__init__()
        self.c1 = nn.Conv2d(1, 16, 3, padding=1)
        self.c2 = nn.Conv2d(16, 32, 3, padding=1)
        self.fc1 = nn.Linear(32 * 8 * 8, 64)
        self.fc2 = nn.Linear(64, n_class)

    def forward(self, x):
        x = F.max_pool2d(F.relu(self.c1(x)), 2)
        x = F.max_pool2d(F.relu(self.c2(x)), 2)
        x = x.flatten(1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)


def train(model, Xtr, ytr, Xte, yte, epochs, lr, label):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.CrossEntropyLoss()
    t0 = time.time()
    for ep in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(len(Xtr))
        for i in range(0, len(Xtr), 32):
            b = perm[i:i + 32]
            opt.zero_grad()
            loss = lossf(model(Xtr[b]), ytr[b])
            loss.backward()
            opt.step()
        if ep % max(1, epochs // 4) == 0 or ep == epochs:
            model.eval()
            with torch.no_grad():
                a_tr = (model(Xtr).argmax(1) == ytr).float().mean().item()
                a_te = (model(Xte).argmax(1) == yte).float().mean().item()
            print(f"    ep {ep:>3}  train {a_tr*100:5.1f}%  test {a_te*100:5.1f}%"
                  f"   ({time.time()-t0:.0f}s)", flush=True)
    model.eval()
    with torch.no_grad():
        a_tr = (model(Xtr).argmax(1) == ytr).float().mean().item()
        a_te = (model(Xte).argmax(1) == yte).float().mean().item()
    return n_params(model), a_tr, a_te


def main():
    if not os.path.exists(DATA):
        print("run scratch/build_training_set.py first")
        return 1

    d = np.load(DATA)
    X = d["X_hist"].reshape(-1, 1, 32, 32).astype(np.float32)
    y = d["y"]
    tr, te = split(y)

    # Per-image standardisation.
    mu, sd = X[tr].mean(), X[tr].std() + 1e-8
    Xn = (X - mu) / sd

    print("=" * 74)
    print("EXACT PARAMETER COUNTS (torchvision, measured not quoted)")
    print("=" * 74)
    for name, fn in (
        ("ResNet-50", lambda: torchvision.models.resnet50(weights=None, num_classes=1000)),
        ("InceptionV3", lambda: torchvision.models.inception_v3(weights=None, num_classes=1000, init_weights=False)),
        ("Mask R-CNN (R50-FPN)", lambda: torchvision.models.detection.maskrcnn_resnet50_fpn(weights=None, weights_backbone=None)),
    ):
        try:
            m = fn()
            print(f"  {name:<24}{n_params(m):>14,}")
            del m
        except Exception as e:
            print(f"  {name:<24}  unavailable: {type(e).__name__}: {e}")
    print(f"  {'YOLOv3':<24}{'not in torchvision':>14}")
    print()

    # ---- Small CNN on the native 32x32 image ----------------------------
    print("=" * 74)
    print("TRAIN: small CNN on native 32x32  (our recommendation)")
    print("=" * 74)
    Xtr = torch.from_numpy(Xn[tr]); Xte = torch.from_numpy(Xn[te])
    ytr = torch.from_numpy(y[tr]).long(); yte = torch.from_numpy(y[te]).long()
    p_small, tr_s, te_s = train(SmallCNN(), Xtr, ytr, Xte, yte, 40, 3e-3, "small")

    # ---- Real ResNet-50, from scratch, upsampled to 64x64 ---------------
    print()
    print("=" * 74)
    print("TRAIN: ResNet-50 from scratch, 32x32 upsampled to 64x64, 3 channels")
    print("=" * 74)
    Xr = F.interpolate(torch.from_numpy(Xn), size=64, mode="bilinear",
                       align_corners=False).repeat(1, 3, 1, 1)
    Xtr_r, Xte_r = Xr[tr], Xr[te]
    p_res, tr_r, te_r = train(
        torchvision.models.resnet50(weights=None, num_classes=4),
        Xtr_r, ytr, Xte_r, yte, 12, 1e-3, "resnet")

    # ---- Verdict --------------------------------------------------------
    print()
    print("=" * 74)
    print("RESULT")
    print("=" * 74)
    print(f"{'model':<22}{'params':>14}{'params/sample':>15}{'train':>9}{'TEST':>8}")
    print("-" * 74)
    print(f"{'small CNN (32x32)':<22}{p_small:>14,}{p_small/len(tr):>15,.0f}"
          f"{tr_s*100:>8.1f}%{te_s*100:>7.1f}%")
    print(f"{'ResNet-50 (64x64)':<22}{p_res:>14,}{p_res/len(tr):>15,.0f}"
          f"{tr_r*100:>8.1f}%{te_r*100:>7.1f}%")
    print("-" * 74)
    print(f"chance = 25.0%   test set = {len(te)} samples "
          f"(1 sample = {100/len(te):.2f}%)")
    print()
    d_te = (te_s - te_r) * 100
    if d_te > 2.0:
        print(f"Small CNN wins by {d_te:.1f} points on test.")
    elif d_te < -2.0:
        print(f"ResNet-50 wins by {-d_te:.1f} points on test -- the scale")
        print("argument does NOT hold on this dataset.")
    else:
        print(f"Difference {abs(d_te):.1f} points is inside the noise floor")
        print(f"({100/len(te):.2f}% per sample). They are indistinguishable here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
