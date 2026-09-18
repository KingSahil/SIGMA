# CNN: what the input is, and how you process it

*Answering Sanchit's two questions — "what about model training input?" and "how  
will we process the model?" — with measured evidence, 17 Sep 2026.*

Everything below was run, not reasoned about. Reproduce with:

```
<radioconda>/python.exe scratch/build_training_set.py       # build the dataset
<radioconda>/python.exe scratch/train_baseline_model.py     # score it
```

---

## The short answer

**Input:** a **32×32 constellation-density image** of the *demodulated symbols*,  
plus 4 quality scalars. Not raw IQ.

**Processing:** the DSP pipeline runs first on each capture and produces the  
image; a small 2-D CNN classifies it; the label goes to the demodulator.

**Measured result on 360 generated captures:** the image alone gets **93.2%**;  
with the scalars, **97.7%**. Chance is 25%.

---

## The output, and what it is actually worth

**The network emits four probabilities — one per constellation.** That is the
entire output:

```
BPSK  0.94      QPSK  0.04      8PSK  0.01      16QAM 0.01
```

Its **only** job is to choose which constellation the demodulator should slice.
A wrong label does not crash anything — it selects the wrong carrier-recovery
exponent (BPSK 2, QPSK/16QAM 4, 8PSK 8) and returns *silently wrong bits*.

**Two honest caveats before quoting this as a win.**

**(1) It changes one step of eight.** The pipeline is: symbol rate → constellation
→ **carrier exponent** → matched filter → timing → rotation → decisions → bits.
The CNN fills one slot.

**(2) A classifier already ships and already works.** `classify_constellation()`
in `sigma_demod.py` demodulates under each candidate and keeps the simplest that
fits, guarded by a "≥2 constellation phases" rule. It scores **144/144** over
4 modulations × 4 rates × 3 excess bandwidths × 3 seeds, and abstains on noise
(3/3). The real ResNet-50 experiment measured **zero** difference against a small
CNN at 170× the parameters — and the architecture comparison cannot resolve
differences under ~2 points (88-sample test set, 1.14% per sample).

So the CNN's value is **not** a measured accuracy gain. It is:

| Value | Status |
|---|---|
| Satisfies the PS requirement for an ML/CNN classifier | ✅ concrete — no network exists today |
| A second, independent opinion to cross-check tier 2 | ✅ real, but only surfaces *disagreement* |
| Accuracy on real (fading / low-SNR / unseen) signals | ⚠️ **unproven.** Synthetic-on-synthetic only |

**The sequencing consequence:** because the demodulator's own EVM classifier is
the stronger instrument (a physical measurement with a known noise floor, versus
a softmax with no error bars on real data), the CNN should be built **as a
cross-check with the existing classifier as the authority** — or deferred until
§3 iii/iv/v have code, since three empty sections cost more than one duplicate
classifier.

---

## 1. Two things I got wrong first, and what the measurement showed

These matter because both are mistakes someone will otherwise repeat.


### Mistake 1 — I assumed `SPS` would identify the modulation. It does not.

`docs/L1_L2_L3_ARCHITECTURE.md` §4.1 lists `SPS` as *"the single most  
informative feature"* for the CNN. **That claim is wrong and I measured it.**

At a fixed symbol rate, the symbol-rate estimate is *identical* across all four  
modulations:

```
rate=100k alpha=0.35 snr=30 seed=42
  BPSK   meas_sps=10.000  R_s=100,000.8  lock=HIGH  prom=46.0 dB
  QPSK   meas_sps=10.000  R_s=100,000.7  lock=HIGH  prom=46.3 dB
  8PSK   meas_sps=10.000  R_s=100,000.7  lock=HIGH  prom=46.4 dB
  16QAM  meas_sps=10.000  R_s=100,000.9  lock=HIGH  prom=46.5 dB
```

That is **correct physics**, not an estimator weakness: the envelope clock sits  
at `R_s` because that is the pulse-shaping rate. Nothing about the *shape* of  
the constellation appears in the envelope's periodicity. BPSK and QPSK at the  
same `R_s` have the same clock.

Scored over the whole 360-capture dataset:

| Scalar               | Accuracy alone (4 classes) |
| -------------------- | -------------------------- |
| `locked`             | 25.0%                      |
| `lock_confidence`    | 26.9%                      |
| `prominence_db`      | 25.0%                      |
| `samples_per_symbol` | 25.0%                      |
| **chance**           | **25.0%**                  |

**Every scalar is at chance.** So the scalars are not a classifier — they are a  
**quality gate** (they tell you whether to trust the image). `SPS` is still  
essential, but for the *demodulator*, not for the label.

**Fix needed in the doc:** `L1_L2_L3_ARCHITECTURE.md` §4.1 currently says `SPS`  
is the key feature. It should say the **constellation image** is the key  
feature, and the scalars gate it.


### Mistake 2 — I built the first image from raw decimated samples. It was a blob.

My first attempt sampled every `SPS`-th raw sample to build the image. Result:  
**25.3% — exactly chance.** The reason is visible in the numbers: the image had  
~140 non-zero bins spread over the whole grid with a max of 0.023, and the  
I/Q centroids were identical (7.61/7.52) for every class.

Why: the raw capture still carries a **60 kHz carrier offset**. Decimating it  
without carrier recovery leaves every symbol rotating, so the "constellation" is  
a smeared ring, not points. There is nothing to classify.

**The fix — and this is the key architectural point:** build the image from the  
**demodulator's output**, i.e. after carrier recovery, matched filtering, timing  
and phase correction. `sigma_demod.demodulate()` already does all of that and  
returns `res.symbols`. Using those, the image became real:

| Feature set                           | Accuracy       |
| ------------------------------------- | -------------- |
| raw-decimated image (wrong)           | 25.3% = chance |
| **demodulated-symbols image (right)** | **93.2%**      |

This also settles a design question: **the CNN cannot run before the  
demodulator.** The DSP chain produces the input. The order in the Notion  
flowchart (classifier → demodulation) is backwards for this architecture.

---

## 2. The training input, concretely

`scratch/build_training_set.py` writes `data/ml/train.npz`:

```
X_scal  (360, 4)      4 measured scalars
X_hist  (360, 1024)   32x32 constellation-density image, flattened
X       (360, 1028)   the two concatenated
y       (360,)        integer class label
```

Class order is in `data/ml/feature_spec.json`:

| Index | Class | Ground-truth SPS values swept |
| ----- | ----- | ----------------------------- |
| 0     | BPSK  | 4, 10, 20, 40, 80             |
| 1     | QPSK  | 4, 10, 20, 40                 |
| 2     | 8PSK  | 4, 10, 20, 40                 |
| 3     | 16QAM | 4, 10, 20, 40                 |

### The sweep — deliberately including the hard regimes

| Dimension          | Values                     | Why                                                            |
| ------------------ | -------------------------- | -------------------------------------------------------------- |
| Modulation         | BPSK, QPSK, 8PSK, 16QAM    | the PS §3 families we can currently slice                      |
| Symbol rate        | 25k, 50k, 100k, 200k, 250k | **low SPS is the hard regime**                                 |
| Excess bandwidth α | 0.20, 0.35, 0.50           | α=0.20 is the lowest and the most informative case             |
| SNR                | 10, 20, 30 dB              | 10 dB is realistically hostile                                 |
| Seeds              | 2                          | catches a lucky-noise result                                   |

> **Superseded note:** this table used to say α=0.20 caused `NO DEMOD` in 6 cases.
> That is no longer true — the demodulator now locks **72/72 with 0 refused**,
> including every α=0.20 case. Those failures were carrier-estimate defects, not
> the timing search. The dataset still *should* include α=0.20 (it is the most
> demanding case), but no longer because it is a known failure.

360 captures total. Do **not** train only on the easy middle (α=0.35, high SNR,  
mid rates) — that model will look excellent in validation and fail on the first  
real capture.

### What a single training example is

1. Generate a signal with **known** modulation, `R_s`, α, SNR, seed.
2. Run the real L2 symbol-rate estimator on it → `SPS`, confidence, prominence.
3. Run `demodulate()` at the best-fitting constellation → symbols.
4. Fold those symbols into a 32×32 density image (fixed extent −2.5…+2.5, RMS-normalised).
5. Label = the modulation we generated with.

**No manual labelling. The generator is the label.** That is the whole reason  
this approach is viable on our timeline, and it is also its main limitation —  
see §5.

---

## 3. How the model processes it


### Architecture (small on purpose)

```
constellation image (32x32x1)
        │
   Conv2D(16, 3x3) → ReLU → MaxPool(2)      # 32→16
        │
   Conv2D(32, 3x3) → ReLU → MaxPool(2)      # 16→8
        │
   Flatten  (32*8*8 = 2048)
        │
   concat ← 4 scalars
        │
   Dense(64) → ReLU → Dropout(0.3)
        │
   Dense(4) → Softmax
        │
   (label, confidence)
```

~140k parameters. That is a few seconds per epoch on CPU, which matters because  
**there is no GPU framework installed** (see §4).

**Why this shape and not raw IQ:** a raw-IQ CNN is the standard published  
architecture (RadioML and friends), but those models are trained on 100k–1M  
labelled examples from a professional simulator. We have 360 synthetic captures  
we generated ourselves. A constellation image is already a **feature-engineered**  
representation — the rotation, the carrier offset and the timing have been  
removed by the DSP chain — so the network only has to learn *shape*, which is a  
far smaller problem. It is the honest choice at our data scale.

### Wiring it in

```python
# in _run_demod_stage(), replacing the heuristic string test
mod_img, scal = build_cnn_input(samples, self.samp_rate, slock, sps)
label, conf = cnn.predict(mod_img, scal)
if conf < ABSTAIN_THRESHOLD:
    self._reset_demod_panel("ABSTAINED", f"CNN confidence {conf:.0%} below threshold")
    return
# else: label drives the slicer, as today
```

**Keep the heuristic classifier as a cross-check.** If the CNN and the heuristic  
disagree, that is a signal worth logging — and on our three real captures the  
heuristic already reports `LOW` lock, so the two disagreeing is expected and  
informative, not a bug.

### Abstention is mandatory

The problem statement says *"confidence-scored analysis"*. If the CNN is forced  
to emit a label on a weak input it will produce a confident wrong answer — and  
since the demodulator recovers bits at 100% *once told the right modulation*, a  
wrong label is the single dominant error source in the whole chain. Gate on  
confidence and emit `ABSTAINED` with a reason.

### Why not ResNet-50 / InceptionV3 / YOLOv3 / Mask R-CNN?

This gets asked every time a CNN is proposed, so it is measured here rather than
argued. Reproduce with `scratch/architecture_choice.py`.

**Two of the four answer a different question.**

| Model | What it outputs | Our task |
|---|---|---|
| YOLOv3 | bounding boxes + a class per box | one capture → one label |
| Mask R-CNN | a pixel mask per detected object | one capture → one label |
| ResNet-50 | one label per image | ✅ matches |
| InceptionV3 | one label per image | ✅ matches |

YOLOv3 and Mask R-CNN are a **detector** and a **segmenter**. They answer *"where
are the objects, and which pixels belong to each"*. Our captures contain one
signal and we want one label. That is a category error, not a performance
difference — no amount of training makes a box-regression head emit a modulation
class.

**The other two are the right task but the wrong input size.** ResNet-50 expects
224×224, InceptionV3 expects 299×299. We have 32×32. Upsampling to 224 invents no
information, and ResNet's own stem immediately downsamples by 4× again — so the
extra resolution is discarded before it is used.

**Measured: capacity is NOT the binding constraint here.** The script sweeps model
size on our own dataset (272 train / 88 test, 1024 input pixels):

| Hidden | Params | Params/sample | Train acc | **Test acc** |
|---|---|---|---|---|
| 8 | 8,236 | 30 | 100.0% | 98.9% |
| 64 | 65,860 | 242 | 100.0% | 98.9% |
| 256 | 263,428 | 968 | 100.0% | **100.0%** |
| 1024 | 1,053,700 | 3,874 | 100.0% | 98.9% |

**Test accuracy did not collapse as capacity grew.** The script was written to
demonstrate overfitting and the measurement disproved it. The four classes are
cleanly separable in pixel space, so even a 1M-parameter model finds the simple
boundary.

**So these four cannot be ranked on our data at all.** The test set is 88 samples —
one sample is **1.14%** of accuracy. Any difference between architectures would sit
inside that noise. Ranking them would be measuring luck.

**Caveat on the sweep above:** the MLP's effective capacity is capped by its
1024-dimensional input, so it is not a perfect proxy for ResNet-50 on a
150,528-dimensional input. That caveat was then **closed directly** — see below.

**Measured: a real ResNet-50 does not beat the small CNN.** The sweep above used
an MLP as a stand-in, so `scratch/resnet_vs_small_cnn.py` trains an actual
ResNet-50 from scratch (our 32×32 upsampled to 64×64, 3 channels) against the
small 2-conv CNN, on the identical stratified split:

| Model | Params | Params/sample | Train acc | **Test acc** | Time to converge |
|---|---|---|---|---|---|
| small CNN (32×32) | 136,196 | 501 | 100.0% | **100.0%** | 14 s |
| ResNet-50 (64×64) | 23,516,228 | 86,457 | 100.0% | **100.0%** | 83 s |

**170× the parameters bought 0.0 points.** The difference sits well inside the
1.14%-per-sample resolution of an 88-sample test set. The small CNN reaches the
same accuracy in 14 s that ResNet-50 needs 83 s to reach.

Exact counts, measured with torchvision rather than quoted: ResNet-50
**25,557,032** (1,000-class head; **23,516,228** when instantiated for our 4
classes), InceptionV3 **27,161,264**, Mask R-CNN (R50-FPN) **44,454,513**,
small CNN **136,196**. YOLOv3 is not in torchvision and remains a published
figure — it is excluded on task grounds anyway.

**What actually decides it — there is no headroom.** We are already at 98.9–100%.
No architecture can exceed the ceiling. The open risk is whether these features
survive *real* signals (fading, low SNR, modulations we have not generated), and
that is a **data** question, not an architecture one.

**Recommendation:** the small purpose-built 2-D CNN above (~140k params). Not
because it is bigger or newer, but because it is sized to the problem and the
data. Then spend the effort on the generator — fading, more modulations, more
seeds — because that is where the remaining risk lives.

---


## 4. Environment reality check

**Nothing is installed.** Measured in Radioconda:

| Package          | Status        |
| ---------------- | ------------- |
| numpy            | ✅             |
| scipy            | ✅ 1.15.2      |
| pandas           | ✅ 2.2.3       |
| **torch**        | ❌ **missing** |
| **tensorflow**   | ❌ **missing** |
| **scikit-learn** | ❌ **missing** |

There is also no training code, no dataset, and no model file anywhere in the  
repo. So "training the model" is currently a from-zero task, and the first  
concrete action is a decision: **PyTorch or TensorFlow?**

> **Feasibility confirmed.** To get the exact parameter counts in §3, torch
> 2.14.0+cpu and torchvision 0.29.0+cpu were installed into an isolated venv
> (`~/.workbuddy-ai/binaries/python/envs/default`) and a real ResNet-50 was
> trained on this machine. The install took 1 h 57 m on this connection, but it
> **succeeded** — so the "no framework available" blocker is a download, not a
> dead end. That venv is not wired into the app; the app still needs its own
> install (below).

- **PyTorch** — recommended. Smaller install, easier to debug, and a 2-conv  
  model is 40 lines.
- **TensorFlow/Keras** — fine if Nimish already knows it. `keras.Sequential`  
  is very readable.

Install into Radioconda, not a separate venv, so the app can import it:

```
<radioconda>/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Important:** whatever gets installed becomes a hard dependency of the app. The  
GUI must degrade gracefully when the model or the framework is absent —  
otherwise "no model installed" becomes "app will not start". Wrap the import in  
`try/except` and fall back to the heuristic classifier.

---


## 5. The honest limits — say these out loud

1. **97.7% is on generated data, from a generator we wrote.** It is not  
   real-world accuracy. State it as *"97.7% on our own synthetic sweep."*
2. **The generator's assumptions are the model's ceiling.** It uses RRC pulse  
   shaping, a clean AWGN channel, and no fading. A model trained on it will meet  
   conditions it has never seen. Add the fading step from the Notion recipe  
   (`Generate QPSK → AWGN → freq offset → phase offset → fading → coding`) as  
   soon as the base case works — it is the step most likely to expose an  
   overfitted feature.
3. **Class balance is even here (90 each), which is not realistic.** Real  
   captures are overwhelmingly unmodulated or noise. Expect a real deployment to  
   need a "none of the above" class.
4. **Only four classes.** PS §3 also asks for FSK. FSK is not demoduable yet  
   (`TEAM_TASKS.md` §3 A4), so it cannot be in the dataset — and the L2  
   classifier currently emits `"BPSK / 2-FSK"` as an ambiguity. Resolve FSK  
   before claiming PSK+FSK classification.
5. **360 samples is small.** It proved the *features* work. It is not enough to  
   train a production classifier — the target should be several thousand, which  
   is minutes of generation time.

---

## 6. What to tell Sanchit

> Input is a 32×32 picture of the constellation, built from the demodulator's  
> output — not raw IQ. I measured that SPS and the other scalars are at chance  
> for telling modulations apart, so the image carries the label and the scalars  
> just gate quality.
>
> It works: **97.7% on 360 generated captures** (chance 25%), with BPSK/QPSK/  
> 8PSK/16QAM at 100/100/100/91% recall.
>
> Two blockers before this is real: (1) **the framework is proven but not wired
> in** — PyTorch/torchvision were installed into an isolated venv and used to
> train a real ResNet-50 to 100.0% test accuracy on this same dataset (no better
> than the small CNN, at 170× the parameters), but torch is **not importable from
> the app** and no training script lives in the repo yet; (2) the **generator
> needs more samples and a fading step**, because right now it is
> synthetic-on-synthetic and we should not quote it as real accuracy.
>
> Also: the Notion flowchart has the classifier *before* demodulation. For this  
> design it has to be *after*, because the demodulator is what produces the  
> constellation image.

---

## 7. Files

| File                              | What it is                                                          |
| --------------------------------- | ------------------------------------------------------------------- |
| `scratch/build_training_set.py`   | generates the corpus, extracts features, writes `data/ml/train.npz` |
| `scratch/train_baseline_model.py` | stratified split + real classifier; prints the honest score         |
| `data/ml/train.npz`               | the dataset (`X_scal`, `X_hist`, `X`, `y`)                          |
| `data/ml/feature_spec.json`       | class order, feature names, shapes — the model's contract           |

Both scripts run in ~60 s in Radioconda. Re-run them after any change to  
`sigma_symbol_rate.py` or `sigma_demod.py` — the dataset is derived from those,  
so a change there silently changes the model's input distribution.
