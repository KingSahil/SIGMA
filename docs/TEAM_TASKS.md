# SIGMA — task breakdown and owner assignment

*Status as measured on 17 Sep 2026. Every figure below was re-measured today, not
recalled. Where something is unknown or unstarted, it says so.*

---

## 1. Where we actually are

| Problem-statement requirement | Status | Evidence |
|---|---|---|
| Ingestion (`.iq` / `.wav`) | ✅ done | WAV header parse + IQ binary decode |
| Spectral features (SNR, power, OBW, constellation) | ✅ done | 4 live GNU Radio sinks in the GUI |
| Symbol rate `R_s` | ✅ done | **10/10 locked**, 9 at exactly 0.00% error |
| Sample rate `f_s` | ⚠️ resolved, not measured | Proven unmeasurable from samples; ranked provenance in the GUI |
| PSK demodulation (BPSK/QPSK) | ✅ done | **46/46 at exactly 100.00%** bit accuracy |
| QAM demodulation (16QAM) | 🟢 **works, gate blocks it** | **99.98% bit accuracy** measured today (§3 A1) |
| PSK demodulation (8PSK) | 🔴 broken, cause known | 51.70% = random. Fix identified (§3 A2) |
| FSK demodulation | ❌ not started | no code |
| CNN modulation classifier | 🟡 interface defined | contract in `L1_L2_L3_ARCHITECTURE.md` §4.1 |
| Interleaving detection / de-interleaving | ❌ not started | no code |
| FEC (Viterbi / RS / LDPC) | ❌ not started | no code |
| Bitstream correlation / header detection | ❌ not started | no code |

**Roughly 3 of 5 problem-statement sections are complete.** The remaining work is
real work, not polish.

---

## 2. Who does what

Four workstreams, deliberately ordered by *value per hour* — the top ones are
small and unblock other people.

| # | Workstream | Owner | Size |
|---|---|---|---|
| A | **Unblock 16QAM + fix 8PSK carrier recovery** | Sahil (demod) | small, well-understood |
| B | **CNN modulation classifier** | Nimish (ML) | largest |
| C | **FSK demodulation** | Sahil or a third hand | medium |
| D | **De-interleaving + FEC** | unassigned — needs an owner | large |

---

## 3. Workstream A — demodulation completeness (Sahil)

Highest value first. **A1 is the single cheapest win in the project.**

### A1. Let 16QAM through the gate — *~5 lines*

`sigma_demod.py` already defines the 16QAM constellation and it **demodulates at
99.98%**. The GUI gate in `sigma_main_window.py` refuses it:

```python
if "QPSK" in mod:        label = "QPSK"
elif "BPSK" in mod:      label = "BPSK"
elif "PSK" in mod:       # <-- 8PSK and 16QAM get refused here
```

**Do:** add QAM handling and make the gate ask the demodulator which
constellations it supports, instead of hardcoding a list in two places.

**Verify:** `scratch/probe_8psk_16qam.py` should show 16QAM added to the GUI path.
Add it to the regression suite so it cannot silently break.

### A2. Fix 8PSK carrier recovery — *small, root cause known*

**Root cause: `estimate_carrier_offset()` hardcodes `x**4`.**

The M-th power method works because raising an M-fold-symmetric PSK signal to the
M-th power collapses all constellation points onto one, leaving a pure tone at
`M × offset`. But `M` must match the constellation:

| Signal | x² | x⁴ | x⁸ |
|---|---|---|---|
| 2-PSK | **−2 Hz** | −2 Hz | −2 Hz |
| 4-PSK | +303 Hz | **−2 Hz** | −2 Hz |
| 8-PSK | −11111 Hz | −16390 Hz | **−2 Hz** |

*(error vs a true +60,000 Hz offset; `scratch/probe_power_matrix.py`)*

8PSK is 8-fold symmetric, so `x⁴` leaves the modulation partly intact and the
residual biases the peak. **The exponent must become a parameter** —
`power = constellation order` (2 / 4 / 8).

Also fix the ambiguity fold, which is tied to the same number:

```python
span = samp_rate / 4.0        # <-- must be samp_rate / power
```

Measured symptom of the stale fold: a true +150 kHz offset on 8PSK returns
`locked=False` with EVM 51.5%.

**Verify:** extend `scratch/probe_power_matrix.py` into a real assertion — every
constellation must land within a few Hz at several offsets, and must lock across
the full `±f_s/(2·power)` span.

### A3. Loosen the α = 0.20 boundary — *medium*

Five BPSK cases and one QPSK case at `α = 0.20` report `NO DEMOD` rather than
wrong bits. That is correct behaviour, but it is a capability gap.

**Do:** implement a **Gardner** or **Müller & Müller** timing-error detector after
matched filtering. Do **not** attempt the zero-ISI-null approach — it was
measured and is *worse* than taking the strongest spectral bin (11/20 vs 14/20).

### A4. FSK demodulation — *medium*

Not started. A discriminator (differentiate the phase) plus the existing timing
search covers most of it, but the L2 classifier currently emits `"BPSK / 2-FSK"`
as an *ambiguity* rather than distinguishing them. That needs resolving first, or
FSK will never be selected.

---

## 4. Workstream B — the CNN (Nimish)

Read `docs/L1_L2_L3_ARCHITECTURE.md` §4.1 first — the interface is already specified.

### B0. Install a framework — *do this first, it is currently a hard blocker*

**No ML framework is installed.** Measured in Radioconda: `numpy` ✅, `scipy`
1.15.2 ✅, `pandas` 2.2.3 ✅, but **`torch` ❌, `tensorflow` ❌, `sklearn` ❌**.
There is also no training code and no model file anywhere in the repo.

Pick one and install it into Radioconda (not a separate venv, or the app cannot
import it):

```
<radioconda>/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Whatever is installed becomes a **hard dependency of the app**. Wrap the import
in `try/except` and fall back to the existing heuristic classifier, or "model
not installed" becomes "app will not start".

### B1. Build the feature extractor

**This is already written and measured** — see
[`CNN_INPUT_AND_TRAINING.md`](CNN_INPUT_AND_TRAINING.md) and
`scratch/build_training_set.py`. Sanchit's two questions ("what is the training
input?", "how do we process the model?") are answered there with numbers.

The input is a **32×32 constellation-density image of the demodulated symbols**,
plus 4 scalars that act as a *quality gate* — not as a classifier. Measured:
every scalar is at chance (25% on 4 classes) for identifying the modulation,
because at a fixed `R_s` the envelope clock is identical for BPSK/QPSK/8PSK/
16QAM. The image is where the label lives: **93.2% alone, 97.7% with the
scalars** on 360 generated captures.

**The image must be built from `demodulate().symbols`, not from decimating the
raw capture.** Raw decimation leaves the carrier offset in place, so the points
smear into a ring — measured 25.3%, exactly chance. Consequence: **the CNN runs
after the demodulator front-end, not before it.**

> [!WARNING]
> **Corrected claim.** An earlier version of this file said to feed `SPS` "not
> raw IQ" because it was the key feature. `SPS` is still essential — as the
> demodulator's input — but it is **not** a modulation cue. Feed the
> constellation image.

### B2. Generate training data with known labels

Use `scratch/build_training_set.py` (which supersedes `make_ground_truth.py` for
this purpose — the latter generates only 3 files). Sweep the dimensions that
actually break things, not just the easy middle:

- symbol rate 25–250 ksps (low SPS is the hard regime)
- excess bandwidth α = 0.20 / 0.35 / 0.50 (**α=0.20 is the hard regime**)
- modulation: BPSK, QPSK, 8PSK, 16QAM
- at least 2 seeds, to catch lucky noise

Currently 360 captures. Scale to **several thousand** — it is minutes of
generation time. Then add the **fading** step from the Notion recipe
(`QPSK → AWGN → freq offset → phase offset → fading → coding`); it is the step
most likely to expose an overfitted feature.

Score it with `scratch/train_baseline_model.py` (stratified split, prints a
confusion matrix) — **not** by eyeballing a loss curve. Current measured result
is **97.7%** on 360 captures, chance 25%, with 100/100/100/91% recall on
BPSK/QPSK/8PSK/16QAM.

### B3. Make the model able to abstain

**Design rule, not a nicety.** All three real project captures report `LOW` symbol-rate
lock — they are synthetic with no clean pulse-shaping clock. A model forced to emit
a label on a weak measurement produces a confident wrong answer, which is the exact
failure mode this project exists to avoid.

Output `(label, confidence)` and let confidence gate abstention.

### B4. Wire the label into the demodulator

Replace the heuristic `modulation_class` at the gate — **at that point only**. Keep
the heuristic as a cross-check; a disagreement between the CNN and the heuristic is
itself useful signal, and worth logging.

### B5. Be honest in the write-up

Say "trained on generated ground truth". Do not claim real-file accuracy we cannot
demonstrate.

---

## 5. Workstream D — de-interleaving and FEC (unassigned)

The largest untouched area, and it is **two full problem-statement sections**. It
needs an owner before it becomes a scramble.

### D1. Interleaving detection — 4 modes required

Block, convolutional, diagonal, pseudo-random.

**Recommended approach — and it reuses a pattern we already proved.** We cannot
*directly observe* the interleaving depth any more than we can observe `f_s`. So
build it the same way we built the sample-rate resolver:

1. **Detect, or report that you cannot.** For each candidate mode and a small set
   of depths (e.g. 4–64), de-interleave and score the result. A correct
   de-interleaving makes the bitstream *structured* — burst errors collapse into
   scattered single errors, and a convolutional decoder's syndrome rate drops.
   That score is a real measurement.
2. **Label the confidence.** If no candidate beats the null hypothesis
   meaningfully, report `UNDETERMINED` with the best score. Do not guess.
3. **Reuse the honesty pattern.** Same shape as `SampleRateResult`: ranked
   candidates, a confidence label, and a refusal path that says why.

**Testable without a transmitter:** build an interleaver, interleave known bits,
then check the detector recovers them. That is ground truth we control.

### D2. FEC — start with Viterbi

Ordered by effort, and matching the problem statement:

1. **Convolutional codes + Viterbi** — start here. Well-specified, ground truth is
   easy to generate, and it is the most commonly encountered.
2. **Reed-Solomon** — block codes, standard implementations exist
   (`reedsolo` is small and pure-Python).
3. **Concatenated** — becomes easy once 1 and 2 exist.
4. **LDPC** — hardest; leave until the others are done, and consider whether the
   rubric needs it before spending the time.

**Key insight for detection:** an FEC-coded stream has *statistical structure* that
an uncoded one does not. The rate (1/2, 2/3, 3/4) can be probed by trying to decode
at each and checking whether the syndrome rate drops to near zero. Same
score-and-label pattern as D1.

### D3. Bitstream correlation and header detection

The end of the chain. Look for sync words / repeated patterns via autocorrelation,
and report frame candidates. Meaningful only after FEC works — decoding raw
interleaved noise for a header will find false positives.

---

## 6. Suggested sequencing

```
Now        A1  (5 lines, 16QAM starts working)
           B1  (Nimish starts; does not depend on anything)
           ↓
Next       A2  (8PSK fix; small, root cause known)
           B2  (needs A1/A2 for the full label set)
           ↓
Then       A3  (timing detector — biggest demodulator improvement left)
           B3  (abstention), B4 (wire in)
           ↓
Parallel   D1  (interleaving — needs an owner NOW)
           A4  (FSK)
           ↓
Last       D2  (FEC, Viterbi first)
           D3  (correlation)
           B5  (write-up)
```

**A1 and A2 together make four modulation families demodulable** (BPSK, QPSK,
8PSK, 16QAM) for a few hours of work, because the demodulator core already
handles them. That is the best return available right now.

---

## 7. Verification discipline (everyone, non-negotiable)

1. **Never claim a DSP stage works without scoring it against known ground truth.**
   An estimator that reports "100.00 ksps" looks identical whether it measured
   correctly or locked onto a leakage peak.
2. **Report refusals as refusals, separately from successes.** `NO LOCK` is correct
   behaviour. A confident wrong number is the actual failure.
3. **Sweep, do not spot-check.** One passing case proves nothing.
4. **Run everything in Radioconda**, not a dev Python — its numpy 2.2.x rejects
   `np.fft.rfft` on complex input outright.
5. **When a test fails, check whether the test is wrong.** A recent failure was an
   assertion that `96000` sym/s should match VDL2/AIS, which is `9600`. The module
   was right; the test was wrong. "Fixing" code to satisfy a bad test plants a bug.

### Reproduce every number in this document

```
"$USERPROFILE/radioconda/python.exe" scratch/run_all.py
```

Individual suites:

```
scratch/verify_symbol_rate.py      # symbol rate, 10/10
scratch/verify_wide.py             # demodulation, 46/46
scratch/verify_sample_rate.py      # provenance, 25/25
scratch/verify_demod_gate.py       # gate routing, 8/8
scratch/probe_8psk_16qam.py        # the A1 finding: 16QAM works, 8PSK does not
scratch/probe_power_matrix.py      # the A2 root cause: exponent matrix
```

---

## 8. What to say to judges

State the pipeline as: **"L1/L2/L3 are done and verified against generated ground
truth; the CNN is the layer we are integrating; de-interleaving and FEC are the
next stage."**

A truthful boundary scores better than a feature list that collapses under one
follow-up question.
