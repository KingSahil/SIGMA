# Done vs. remaining — the honest status table

*Verified 17 Sep 2026. Every "done" row has a test you can run; every "left" row
says what is actually missing. Nothing here is estimated.*

---

## 1. The one-screen version

| | Count |
|---|---|
| Problem-statement **requirements** | 5 sections (PS §3 i–v) |
| **Fully done** | **1** (§3 i, partially — see caveat) |
| **Partially done** | **2** |
| **Not started** | **2** |
| Working DSP engine | ✅ yes, verified |
| Working ML classifier | ❌ no model, no framework installed |

**Headline:** the *analysis + demodulation* engine is real and verified. The
*coding layer* (interleaving + FEC) and the *ML model* do not exist.

---

## 2. By pipeline stage

| # | Stage | Status | Evidence |
|---|---|---|---|
| 1 | **INPUT** — load `.iq` / `.wav` | ✅ **Done** | WAV header parse; stereo→IQ, mono→baseband; `complex64` decode |
| 2 | **ANALYSIS** — metrics | ✅ **Done** | 8 metrics computed live; 4 GNU Radio sinks rendering |
| 3 | **MODULATION** — symbol rate + class | ✅ **Done** | R_s **10/10 locked** (9 exact to 0.00%); PSK order measured |
| 4 | **DEMOD** — symbols → bits | 🟡 **Partial** | BPSK/QPSK **46/46 at exactly 100.00%**; 16QAM works but gated; 8PSK broken |
| 5 | **BITS** — display bitstream | ✅ **Done** | GUI card shows symbols, bits, EVM, carrier offset, SPS, leading bits |
| — | **DE-INTERLEAVE** | ❌ **Not started** | no code exists (`grep` finds nothing) |
| — | **FEC DECODE** | ❌ **Not started** | no code exists |
| — | **BIT CORRELATION** | ❌ **Not started** | no code exists |
| — | **CNN CLASSIFIER** | ❌ **Not started** | dataset + baseline done; **no model, no ML framework** |

---

## 3. Requirement-by-requirement (PS §3)

| PS §3 requirement | Status | Detail |
|---|---|---|
| i. **Sampling-frequency estimation** | ⚠️ **Resolved, not measured** | Provably impossible from samples alone. Resolved from ranked sources with `MEASURED`/`INFERRED`/`ASSUMED` labels. **25/25 verified** |
| i. **Modulation classification** | 🟡 **Heuristic done, CNN not built** | Measurement-driven classifier works and is filename-independent. CNN dataset + baseline measured (97.7% on synthetic) but **no network exists** |
| i. **FEC scheme identification** | ❌ **Not started** | — |
| i. **Interleaving type detection** | ❌ **Not started** | — |
| i. **Other features** (SNR, power, BW, constellation) | ✅ **Done** | RMS, peak, dBFS, 99% OBW, noise floor, SNR, peak freq, constellation |
| ii. **Demod — BPSK / QPSK** | ✅ **Done** | **46/46 at exactly 100.00%**, using the *detected* symbol rate |
| ii. **Demod — QAM (16QAM)** | 🟢 **Works, gate blocks it** | **99.98%** measured; GUI refuses it — ~5-line fix |
| ii. **Demod — PSK (8PSK)** | 🔴 **Broken, cause known** | 51.70% = random. `estimate_carrier_offset()` hardcodes `x**4`, needs `x**8` |
| ii. **Demod — FSK** | ❌ **Not started** | — |
| iii. **De-interleaving (4 modes)** | ❌ **Not started** | block / convolutional / diagonal / pseudo-random — none |
| iv. **FEC (Viterbi / RS / LDPC)** | ❌ **Not started** | — |
| v. **Bitstream correlation, header detection** | ❌ **Not started** | — |

---

## 4. What is genuinely done, with numbers

| Item | Result | Reproduce with |
|---|---|---|
| Symbol rate estimation | **10/10 locked**, 9 at 0.00% error | `scratch/verify_symbol_rate.py` |
| Demodulation (BPSK/QPSK) | **46/46 at exactly 100.00%** bit accuracy | `scratch/verify_wide.py` |
| Sample-rate provenance | **25/25** ranking cases | `scratch/verify_sample_rate.py` |
| Demod gate routing | **8/8** classification matrix | `scratch/verify_demod_gate.py` |
| GUI rate-source chip | **3/3** confidence states | `scratch/verify_rate_chip.py` |
| 16QAM (bypassing gate) | **99.98%** | `scratch/probe_8psk_16qam.py` |
| Carrier-recovery exponent matrix | each constellation correct at its own order | `scratch/probe_power_matrix.py` |
| CNN feature pipeline | **97.7%** on 360 synthetic captures (chance 25%) | `scratch/train_baseline_model.py` |
| All of the above at once | — | `scratch/run_all.py` |

**Symbol rate** — measured from envelope cyclostationarity (Welch-averaged FFT of
`|x[n]|²`, nfft=16384). At nfft=1024 the error was ±42%; at 16384 it is 0.00%.

**Demodulation** — carrier recovery (M-th power) → RRC matched filter → timing
search → constellation-symmetry phase search → decisions. **100% on 46
configurations** spanning BPSK/QPSK × 25–250 ksps × α=0.20/0.35/0.50 × 2 seeds,
using the *detected* symbol rate rather than the true one.

**Sample rate** — proven unmeasurable: 1000 samples with a clock every 10 is
byte-identical to 2× rate with a clock every 20. So it is *resolved and labelled*
(USER > WAV header > PROTOCOL > FILENAME > DEFAULT) instead of pretended-measured.

---

## 5. What is left, in priority order

### Tier 1 — cheap, unblocks other work

| # | Task | Size | Why it matters |
|---|---|---|---|
| 1 | **Let 16QAM through the gate** | ~5 lines | Adds a whole modulation family. Already 99.98% — the gate is the only obstacle |
| 2 | **Fix 8PSK exponent** (`x**4` → `x**8`, fold `samp_rate/power`) | small | Adds another family. Root cause measured |
| 3 | **Install an ML framework** (torch/tensorflow — currently **none installed**) | 10 min | Hard blocker: no model can be trained or run without it |

**Tier 1 alone takes demodulable families from 2 → 4**, because the demodulator
core already handles them.

### Tier 2 — the demodulator's remaining quality gates

| # | Task | Size | Detail |
|---|---|---|---|
| 4 | **Timing detector** (Gardner / Müller & Müller) | medium | Fixes α=0.20 — 6 cases currently report `NO DEMOD`. Do **not** use the zero-ISI-null approach: measured *worse* (11/20 vs 14/20) |
| 5 | **Train the CNN** | medium | Dataset + baseline already built. Needs ~40 lines of network |
| 6 | **FSK demodulation** | medium | Not started. Must first resolve the `"BPSK / 2-FSK"` classifier ambiguity or FSK is never selected |
| 7 | **Wire CNN into the gate** + keep heuristic as cross-check | medium | Depends on 5 |

### Tier 3 — the two unstarted problem-statement sections

| # | Task | Size | Detail |
|---|---|---|---|
| 8 | **De-interleaving, 4 modes** | large | block / convolutional / diagonal / pseudo-random. **No owner** |
| 9 | **FEC — Viterbi first** | large | then Reed-Solomon → concatenated → LDPC |
| 10 | **Bitstream correlation / header detection** | medium | Depends on 9 — correlating raw noise finds false positives |

> Two of these — **blind de-interleaver** and **blind FEC** identification — are
> open research problems, not backlog tickets. The consumer analysis flags treating
> them as tickets as *"the single largest risk to credibility with the actual end
> consumer, who will know this."*

### Tier 4 — production gaps (not in the PS, but users need them)

| # | Task | Why |
|---|---|---|
| 11 | **`int8` / `int16` IQ support** | Currently **`complex64` only** (hardcoded). The most common SDR formats load as noise with a silently wrong sample count. Consumer doc flagged this; **still true** |
| 12 | **Export** — JSON / SigMF sidecar / report | Segment D's entire job is a report that doesn't exist |
| 13 | **Session persistence** | No save/revisit. Handoff between analysts is impossible |
| 14 | **Batch processing** | Triage of a queue is manual, one file at a time |
| 15 | **Cross-platform** | Audio is Windows-only (`winsound`); this domain runs Linux |
| 16 | **Classifier validation at operational SNR** | 97.7% is on *self-generated* data — not real-world accuracy |

---

## 6. Known false or stale claims (do not repeat these)

| Claim | Reality |
|---|---|
| *"SPS is the most informative CNN feature"* | **False, measured.** All 4 scalars are at chance (25%) on 4 classes. The constellation image carries the label. Corrected in 3 docs |
| *"Demodulation is planned, not done"* | **Stale.** 46/46 at 100% |
| *"Sample rate inferred from filename"* | **Stale.** Ranked provenance, 25/25 verified |
| *"Classifier accuracy unmeasured"* | **Stale.** 97.7% synthetic, chance 25% |
| *"Confidence: 96.4%"* | **Fabricated.** Was hardcoded and changed if you renamed the file. Deleted |
| *"Signal Detection & Segmentation"* (Notion) | **No code**, and PS §3 does not ask for it |
| *Flask / MERN / Three.js* (Notion) | **None exist.** SIGMA is a PyQt5 desktop app |

---

## 7. The demo boundary

**Can be demoed now, truthfully:** load a capture → 8 metrics + 4 plots →
symbol rate lock → recover bits from BPSK/QPSK at 100% → show the bitstream.

**Cannot be demoed:** de-interleaving, FEC, bit correlation, before/after-FEC
bitstrings, automated report export.

**The awkward fact:** the three real project captures all report `LOW`
symbol-rate lock (6.3–7.0 dB over a 6 dB floor). The GUI gate requires `MEDIUM`
or better, so **it will refuse to demodulate them.** Demo a *generated* capture
with a known payload instead. If a real capture shows a bitstream, the gate was
edited.

---

## 8. Say it this way to judges

> **"L1/L2/L3 are done and verified against generated ground truth; the CNN is
> the layer we are integrating; de-interleaving and FEC are the next stage."**

A truthful boundary scores better than a feature list that collapses under one
follow-up question.
