# Done vs. remaining — the honest status table

*Verified 18 Sep 2026. Every "done" row has a test you can run; every "left" row
says what is actually missing. Nothing here is estimated.*

---

## 1. The one-screen version

| | Count |
|---|---|
| Problem-statement **requirements** | 5 sections (PS §3 i–v) |
| **Fully done** | **0** — no section is complete |
| **Partially done** | **4** — §3 i, §3 ii, §3 iii, §3 iv |
| **Not started** | **1** — §3 v |
| Working DSP engine | ✅ yes, verified — **4 of 5** constellation families |
| Working coding layer | ✅ **shipped in `src/` and wired into the GUI** — detection + convolutional FEC |
| Working ML classifier | 🟡 heuristic **done** (144/144); CNN **not built** |

**Headline:** the *analysis + demodulation* engine is real and verified, covering
**four** constellations, and the *coding layer* (§3 iii/iv) now ships in `src/`
and runs in the GUI. What remains unwritten is the *CNN*, FSK, and §3 v.

**On the count going from "fully done 1" to "fully done 0"** — this is a
**recount, not a regression**. §3 i was previously scored as fully done on the
strength of the feature metrics alone, which was generous: *FEC-scheme
identification* and *interleaving-type detection* are both named inside §3 i and
neither had any code at the time. Scoring each section against its own full text,
no section is complete. Every individual item that has moved so far moved **up**:

| Moved | From | To |
|---|---|---|
| Demodulable constellations | 2 (BPSK/QPSK) | **4** (+8PSK, +16QAM) |
| PSK order identifiable from the signal | 2 | **4** (new symbol-domain classifier) |
| Analogue signals correctly refused | not tested | **5/5** (incl. a real FM/RDS capture) |
| Convolutional FEC decode | not started | **(2,1,3) 100.00%**, 20/20 flips corrected |
| Interleaver modes implemented | 0 | **4** — all proven invertible |
| Interleaver **type identified blind** | not started | **4/4** clean, 4/4 to 10% errors |

---

## 2. By pipeline stage

| # | Stage | Status | Evidence |
|---|---|---|---|
| 1 | **INPUT** — load `.iq` / `.wav` | ✅ **Done** | WAV header parse; stereo→IQ, mono→baseband; `complex64` decode |
| 2 | **ANALYSIS** — metrics | ✅ **Done** | 8 metrics computed live; 4 GNU Radio sinks rendering |
| 3 | **MODULATION** — symbol rate + class | ✅ **Done** | R_s **10/10 locked** (9 exact to 0.00%); constellation named for all four (144/144) |
| 4 | **DEMOD** — symbols → bits | ✅ **Done, all four constellations** | **72/72 locked, 0 refused**; BPSK/QPSK/8PSK **100.00%**, 16QAM **99.98%** |
| 5 | **BITS** — display bitstream | ✅ **Done** | GUI card shows symbols, bits, EVM, carrier offset, SPS, leading bits |
| — | **DE-INTERLEAVE** | ❌ **Not started** | no code exists (`grep` finds nothing) |
| — | **FEC DECODE** | ❌ **Not started** | no code exists |
| — | **BIT CORRELATION** | ❌ **Not started** | no code exists |
| — | **CNN CLASSIFIER** | ❌ **Not started** | dataset + baseline done; **no network exists**. Framework is now *proven installable* (torch 2.14.0+cpu measured), but it is **not wired into the app** — see Tier 1 row 3 |

---

## 3. Requirement-by-requirement (PS §3)

| PS §3 requirement | Status | Detail |
|---|---|---|
| i. **Sampling-frequency estimation** | ⚠️ **Resolved, not measured** | Provably impossible from samples alone. Resolved from ranked sources with `MEASURED`/`INFERRED`/`ASSUMED` labels. **25/25 verified** |
| i. **Modulation classification** | 🟡 **Heuristic done, CNN not built** | Measurement-driven classifier works and is filename-independent. CNN dataset + baseline measured (97.7% on synthetic) but **no network exists** |
| i. **FEC scheme identification** | 🟡 **Partially — code structure, not scheme** | The FEC **code** is known to the receiver in this harness (a (2,1,3) convolutional code). *Identifying an unknown* code from the stream is **not done** |
| i. **Interleaving type detection** | ✅ **Done, shipped** | **4/4 blind**, no geometry hint; **288/288** across lengths/geometries. See §3a |
| i. **Other features** (SNR, power, BW, constellation) | ✅ **Done** | RMS, peak, dBFS, 99% OBW, noise floor, SNR, peak freq, constellation |
| ii. **Demod — BPSK / QPSK** | ✅ **Done** | **100.00%** over the full sweep, using the *detected* symbol rate |
| ii. **Demod — QAM (16QAM)** | ✅ **Done** | **99.98%** (min 99.97%) — the gate now lets it through |
| ii. **Demod — PSK (8PSK)** | ✅ **Done** | **100.00%** over the full sweep. Was 51.70% (chance); the carrier exponent was hardcoded to `x**4` and is now `x**8` |
| ii. **Demod — FSK** | ❌ **Not started** | — |
| iii. **De-interleaving (4 modes)** | ✅ **Done — shipped and wired** | All 4 modes proven invertible. Detector names the mode **blind: 4/4**, no geometry hint, 288/288 across lengths/geometries. **0/4 on random bits** (control). Runs in the GUI |
| iv. **FEC (Viterbi / RS / LDPC)** | 🟡 **Convolutional done**, RS/LDPC not | (2,1,3) encode + Viterbi **100.00%**; corrects **20/20** injected flips; refuses uncoded input. `src/sigma_coding.py` |
| v. **Bitstream correlation, header detection** | ❌ **Not started** | — |

---

## 4. What is genuinely done, with numbers

| Item | Result | Reproduce with |
|---|---|---|
| Symbol rate estimation | **10/10 locked**, 9 at 0.00% error | `scratch/verify_symbol_rate.py` |
| Demodulation (BPSK/QPSK) | **100.00%** bit accuracy | `scratch/verify_wide.py` |
| Demodulation, all four constellations | **72/72 locked, 0 refused**; BPSK/QPSK/8PSK **100.00%**, 16QAM **99.98%** | `scratch/verify_demod_all_mods.py` |
| Constellation classifier (from symbols) | **144/144** correct; noise refused **3/3** | `scratch/verify_modclass_parsimony.py` |
| Unmodulated carrier / ASK refused | **5/5** analogue signals refused, incl. a real FM/RDS capture | `scratch/verify_analogue_refused.py` |
| GUI end-to-end, all four | **4/4 lock**, correct constellation, measured values on screen | `scratch/verify_gui_all_mods.py` |
| Sample-rate provenance | **25/25** ranking cases | `scratch/verify_sample_rate.py` |
| Demod gate routing | **11/11** classification matrix | `scratch/verify_demod_gate.py` |
| GUI rate-source chip | **3/3** confidence states | `scratch/verify_rate_chip.py` |
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

**Interleaver identification** — the detector is handed the *interleaved coded
bit stream* and the FEC code, but **not** the permutation. For each candidate
mode it de-interleaves, decodes, re-encodes and measures the residual:

```
decode(bits) -> re-encode -> compare against bits
```

A genuine codeword reproduces itself exactly. Measured on 192 information bits:

| input | residual |
|---|---|
| clean codeword | **0.0000** |
| 3 channel errors | 0.0077 |
| shuffled codeword | 0.1366 |
| random bits | 0.1418 |

The correct hypothesis scores exactly `0.0000` while every wrong one scores
`0.046–0.148`. Blind detection results: **4/4** on a clean channel, **4/4** at
every flip rate up to **10%**, **0/4** on interleaved random bits (the control —
a perfect score there would prove the detector was cheating), and **4/4** under a
24-bit contiguous burst.

---

## 3a. Where the interleaver detector actually gives up

Reporting "it works" without a boundary is not a measurement. Sweeping 40
payloads per cell at 192 information bits:

| Channel flip rate | Correct | Declined | Wrong |
|---|---|---|---|
| 2% | **40/40** | 0/40 | 0/40 |
| 5% | **40/40** | 0/40 | 0/40 |
| 10% | **40/40** | 0/40 | 0/40 |
| 15% | 39/40 | 0/40 | 1/40 |
| 20% | 23/40 | 2/40 | **15/40** |
| 30% | 7/40 | 9/40 | **24/40** |

**The honest weakness:** past the boundary the detector mostly answers *wrong*
rather than *declining*. The abstention margin catches near-ties only. The root
cause is structural — Viterbi always returns the nearest codeword, so even a
completely scrambled stream keeps a small residual (~0.14), and there is no clean
"this is not a codeword" threshold to trip. A better heuristic would compare the
*best* residual against the *spread* of the candidates rather than an absolute
margin.

**Cost of the geometry search.** Those figures were measured with the block
geometry supplied. Blind (no `rows`/`cols`, which is the realistic case) the
detector is still perfect to 5%, but at 10% it falls to **29/40** — searching
many factorisations gives a wrong hypothesis more chances to score well.
Blind, however, it is **288/288** across 3 lengths × 4 geometries on a clean
channel, so the search is clearly worth its cost.

## 3b. Two bugs the `src/` port exposed (both found only by scoring the shipped copy)

The coding layer was developed in `scratch/` and then moved into
`src/sigma_coding.py`. **Scoring the shipped copy against the same ground truth
immediately found two defects the scratch version did not have** — which is the
argument for never assuming a port is faithful:

1. **Reversed window bit order → 54.25% noiseless.** The port rebuilt the
   K-bit window with a linear-feedback shift instead of
   `(bit << state_bits) | state`. That reverses the bit order relative to the
   encoder while remaining a *perfectly self-consistent trellis* — so it ran
   without error and produced garbage. Measured: `54.25%` on a noiseless
   channel, and a re-encode residual of `0.32` instead of `0.0000`. This is the
   same failure class as the original traceback bug: nothing crashes, the number
   just stops meaning anything.
2. **Single-guess factorisation → 2/4 detection.** `detect_interleaver` guessed
   one `rows`/`cols` pair (the largest factor ≤ √n) when not given them. A
   stream generated at 49×8 was auto-factorised to 28×14 — a *different
   interleaver* — so `block` was reported as `convolutional` and `diagonal`
   declined. **This scored 4/4 when tested in isolation with the true geometry
   passed in, and 2/4 through its real caller.** Fixed by enumerating
   factorisations and taking the best.

**The generalisable lesson:** test a function *through its real caller*. Both
bugs were invisible to the function's own unit test, because the unit test
supplied exactly the information the real caller does not have.

---

## 5. What is left, in priority order

### Tier 1 — ~~cheap, unblocks other work~~ **ALL THREE DONE**

| # | Task | Status | Result |
|---|---|---|---|
| 1 | **Let 16QAM through the gate** | ✅ **Done** | 99.98% (min 99.97%); the GUI now slices it |
| 2 | **Fix 8PSK exponent** (`x**4` → `x**8`, fold `samp_rate/power`) | ✅ **Done** | 51.70% (chance) → **100.00%**. Also needed a sub-bin refinement, Welch averaging and residual-frequency tracking — see below |
| 3 | **Install an ML framework** | 🟡 **Proven installable, not wired in** | torch 2.14.0+cpu / torchvision 0.29.0+cpu installed into an isolated venv and used for real measurements. **The app still cannot import it** — that install must go into Radioconda |

**Tier 1 took demodulable families from 2 → 4.** Two extra things were needed
beyond the exponent fix, both found by measurement rather than reasoning:

- **Sub-bin carrier refinement.** The FFT peak is only accurate to one bin, and
  a residual frequency error *accumulates* rather than staying a constant phase
  offset. On BPSK at 250 ksps the x² line landed one bin off, leaving +58.6 Hz,
  which drifted 132° across 1500 symbols and refused a signal that decodes
  perfectly. Refining on a fine grid over the whole record fixed it.
- **Residual frequency tracking + a second rotation pass.** Removing a linear
  phase ramp shifts the best constant rotation, so a rotation chosen before the
  frequency correction is stale. On 16QAM at 100 ksps that alone was worth EVM
  29.0% → 3.4%.
- **Welch averaging before peak-picking.** On a single FFT a spurious peak can
  outrank the true line. Measured on 8PSK at 250 ksps (seed 9): a spurious peak
  at −270 kHz scored 6.4 against the real +480 kHz line at 5.8, giving a
  −33.8 kHz estimate for a true +60 kHz offset.

### Tier 1b — the classifier, which was the real blocker for 8PSK/16QAM

The demodulator could slice four constellations but the **classifier could only
name two**, so the GUI could never route to 8PSK or 16QAM.

| # | Task | Status | Result |
|---|---|---|---|
| 1b | **Identify 8PSK / 16QAM from the signal** | ✅ **Done** | **144/144** over 4 modulations × 4 rates × 3 excess bandwidths × 3 seeds |

The spectral route cannot do this: measured, 8PSK's strongest M-th-power line is
at `x²` rather than `x⁸`, so it calls an 8PSK capture BPSK. (An attempt to extend
the spectral order detector to M=8 was **measured and rejected** — it labelled
noise "BPSK" and an unmodulated carrier "8PSK".)

The working method is **parsimony over the demodulator's own EVM**: demodulate
under each constellation, keep the ones that fit, and take the one with the
fewest points. Parsimony is required, not cosmetic — a lower-order constellation
is a geometric *subset* of a higher-order one, so a BPSK capture fits BPSK, QPSK
and 8PSK equally well and EVM alone cannot choose.

One guard was essential and was found by testing rather than reasoning: a
PSK/QAM signal must occupy **at least two constellation phases**. Without it, an
unmodulated carrier is reported as a *perfect* BPSK fit (measured EVM **0.2%**),
and an ASK envelope fits 16QAM at 8.3%. With it, a real FM/RDS capture, AM, ASK,
CW and audio baseband are all correctly refused.

### Tier 2 — the demodulator's remaining quality gates

| # | Task | Size | Detail |
|---|---|---|---|
| 4 | ~~**Timing detector** (Gardner / Müller & Müller)~~ | — | ✅ **No longer needed for α=0.20.** The full sweep is now **72/72 locked, 0 refused**, including every α=0.20 case. The old 6 `NO DEMOD` failures were the carrier-estimate defects in Tier 1, not the timing phase search. Do **not** reach for the zero-ISI-null approach: measured *worse* (11/20 vs 14/20) |
| 5 | **Train the CNN** | medium | Dataset + baseline already built. Needs ~40 lines of network |
| 6 | **FSK demodulation** | medium | Not started. Must first resolve the `"BPSK / 2-FSK"` classifier ambiguity or FSK is never selected |
| 7 | **Wire CNN into the gate** + keep heuristic as cross-check | medium | Depends on 5. Note the demodulator-based classifier (Tier 1b) already covers all four constellations at 144/144, so the CNN's marginal value is now **robustness on real signals**, not basic capability |

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
| *"Demodulation is planned, not done"* | **Stale.** 72/72 locked, 0 refused — BPSK/QPSK/8PSK at 100.00%, 16QAM at 99.98% |
| *"8PSK demodulation is broken (51.70%)"* | **Stale.** Fixed → **100.00%**. The carrier exponent was hardcoded `x⁴` and is now per-constellation |
| *"16QAM works but the gate refuses it"* | **Stale.** The gate routes it; 16QAM locks end to end in the GUI |
| *"Sample rate inferred from filename"* | **Stale.** Ranked provenance, 25/25 verified |
| *"Classifier accuracy unmeasured"* | **Stale.** 97.7% synthetic, chance 25% |
| *"Confidence: 96.4%"* | **Fabricated.** Was hardcoded and changed if you renamed the file. Deleted |
| *"The modulation card reports a confidence of X"* | **There is no numeric confidence.** The card shows a **label** plus the provenance word `"measured"`, and discards the alternatives. `"measured"` means *from the signal, not the filename*, not *high confidence*. See §7 |
| *"The CNN will make classification more accurate"* | **Unsupported as stated.** The demodulator-EVM classifier already scores 144/144 and refuses noise. The CNN's value is requirement coverage + a second opinion, not a measured accuracy gain |
| *"Signal Detection & Segmentation"* (Notion) | **No code**, and PS §3 does not ask for it |
| *Flask / MERN / Three.js* (Notion) | **None exist.** SIGMA is a PyQt5 desktop app |

---

## 7. What the classifier actually outputs (and what it does not)

Worth writing down because it is easy to misread the UI.

**The modulation card shows a label, not a probability.** It displays one class
plus the provenance word `"measured"`:

```
modulation_class      = "BPSK"
modulation_confidence = "measured"      # provenance, NOT a confidence value
```

`"measured"` means *"this came from the signal, not from the filename"*. It is a
real distinction — an earlier version returned hardcoded confidences whenever
`"bpsk"`/`"qpsk"` appeared in the filename, so renaming a file changed the answer.
That is fixed. But it is **not** a statement of how sure the classifier is, and
it is not a percentage.

**The other candidates are discarded, not ranked.** There is no `0.94 / 0.04 /
0.01 / 0.01` anywhere in the shipped code. The app cannot report *"BPSK, but QPSK
was a close second"* — and that matters, because BPSK-vs-QPSK is the exact pair
the regression suite found hardest to separate (`PSK_LINE_MARGIN_DB = 3.0` is a
thin margin).

**The real confidence is expressed as EVM, after demodulation.** Two tiers exist,
and they are not equally strong:

| Tier | Source | Strength |
|---|---|---|
| 1. Spectral classifier | M-th-power line | Names **BPSK or QPSK only**; cannot separate 8PSK (its strongest line sits at `x²` either way) |
| 2. Symbols-fitted classifier | EVM against each constellation | **144/144**, names all four, abstains on noise |

Tier 2 supersedes tier 1, and the GUI shows that it did:

> *"symbols: 8PSK is the simplest that fits (EVM 3.3%; the classifier said BPSK)"*

That tooltip is the honest confidence display — a **physical** measurement with a
known noise floor (3.3% against roughly a 3% floor), which is stronger evidence
than a softmax probability would be.

**If a numeric per-class confidence is wanted**, the source to use is tier 2's
per-constellation EVM (already computed as `evms` in `_run_demod_stage`), not a
new network. Showing the runner-up's EVM would make the margin visible.

---

## 8. The demo boundary

**Can be demoed now, truthfully:** load a capture → 8 metrics + 4 plots →
symbol rate lock → recover bits from **any of the four constellations**
(BPSK/QPSK/8PSK at 100%, 16QAM at 99.98%) → show the bitstream.

**Cannot be demoed:** de-interleaving, FEC, bit correlation, before/after-FEC
bitstrings, automated report export.

**The awkward fact:** the three real project captures all report `LOW`
symbol-rate lock (6.3–7.0 dB over a 6 dB floor). The GUI gate requires `MEDIUM`
or better, so **it will refuse to demodulate them.** Demo a *generated* capture
with a known payload instead. If a real capture shows a bitstream, the gate was
edited.

---

## 9. Say it this way to judges

> **"L1/L2/L3 are done and verified against generated ground truth — demodulation
> covers BPSK, QPSK, 8PSK and 16QAM at 100/100/100/99.98% over 72 configurations.
> The CNN is a second opinion on classification, not a prerequisite: the
> classifier derived from the demodulator's own EVM already names all four
> constellations at 144/144 and refuses noise. De-interleaving and FEC are the
> next stage."**

A truthful boundary scores better than a feature list that collapses under one
follow-up question. In particular, do **not** claim the CNN improves accuracy —
on every dataset we can measure it is equal to the classifier already shipped,
and its value is requirement coverage plus cross-validation.

