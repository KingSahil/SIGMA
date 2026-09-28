# Verification — how every DSP number was proven

*Companion to [`L1_L2_L3_ARCHITECTURE.md`](L1_L2_L3_ARCHITECTURE.md). Read this
before quoting any figure from the project.*

---

## Why this document exists

Signal-processing code fails in a specific and dangerous way: **it produces a
confident, precise, wrong number.** An estimator reporting `100.00 ksps` looks
byte-for-byte identical whether it measured the symbol rate or locked onto a
leakage peak. A constellation diagram that "looks like QPSK" is not evidence.

So the rule adopted here is:

> **No DSP stage is claimed to work until it has been scored against a
> known-correct answer, over many configurations.**

Everything below was measured. Where something does not work, it is listed as
not working.

---

## 1. The ground-truth harness

The project's own captures are synthetic and carry **no recoverable symbol
clock** (every 4th-power peak sits at exactly `f_s × 0.4`, regardless of file
content). They therefore cannot be used to verify anything. We generate
signals where the answer is known by construction.

| Script | Role |
| :--- | :--- |
| `scratch/make_ground_truth.py` | RRC pulse-shaping + signal synthesis with known `R_s`, modulation, α |
| `scratch/verify_symbol_rate.py` | Symbol-rate accuracy vs known `R_s` |
| `scratch/verify_demod.py` | Bit accuracy vs known transmitted bits |
| `scratch/verify_wide.py` | 46-case sweep across modulation × rate × α × seed |
| `scratch/run_all.py` | Runs all **17**. **This is the command you want.** |
| `scratch/fec_ground_truth.py` | `(2,1,3)` convolutional encode/decode + the four interleaver modes, with invertibility and burst proofs |
| `scratch/verify_interleaver_detect.py` | Names the interleaver **blind** from the coded stream |
| `scratch/verify_coding_module.py` | Scores the **shipped** `src/sigma_coding.py`, incl. the uncoded-refusal safety property |
| `scratch/verify_coding_gui.py` | The coding layer through the real window, widget text read back |
| `scratch/header_ground_truth.py` | Sync-word search + the chance-threshold table for PS §3 v |
| `scratch/verify_provenance_label.py` | The modulation card reports a **source**, not a confidence — all four provenance strings read back from the widget |
| `scratch/fec_scheme_search.py` | PS §3 i ground truth: five codes recovered, the margin over the runner-up, and the control showing a bare argmin claims a scheme for 12/12 noise streams |
| `scratch/verify_scheme_search.py` | The same against the **shipped** module + GUI, the fast path's blind spot (0/16), and the deep search that closes it (16/16 for K ≤ 7) |
| `scratch/verify_default_view.py` | Proves the GUI's *default* view completes the pipeline |
| `scratch/verify_demod_panel.py` | Proves the DEMODULATION card shows real values, and the refusal shows a reason |
| `scratch/measure_real_display.py` | Measures window/content fit on the **real** screen |
| `scratch/verify_launch_and_refusal.py` | Proves the app launches **and** still declines untrusted input |
| `scratch/ui_probe.py` | Builds the real window offscreen, reads widget text back |
| `scratch/launch_smoke.py` | Launches the real GUI (not offscreen) for 4 s |

### Running it

```powershell
& "$env:USERPROFILE\radioconda\python.exe" scratch\run_all.py
```

**Run this in Radioconda**, not a managed Python — see §5.

---

## 2. Results

### 2.1 Symbol rate estimation — `src/sigma_symbol_rate.py`

| Metric | Value |
| :--- | :--- |
| Cases locked | **10 / 10** |
| Cases at 0.00% error | **9** |
| Conditions | 25–250 ksps, α = 0.15–0.50 |
| Failure | 500 ksps (SPS = 2) — reports `LOW` confidence, not a wrong number |

### 2.2 Constellation identification

Two tiers exist and they are **not equally strong**. Do not conflate them.

**Tier 1 — spectral order detection** — `_detect_psk_order()` in `sigma_analyzer_core.py`

| Metric | Value |
| :--- | :--- |
| Correct | **11 / 12** |
| BPSK | 6 / 6 |
| The one miss | returns `0` = "undetermined", i.e. abstains |
| **Ceiling** | **names BPSK or QPSK only.** It cannot report 8PSK: measured, 8PSK's strongest M-th-power line sits at `x²` (29.2) rather than `x⁸` (28.8), so an 8PSK capture is reported as BPSK |

**Tier 2 — symbols-fitted parsimony classifier** — `classify_constellation()` in `sigma_demod.py`

| Metric | Value |
| :--- | :--- |
| Correct | **144 / 144** |
| Conditions | 4 modulations × 4 rates × 3 excess bandwidths × 3 seeds |
| Noise | **abstains 3/3** (correct) |
| Guard | requires **≥2 distinct constellation phases** |

Tier 2 supersedes tier 1 and names all four constellations. In the GUI, tier 1's
label is used as the first hypothesis, and tier 2 corrects it — visibly:

```
symbols: 8PSK is the simplest that fits (EVM 3.3%; the classifier said BPSK)
```

**An attempt to extend tier 1 to M=8 was measured and reverted.** It labelled
pure noise "BPSK" and an unmodulated carrier "8PSK" — confident wrong answers.
The conservative 2-vs-4 comparison (with `PSK_LINE_MARGIN_DB = 3.0`) is what
ships. The measured evidence is recorded in `_psk_line_scores()`'s docstring so
the experiment is not repeated.

### 2.3 Demodulation — `src/sigma_demod.py`

| Modulation | Cases | Perfect | Mean | Min | Refused | Carrier exponent |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| BPSK | 18 | 18 | 100.00% | 100.00% | 0 | 2 |
| QPSK | 18 | 18 | 100.00% | 100.00% | 0 | 4 |
| 8PSK | 18 | 18 | 100.00% | 100.00% | 0 | 8 |
| 16QAM | 18 | 0 | 99.98% | 99.97% | 0 | 4 |
| **Total** | **72** | | | | **0** | |

Conditions: 4 modulations × 25–250 ksps × α = 0.20/0.35/0.50 × 2 seeds.
Reproduce: `scratch/verify_demod_all_mods.py`.

Critically, the demodulator was fed the **detected** symbol rate, not the true
one. A version that only passes when handed the answer would prove nothing.

**16QAM does not reach exactly 100%** — roughly 2 bit errors per 6000 bits, a
consistent noise floor. Reported as measured rather than rounded up.

**The α = 0.20 gap closed on its own.** An earlier revision had 6 `NO DEMOD`
cases at α = 0.20 and proposed a Gardner / Müller & Müller timing detector. The
full sweep is now **72/72 locked, 0 refused** — those failures were the
carrier-estimate defects (§2.3a), not the timing phase search. **No case needs a
timing detector now.** Do not implement one for this reason.

**Two further defects had to be fixed, both found by measurement:**

- **Sub-bin carrier refinement.** An FFT peak is accurate to one bin, and a
  residual *frequency* error accumulates across the record rather than staying a
  constant phase offset. Measured: BPSK at 250 ksps left +58.6 Hz, drifting 132°
  over 1500 symbols, refusing a signal that decodes perfectly.
- **Welch averaging before peak-picking.** On a single FFT a spurious peak
  outranks the true line. Measured on 8PSK at 250 ksps seed 9: a spurious peak
  at −270 kHz scored 6.4 against the real +480 kHz line at 5.8, returning
  −33.8 kHz for a true +60 kHz offset.
- **Decision-directed residual tracking + a second rotation pass.** `x⁴` does
  *not* collapse 16QAM (its points sit at three radii, leaving three measured
  phase clusters). Removing a phase ramp also shifts the best constant rotation,
  so a rotation chosen before the frequency correction is stale. Measured on
  16QAM at 100 ksps: EVM 29.0% → **3.4%**.

### 2.4 GUI

Verified by **reading widget text**, not by screenshot:

```
input file      : demo_bpsk_100ksps_1msps.iq
symbol rate     : 100.00 ksps        samples/symbol : 10.00
lock            : HIGH (37.7 dB)     modulation     : BPSK / Source: measured
step 4 DEMOD    : 4. DEMOD ✓         step 5 BITS    : 5. BITS ✓
```

And the **DEMODULATION & BITSTREAM** card shows the demodulator's real output,
not just a status light:

```
DEMOD state   : LOCKED
DEMOD method  : BPSK  ·  RRC matched filter
DEMOD stats   : Symbols: 6000      Bits: 6000      EVM: 26.6%
                Carrier offset: +59,998 Hz      SPS used: 10.00      Timing: searched
BITSTREAM     : 0110 0101 1001 1100 0110 1101 0010 1111 1000 0100 1100 0000 ...
```

The refusal path is equally explicit:

```
DEMOD state   : DECLINED
DEMOD reason  : Symbol rate lock is only LOW (7.0 dB over the noise floor), so the
                bitstream would be sampled on an untrusted clock. Declined.
BITSTREAM     : --
```

Full 5-stage pipeline completes. On the real 2560×1528 display the window opens
at **1400×1294** with the content needing 1246×1160 — **no scrollbars**, and the
metric grid, the demodulation card and the pipeline stepper are all visible.
(Measuring width under `QT_QPA_PLATFORM=offscreen` is misleading: the dummy
screen is 800×600 and badly distorts the layout's size hints.)

**All four constellations were then verified end-to-end through the GUI** by
driving the real update path and reading the widget strings back —
`scratch/verify_gui_all_mods.py`, **4/4 lock**:

| File | State | Constellation on screen | EVM | Residual tracked |
| :--- | :--- | :--- | ---: | ---: |
| `gui_test_bpsk_100ksps_1msps.iq` | LOCKED | BPSK | 3.3% | −1.4 Hz |
| `gui_test_qpsk_100ksps_1msps.iq` | LOCKED | QPSK | 3.3% | −1.4 Hz |
| `gui_test_8psk_100ksps_1msps.iq` | LOCKED | 8PSK *(classifier said BPSK)* | 3.3% | −1.4 Hz |
| `gui_test_16qam_100ksps_1msps.iq` | LOCKED | 16QAM | 3.3% | −1.4 Hz |

The refusal path was verified with a **genuine unmodulated carrier** file
(`gui_test_cw_unmodulated.iq`) — three forced labels, all correctly declined:

```
CW / Unmodulated   -> UNSUPPORTED   (Detected CW / Unmodulated; no digital constellation)
AM / ASK           -> UNSUPPORTED   (Detected AM / ASK; no digital constellation explains)
FM / RDS           -> UNSUPPORTED   (Detected FM / RDS; no digital constellation explains)
```

> **Note the 8PSK row.** It locks *despite* the spectral classifier saying BPSK —
> that is tier 2 correcting tier 1, and the tooltip says so out loud. This is the
> single clearest demonstration that the two tiers are distinct.

### 2.5 Filename-independence

Renaming `bpsk_modulated_1msps.iq` → `anonymous_capture.iq` → `random_data.iq`
all yield `BPSK | measured`. Before the fix, the renamed file fell through to
`Digital PSK/FSK / 78.4%` — a fabricated confidence produced by a substring
match on the filename.

### 2.6 Coding layer (PS §3 iii / iv)

Shipped in **`src/sigma_coding.py`** and wired into the analysis pass, so the
demodulated bits run through interleaver detection and FEC decode automatically.
The measurements below are scored against the **shipped module**, not a scratch
copy — which matters, see below.

**Convolutional FEC.** A `(2,1,3)` code, `polys = (0b111, 0b101)`, terminated with
`K-1` zero tail bits so the trellis returns to a known state.

| Injected flips | Uncorrected | Decoded | Errors fixed |
|---:|---:|---:|---:|
| 1 | 99.88% | **100.00%** | 1/1 |
| 5 | 99.38% | **100.00%** | 5/5 |
| 10 | 98.75% | **100.00%** | 10/10 |
| 20 | 97.50% | **100.00%** | 20/20 |
| 40 | 95.00% | 99.75% | 39/40 |
| 80 | 90.00% | 96.00% | 64/80 |

Score **error counts, not accuracies**: at 1 flip the uncorrected stream is
already 99.88% correct, so an accuracy delta of +0.12% reads as "no help" when in
fact every error was removed.

**Uncoded input is refused.** The safety property that makes it safe to run on
every capture: `analyse_coding_layer` on ordinary uncoded traffic reports
`had_fec=False` with a residual of ~0.13 and leaves `decoded_bits` as `None`. A
Viterbi decoder *would* return confident output for any input, so reporting it
would invent a payload. Verified in check 3 of `verify_coding_module.py`.

**Interleaver identification, blind.** The detector receives the interleaved
coded stream and the code, but **not** the permutation. It de-interleaves under
each candidate — searching factorisations rather than guessing one — then tests
the result with

```
decode(bits) -> re-encode -> compare against bits
```

| Input | Residual |
|---|---|
| clean codeword | **0.0000** |
| 3 channel errors | 0.0077 |
| shuffled codeword | 0.1366 |
| random bits | 0.1418 |

The correct hypothesis scores exactly `0.0000`; every wrong one scores
`0.046–0.148`. Results: **4/4** blind with no geometry hint, **288/288** across
3 lengths × 4 geometries on a clean channel, **0/4** on interleaved random bits
(the control), and **100%** payload recovery end to end for all four modes.

The operating boundary, the cost of the geometry search, and the two bugs the
`src/` port exposed are all in `STATUS_DONE_VS_LEFT.md` §3a–3b.

Reproduce: `scratch/verify_coding_module.py`, `scratch/verify_coding_gui.py`.

### 2.7 Bitstream correlation / header detection (PS §3 v)

Sync-word search, shipped alongside the FEC layer and run on every analysis.
The gate is **calibrated against the chance distribution** rather than fixed:
with `m = n - L + 1` offsets and error counts `Binomial(L, 0.5)`, the expected
number of chance hits at or below `e` is `m · P(X ≤ e)`, and a hit is reported
only when that expectation is below 1%.

| Sync length | Stream | Threshold | Expected chance hits |
|---|---|---|---|
| 16 | 400 | 0 | 0.0059 |
| 16 | 20,000 | **none** | not decidable |
| 32 | 400 / 20,000 / 100,000 | 0 | ~0 / ~0 / 2.3e-5 |

A 16-bit sync word is decidable in a 400-bit stream but **not** in a 20,000-bit
one — more data means more chances for a false match. Detection is a property of
**(pattern length, stream length)**, not of the correlator.

| Test | Result |
|---|---|
| Locate at a known offset (0, 37, 200, 913) | **4/4**, 0 bit errors |
| Channel flip rate 0 / 2 / 5% | **20/20** each |
| Channel flip rate 10% | 19/20 |
| **Control:** unframed noise | **0/25** false detections |
| Refusal: 16-bit sync in a 20,000-bit stream | declines, as required |

The control is what gives the rest meaning: a fixed "best score ≤ 4" rule fires
on **19/25** streams of 200,000 bits.

**A bug worth recording:** the first gate required a hit *strictly better than*
the chance threshold. For a 392-bit stream that threshold is 0, so `errors < 0`
was unsatisfiable and the detector returned **nothing at all, at every offset, on
a clean channel**. Fixed by deriving the gate from a probability rather than a
score comparison. The symptom — failing *uniformly* — matches the Viterbi
traceback bug's fingerprint: a detector that never succeeds is as broken as one
that always does.

Reproduce: `scratch/header_ground_truth.py` (ground truth + chance table),
`scratch/verify_coding_module.py` §6 (shipped module).

### 2.8 The modulation card reports a source, not a confidence

A truthfulness property rather than a DSP one, but it needs a test all the same,
because it is user-visible and it regressed twice.

`"measured"` answers *where the class came from* (the signal, not the filename).
It is **not** a probability, and the four-way candidate distribution does not
exist — runner-up classes are discarded, not ranked. So a label reading
`Confidence: measured` invites the reader to treat a provenance word as a score.

Checked by reading the widget text back for **every** provenance value:

| stored value | rendered |
|---|---|
| `measured` | `Source: measured` |
| `indeterminate` | `Source: indeterminate` |
| `filename hint, unverified` | `Source: filename hint, unverified` |
| `--` | `Source: --` |

The test also asserts the label contains **no digits**, so a future "helpful"
percentage cannot be reintroduced without failing, and confirms the **genuine**
confidence figure (EVM) is still displayed in the demod card — removing the
misleading word must not remove real information.

The field was renamed `modulation_confidence` → `modulation_source`; the old
name remains as a read/write property alias, and the test asserts the two
cannot disagree.

Reproduce: `scratch/verify_provenance_label.py`.

### 2.9 Blind FEC-scheme identification (PS §3 i)

The coding layer used to take `K` and `polys` as inputs. It now **identifies the
code from the stream**, because a real receiver is not told which one was used
and the code is not carried in the signal.

**The control is the important part.** A search over candidate codes always
returns a winner, so an unthresholded one fabricates:

| rule | random streams given a scheme |
|---|---|
| bare argmin | **12/12** |
| residual `≤ FEC_THRESHOLD` (0.03) | **0/12** |

Results against the shipped module:

| Test | Result |
|---|---|
| Each of 5 codes named from its own encoding | **5/5** |
| True code residual vs runner-up | 0.0000 vs ~0.12 (**margin 0.12+**) |
| Random streams given a scheme | **0/12** |
| Fast path: non-default code + interleaver | **0/16** (the measured blind spot) |
| Deep search: same cases, K ≤ 7 | **16/16** |
| Deep search on random bits | **0/4** |
| K=9 on a short stream | reported `'skipped: stream too short'`, not rejected |

Two properties are checked because they are easy to get wrong:

* **A skipped candidate is not a rejected one.** K=9 is gated by stream length
  (`MIN_BITS_FOR_K9`); when it is not tested the table says so explicitly, since
  "not tested" and "tested and rejected" are different claims.
* **The reason string must not contradict the result.** An early version
  searched for the code on the *raw* bits and then de-interleaved, so an
  interleaved codeword reported *"the code search fell short"* while
  simultaneously decoding the payload at 100%. The search now runs on the
  stream that is actually decoded.

Reproduce: `scratch/fec_scheme_search.py` (ground truth),
`scratch/verify_scheme_search.py` (shipped module + GUI, ~2 min).

---

## 3. Known limitations (unresolved, stated plainly)

### 3.1 Low excess bandwidth (α = 0.20) — **closed**

An earlier revision reported `NO DEMOD` on BPSK at α = 0.20 (all five rates) and
QPSK 200 ksps α = 0.20 seed 7. **The full sweep is now 72/72 locked, 0 refused**,
including every α = 0.20 case.

The cause was **not** the timing phase search. The 6 failures were downstream of
the carrier-estimate defects fixed in §2.3 — a biased or bin-quantised carrier
estimate drifts the constellation during the record, which looks exactly like a
timing problem. **Do not implement a Gardner / Müller & Müller detector for
this**; no case needs one now.

**One approach to keep rejected:** a zero-ISI-null timing search was tried and
**measured worse** than simply taking the strongest spectral bin — 11/20 against
14/20. It is recorded here so it is not attempted again as a "fix" for a low-α
failure.

### 3.2 Sample rate cannot be measured — only resolved and labelled

`_load_signal_file()` used to substring-match `"250k"` and `"1m"`. That was
replaced by `src/sigma_sample_rate.py`, but the important result is *why* it can
never be a measurement.

**Proof that `f_s` is not observable from samples.** Take 1000 samples with a
symbol clock every 10 samples. Now imagine the same signal recorded at twice the
rate: the clock is every 20 samples. The two files contain **byte-identical
samples** — a capture has no absolute time reference. The only difference is the
label on the file. Therefore no algorithm reading only the samples can recover
`f_s`.

What *is* observable is `SPS = f_s / R_s`. `probe_rs_abs.py` measured it with
**no knowledge of `f_s` at all**, and was accurate to **mean 0.001%, max 0.002%**.
That is why the demodulator works even when `f_s` is a guess — but it also means
every reported *symbol rate in Hz* inherits the guess's error exactly.

**What the module does instead.** It resolves `f_s` from the most trustworthy
available source and reports the trust level:

| Rank | Source | Confidence | Notes |
| :--- | :----- | :--------- | :---- |
| 1 | Operator (**⚙ Settings**) | `MEASURED` | They have the datasheet / SDR config |
| 1= | WAV container header | `MEASURED` | A real, in-band reference |
| 2 | Recognised standard `R_s` | `MEASURED` | Corrects `f_s` to `f_s_assumed × (R_standard / R_measured)` |
| 3 | Filename token | `INFERRED` | A hint. Wrong if the file was renamed |
| 4 | Fallback | `ASSUMED` | Nothing available |

Protocol matching is deliberately conservative — a near-miss declines rather
than guessing, because a mis-identified standard yields a *confidently* wrong
rate. Only a close match (±0.5%, looser for narrowband CW) is accepted, and
several standards legitimately sharing one rate (AIS and VDL2 are both 9600) is
treated as a label ambiguity, not a rate ambiguity.

The GUI shows the provenance under the input card, colour-coded, so a filename
guess is never presented with the authority of a measured value.

**Verification:** `scratch/verify_sample_rate.py` — **25/25 passing**.
Two real bugs were found by that suite, not by inspection:

- `(\d+)\s*k\b` matched only `"250"` inside `"250k"` — a word boundary exists
  between the digit and the letter, so the regex consumed the digits and dropped
  the multiplier, yielding 250 Hz which the sanity floor then discarded. Fixed
  with a `(?![a-z])` lookahead so the multiplier is consumed but not overrun.
- A test asserted `96 000` sym/s was VDL2/AIS. VDL2/AIS is `9 600`. The module
  was right to decline; the *test* was wrong. Corrected, and a case locking in
  the 10× rejection added.

An implausible `SPS` (outside 2–4096) is surfaced as a probable renamed file —
cheap, needs no extra measurement, and catches the exact off-by-2×/10× failure
mode.

### 3.3 The bundled dataset has no symbol clock

`signal.iq`, `bpsk_modulated_1msps.iq`, etc. all show `LOW` lock and stages 4–5
decline. They are not usable for demonstrating end-to-end demodulation. Use
`demo_bpsk_100ksps_1msps.iq`, or generate one with `make_ground_truth.py`.

---

## 4. Method notes worth keeping

- **Welch averaging is mandatory.** A single FFT of a noise-like sequence has
  ~100% spectral variance; one noise bin outranks the real clock line. Overlap
  segments with a Hann window before peak-picking.
- **FFT length matters enormously.** `nfft=1024` @ 1 Msps = ~976 Hz bins lets
  the signal's own leakage win. Going to `nfft=16384` took the error from
  **±42% → 0.00%**.
- **Never estimate carrier offset from a power-weighted spectral centroid.**
  A wideband signal's centroid is not its carrier.
- **Score recovered bits with a rotation search.** BPSK has 180° ambiguity,
  QPSK 90°. Without searching, you measure the ambiguity rather than the
  demodulator. Real receivers resolve this with a preamble.
- **Generate test symbols from the constellation index**, then derive expected
  bits. Generating QPSK from independent random per-axis bits silently imposes
  a Gray-vs-binary labelling mismatch and produces an exactly-50% BER that
  looks like a demodulator bug. It is a harness bug.
- **Verify the GUI in-process.** Screenshots prove pixels were painted, not that
  values are correct, and they hide anything below the fold. Build the window,
  call the real `_update_all_displays()`, then assert on widget text.
- **Do not use `EnumWindows` to inspect the app's window.** Each shell
  invocation may run in a different Windows desktop session, returning stale or
  unrelated windows. Read `window.width()` / `widget.mapTo()` inside the process.
- **`PrintWindow` truncates GPU-composited windows.** Use `widget.grab()`.

### One approach that was tried, measured, and reverted

The zero-ISI (Nyquist) null *does* exist at the true symbol period — the
envelope dips there. It was investigated as a **search** mechanism across four
variants and **rejected on measurement**:

| Variant | Result |
| :--- | :--- |
| Absolute-threshold null test | Fixed QPSK α=0.20 (46→50 perfect) but accepted junk at unrelated periods |
| "Lowest passing candidate" rule | **Regression: every case halved** (0/60) |
| Local-contrast scoring | **11/20 correct vs 14/20** for simply taking the strongest bin — worse |
| Rescan-the-spectrum | Found a false clock at 81.05k before reaching the true 100k |

It also cannot distinguish `SPS` from `2·SPS` — both are genuinely
symbol-aligned, and `2·SPS` often measures a *deeper* null.

**Conclusion: the zero-ISI null confirms a period but cannot search for one.**
All of that code was removed. `scratch/diag_score_select.py` is retained as the
evidence so this is not re-attempted.

---

## 5. Environment caveat — verify in Radioconda

The app ships against **Radioconda**, whose numpy (2.2.x) differs from a
typical dev install in ways that matter:

| Behaviour | Radioconda numpy 2.2.x | Dev numpy 2.5.3 |
| :--- | :--- | :--- |
| `np.fft.rfft(complex_input)` | **raises `TypeError`** — `ufunc 'rfft_n_even' not supported` | works |
| `complex128 ** 2` | can drop the complex dtype | fine |

Even `np.fft.rfft(np.ones(1024, dtype=np.complex128))` fails there. Use
`np.fft.fft` and slice the first half for complex input, and prefer repeated
multiplication over `**`.

**Code that passes on a dev numpy can still crash on the judge's machine.**
Always verify with:

```powershell
& "$env:USERPROFILE\radioconda\python.exe"
```

---

## 6. Reproducing everything

```powershell
# DSP correctness (no GUI, no GNU Radio needed) -- runs all 17 suites
& "$env:USERPROFILE\radioconda\python.exe" scratch\run_all.py

# Individual DSP suites
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_symbol_rate.py          # 10/10
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_demod_all_mods.py       # 72/72, 0 refused
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_modclass_parsimony.py   # 144/144
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_no_symbols_guard.py     # CW/ASK refused
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_analogue_refused.py     # FM/AM/ASK/CW/audio
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_demod_gate.py           # 11/11 routing
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_gui_all_mods.py         # 4/4 through the GUI
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_wide.py                 # BPSK/QPSK legacy, 46/46

# Coding layer (PS section 3 iii / iv)
& "$env:USERPROFILE\radioconda\python.exe" scratch\fec_ground_truth.py            # encode/decode, 4 interleavers
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_interleaver_detect.py   # 4/4 blind, 0/4 on noise
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_coding_module.py        # shipped module, refusal check
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_coding_gui.py           # through the real window
& "$env:USERPROFILE\radioconda\python.exe" scratch\header_ground_truth.py         # sync search + chance table
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_provenance_label.py     # card says Source, not Confidence

# FEC scheme identification (PS section 3 i)
& "$env:USERPROFILE\radioconda\python.exe" scratch\fec_scheme_search.py           # 5 codes, margin, 0/12 control
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_scheme_search.py        # shipped module + GUI (~2 min)

# GUI: default view completes the pipeline
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_default_view.py

# GUI: the DEMODULATION card shows real values / a real reason
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_demod_panel.py

# GUI: window and content fit the real screen with no scrollbars
& "$env:USERPROFILE\radioconda\python.exe" scratch\measure_real_display.py

# GUI: launches, and still declines untrusted input
& "$env:USERPROFILE\radioconda\python.exe" scratch\verify_launch_and_refusal.py

# GUI: real window, 4 second smoke test
& "$env:USERPROFILE\radioconda\python.exe" scratch\launch_smoke.py
```

`scratch/` is development-only and not part of the shipped application, but
keeping it is what makes the claims above checkable.
