# SIGMA vs. the Notion plan — what matches, what does not

*Written 17 Sep 2026, after reading the team Notion page
`app.notion.com/p/sih-2026-3c731571abe8806e8546d97dfc960b68` and re-measuring the
code on the same day. Every claim about our side of the table was run, not
recalled.*

The Notion page is a **plan**. This document compares that plan against the
**measured state of the repository**. Where they agree, say so and move on.
Where they disagree, someone has to decide which one changes — and it should be
a decision, not an accident.

---

## 0. One-paragraph verdict

The Notion page and the code agree on **the shape of the pipeline** and on
**the problem statement**. They disagree on **the technology stack**, they
disagree on **what the CNN should eat**, and the page's worth-showing demo
depends on **two stages that have no code at all**. Three of the page's numbers
or features would be *misrepresentations* if demoed today. None of this is
fatal — the fix list is short — but it needs saying out loud before the demo.

---

## 1. The page's process chart vs. our pipeline

The Notion chart, left to right:

```
IQ/WAV → File Parser → Signal Processing → Signal Detection & Segmentation
       → AI/ML Classifier (CNN) → Signal Parameters → Demodulation
       → FEC/Deinterleave → Bit Stream Correlation → FINAL REPORT
```

Mapping onto what exists:

| Notion stage | Our implementation | Status |
|---|---|---|
| File Parser / IQ-WAV detection | L1 — `sigma_analyzer_core.py` decode + `sigma_sample_rate.py` | ✅ **done** |
| Signal Processing (FFT/PSD/SNR, Filtering) | L2 — Welch PSD, OBW, SNR, 4 live GNU Radio sinks | ✅ **done** |
| **Signal Detection & Segmentation** | **nothing** | ❌ **no code** |
| AI/ML Classifier (CNN) | heuristic classifier only | 🟡 **heuristic done, CNN not integrated** |
| Signal Parameters | L2 output dict + GUI metrics panel | ✅ **done** |
| Demodulation | L3 — `sigma_demod.py` | ✅ BPSK/QPSK done; 16QAM works but gated; 8PSK broken; FSK absent |
| FEC / Deinterleave | **nothing** | ❌ **no code** |
| Bit Stream Correlation | **nothing** | ❌ **no code** |
| FINAL REPORT | metrics panel exists; no export | 🟡 **partial** |

**The one row worth arguing about: "Signal Detection & Segmentation."** The page
puts it *before* the classifier, which is correct DSP order — you cannot classify
a signal you have not found. But it is also **the stage the problem statement
doesn't ask for** (PS §3 lists parameters, demodulation, de-interleaving, FEC,
correlation — not segmentation). Right now every file we have is a single
continuous signal, so segmentation has never been *needed*. That will change the
moment a capture contains two bursts at different frequencies. **Recommendation:
leave it out of the demo script, and if a judge asks, say plainly that our
captures are single-signal so segmentation is not on the critical path.** Do not
draw it in the architecture diagram if we are not building it.

---

## 2. The technology stack — this is the biggest divergence

Notion's "Your technology / Use in PS147" table:

| Notion says | What SIGMA actually is | Verdict |
|---|---|---|
| Python | Python 3, PyQt5, NumPy, SciPy | ✅ agree |
| NumPy | yes — all DSP | ✅ agree |
| Pandas | **not used anywhere** | ⚠️ aspirational |
| CNN | not yet integrated | 🟡 planned |
| ML | heuristic estimators only | 🟡 partial |
| **Flask** — backend/API | **does not exist** | ❌ **not built** |
| **MERN** — dashboard | **does not exist**; GUI is PyQt5 | ❌ **not built** |
| **Three.js** — 3D viz | **does not exist**; viz is GNU Radio QtGUI sinks (2-D) | ❌ **not built** |
| RAG — optional | nothing | ❌ not built |
| LLM — explain results | nothing | ❌ not built |
| Spectrogram/constellation classification | constellation sink exists; classification does not | 🟡 half |

**This is not a small gap.** The Notion page describes a **web application**
(Flask API + MERN dashboard + Three.js 3-D waterfall). SIGMA is a **native
desktop application** (PyQt5, with embedded GNU Radio Qt GUI sinks). These are
two different architectures, and only one of them is running.

Two honest ways to resolve it, and the team has to pick one:

1. **Keep the desktop app.** Rewrite the Notion table to match reality: PyQt5,
   embedded GNU Radio QtGUI sinks, no Flask/MERN/Three.js. Cheapest, and the
   demo already works this way. The "3-D waterfall" bullet becomes a 2-D
   waterfall, which is what GNU Radio actually ships and what the demo shows.
2. **Add a web layer.** Flask wraps the existing Python DSP core as an API;
   MERN renders the dashboard; Three.js does 3-D. This is real work — a second
   product surface — and it does not advance a single problem-statement
   requirement (§3 i–v are all DSP, not web).

**Recommendation: option 1, and be explicit about it.** The problem statement
says *"GUI-based model"* and asks for a GUI, not a website. Scoring is on the
pipeline. Spending the remaining time on a Flask API instead of FEC would be
optimising the wrong axis.

---

## 3. "Confidence: 96.4%" — please remove this from the page

The Notion process chart shows a mock signal-parameters box:

```
│ Modulation: QPSK  │
│ Symbol Rate: XXXX │
│ SNR: XX dB        │
│ Bandwidth: XXXX   │
│ Confidence: 96.4% │
```

and the demo script (Step 3) has the AI say:

> **Detected: QPSK**
> **Confidence: 96.7%**

**`96.4%` and `96.7%` are the exact figures that were removed from this codebase
as fake.** An earlier revision of `sigma_analyzer_core.py` returned hardcoded
confidences — `"96.4%"`, `"94.8%"`, `"92.1%"` — whenever the filename contained
`bpsk`/`qpsk`/`fm`/`rds`, and those constants *shadowed* the real measured
statistics computed immediately above them. Renaming a file changed the reported
modulation. It is documented as a warning in `docs/ARCHITECTURE.md` §2.4 and
guarded by a regression test: `bpsk_modulated_1msps.iq` renamed to
`anonymous_capture.iq` still reports `BPSK | measured`.

So the page is describing, as a target, the precise thing we deliberately
deleted.

**What we actually have to show instead** — and it is *better*, because it
survives a follow-up question:

| Instead of | Say |
|---|---|
| `Confidence: 96.4%` | `Symbol rate lock: LOW (6.6 dB above noise floor)` |
| a magic percentage | `SPS = 3.137` (measured — feeds the demodulator) |
| `Detection confidence` | `Carrier offset: +59,998 Hz` vs. a true 60,000 Hz |

The last one is the strongest single number in the project: a **2 Hz error** on a
signal we generated with a known offset, produced by the full chain running on
the *detected* symbol rate. That is evidence. A hardcoded `96.4%` is decoration,
and a judge who asks "how is confidence computed?" will find out.

---

## 4. What the CNN should eat — the page and the measurements disagree

Notion proposes two options:

> **IQ → constellation representation → CNN**
>
> or
>
> **IQ features + Spectrogram + Constellation ↓ Fusion model ↓ Modulation classification**

`docs/L1_L2_L3_ARCHITECTURE.md` §4.1 specifies something different, and the
reason is measured, not stylistic. **This section was revised on the same day it
was written — the first version made a claim the measurements then disproved.**

| # | Our CNN input | Why |
|---|---|---|
| 1 | **Constellation-density map, 32×32, of the *demodulated* symbols** | **the label lives here.** Measured 93.2% alone, 97.7% with the scalars |
| 2 | PSK-order candidate `{0,2,4}` | from `_detect_psk_order()` |
| 3 | `SPS` | feeds the **demodulator**, not the label — measured at chance as a modulation cue |
| 4 | Lock confidence | **gates abstention** |
| 5 | Occupied bandwidth | cross-check: `OBW/R_s ≈ 1 + α` |

**Why this matters in one line:** a raw-IQ CNN needs orders of magnitude more
training data than a five-person team can generate and label honestly. A
constellation image is already feature-engineered — carrier offset, timing and
rotation have been removed by the DSP chain — so the network only learns shape.
That is the honest choice at our data scale.

> [!WARNING]
> **The first version of this section said to feed `SPS` "plus four scalars"
> because `SPS` was the key feature. That was wrong.** Measured: at a fixed `R_s`
> the symbol-rate estimate is *identical* for BPSK/QPSK/8PSK/16QAM, and all four
> scalars score exactly chance (25% on 4 classes). `SPS` remains essential as the
> demodulator's input. See [`CNN_INPUT_AND_TRAINING.md`](CNN_INPUT_AND_TRAINING.md).

**A consequence for the page's flowchart.** The image must be built from
`demodulate().symbols` — post carrier-recovery, matched filter, timing and phase
correction. Decimating the raw capture leaves the carrier offset in place and the
points smear into a ring (measured 25.3%, exactly chance). So the CNN runs
**after** the demodulator front-end, not before. The Notion chart draws the
classifier *before* demodulation — that ordering is wrong for this design.

The page's **fusion model** (spectrogram + constellation) remains a reasonable
upgrade path once the constellation-only model works end-to-end. Neither the
spectrogram nor the constellation image is normalised against the unknown `f_s`,
so both inherit that ambiguity — but the constellation image at least resolves
the constellation itself, which is what carries the label.
**Recommendation:** ship the constellation model first; treat fusion as the
upgrade if time allows.

---

## 5. The "killer demo" — what we can and cannot do today

The page's 8-step script, audited against the running app:

| Step | Script says | Reality |
|---|---|---|
| 1 | Upload `unknown_signal.iq` | ✅ works |
| 2 | Show waterfall, spectrum, IQ waveform, constellation | ✅ all four are live GNU Radio sinks in the GUI |
| 3 | AI says "Detected: QPSK, Confidence: 96.7%" | ⚠️ **classification works and is measured-driven, but the number must not be a fake**; and on the three real captures lock is `LOW` — see §6 |
| 4 | Estimate sample rate, symbol rate, bandwidth, SNR, carrier offset, modulation | ✅ all six are computed and displayed. `f_s` is **resolved with provenance**, not "estimated" — say it that way |
| 5 | Click DEModulate | ✅ works; the DEMODULATION & BITSTREAM card shows state, method, symbols, bits, EVM, carrier offset, SPS, leading bits |
| 6 | Show recovered symbols → de-interleaving → FEC → bitstream | ⚠️ **symbols ✅, everything after the arrow ❌** |
| 7 | Show before-FEC `1011X010XX110...` vs after-FEC `1011001010110...` | ❌ **cannot be done — no FEC exists** |
| 8 | Generate automated signal analysis report | ❌ **no export/report generator** |

**So steps 1–5 are real and demo-ready. Steps 6 (the back half), 7 and 8 are
not.** The page calls this "a very good 3–5 minute SIH demo," and steps 1–5
genuinely are — that is a complete, honest demo of parameter extraction and
demodulation. The problem is only if we *promise* FEC and then cannot show it.

**Two acceptable paths:**

- **Path A (recommended): shorten the demo to what exists.** Steps 1–5 plus the
  measured carrier-offset accuracy, then state the boundary: *"de-interleaving
  and FEC are the next stage."* `TEAM_TASKS.md` §8 already frames this.
- **Path B: build the missing parts.** `FEC → Viterbi` is the cheapest of them
  (`TEAM_TASKS.md` §5 D2), and a Viterbi decoder on a generated convolutional-
  coded stream is genuinely demonstrable within the timeframe. That would make
  step 7 real. De-interleaving (D1) is larger. Correlation (D3) depends on FEC.

Either path is defensible. **Demoting step 7 from "will show" to "will show if
Viterbi lands" is the honest move.**

---

## 6. The awkward fact the page does not mention

`docs/L1_L2_L3_ARCHITECTURE.md` §5 records it, and I re-measured it today:

```
data/iq/signal.iq                  R_s=22,824.9  SPS=43.812  conf=LOW  prom=7.0 dB
data/iq/bpsk_modulated_1msps.iq    R_s=318,783.5 SPS=3.137   conf=LOW  prom=6.6 dB
data/iq/qpsk_modulated_1msps.iq    R_s=116,748.0 SPS=8.565   conf=LOW  prom=6.3 dB
```

**All three real project captures report `LOW` symbol-rate lock.** They are
synthetic files with no clean pulse-shaping clock, so the envelope line sits
only ~6–7 dB above the floor — just over the 6.0 dB lock threshold.

And the demodulator, when run directly on them, *does* produce bits:

```
BPSK  locked=True  EVM=20.59%  16666 symbols  head: 111111111111100000001111111111111111111100000000
QPSK  locked=True  EVM=31.87%   5556 symbols  head: 000000010101011111010101010110100000010111111111
```

That BPSK head — a long run of 1s then a long run of 0s — is the signature of a
**carrier/phase ambiguity**, not of a payload. These captures contain no real
data. The `LOCKED` state is technically correct (symbols came out) but the EVM
of 20–32% says the constellation is loose.

**Why this matters for the demo:** when the GUI gate requires `MEDIUM` or better
(it does — `sigma_main_window.py:1147`), it **declines to demodulate the real
project captures**. If the demo loads one of these and shows a bitstream, someone
edited the gate. The honest demo loads a **generated** capture with a known
payload, shows the bitstream matches, and separately shows the real captures
resolving their parameters with `LOW` confidence labelled as such.

The CNN will therefore be trained and demonstrated on **generated ground truth**
(`scratch/make_ground_truth.py`), and must be presented that way. This is not a
weakness to hide — it is the reason our numbers are trustworthy.

---

## 7. Where the page is exactly right (credit where due)

Worth saying, because these are the parts not to touch:

- **The pipeline order** is correct and matches ours. No argument.
- **"DSP should handle / ML should handle"** (sub-page *structure of model* §10)
  is a genuinely good separation and matches how we built it: DSP does parsing,
  FFT, PSD, SNR, bandwidth, synchronisation; ML does modulation classification,
  anomaly detection, and parameter estimation where conventional methods
  struggle. Our L1/L2 are pure DSP and our CNN boundary sits exactly there.
- **"GNU Radio should handle connecting signal-processing stages / streaming /
  visualisation"** — that is precisely what `sigma_flowgraph.py` does: GNU Radio
  owns the four live sinks, Python owns the analysis. Correct call.
- **"An FEC-coded stream has statistical structure an uncoded one does not"** —
  this is implied by the *synthetical synthesis* recipe and it is the right
  instinct. It is also exactly how `TEAM_TASKS.md` §5 D2 proposes to detect FEC
  rate: try each rate, check whether the syndrome rate collapses.
- **The synthetic synthesis recipe** — `Generate QPSK → AWGN → frequency offset
  → phase offset → fading → coding/interleaving → IQ → test` — is the right
  build order, and we already do the first five. Add fading last; it is the one
  step that can make an otherwise-working estimator look broken.
- **The waterfall/constellation emphasis** — correct. The constellation diagram
  *is* the most persuasive visual for modulation classification, and it is
  already on screen.
- **"There are public RF datasets"** — true, and worth pursuing for the CNN
  (`IQEngine`, DeepSig RML2016/RML2018, RadioML). But see §4: more data does not
  fix the `f_s` normalisation problem.

---

## 8. The decision list

Things that need a human decision, in priority order:

1. **Flask + MERN + Three.js: in or out?** Pick one. If out, rewrite the Notion
   tech table. This blocks nothing technically but everything strategically —
   two people cannot build a web app and a DSP pipeline in the same week.
2. **Remove `96.4%` / `96.7%` from the Notion page** and replace with real
   measured quantities (§3). Half-hour job; prevents a bad demo.
3. **Does the demo include FEC?** If yes, someone owns Viterbi now
   (`TEAM_TASKS.md` §5 D2). If no, cut steps 6–8 to "next stage."
4. **Assign an owner to Workstream D.** De-interleaving + FEC is **two of the
   five problem-statement sections** and is currently unassigned — the single
   biggest risk on the board.
5. **CNN input: scalars-first or fusion-first?** Recommend scalars-first (§4).

---

## 9. Cross-references

- `docs/L1_L2_L3_ARCHITECTURE.md` — the architecture the team asked for, §4.1
  is the CNN contract
- `docs/TEAM_TASKS.md` — the work breakdown, §5 is the unassigned risk
- `docs/ARCHITECTURE.md` §2.4 — the hardcoded-confidence warning
- `docs/VERIFICATION.md` §3.2 — why `f_s` is resolved, not measured
- `docs/SIH_PROBLEM_STATEMENT.md` — PS 6147 §3, the five requirements
