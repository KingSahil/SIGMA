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
| `scratch/run_all.py` | Runs all three. **This is the command you want.** |
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

### 2.2 PSK order detection — `_detect_psk_order()` in `sigma_analyzer_core.py`

| Metric | Value |
| :--- | :--- |
| Correct | **11 / 12** |
| BPSK | 6 / 6 |
| The one miss | returns `0` = "undetermined", i.e. abstains |

### 2.3 Demodulation — `src/sigma_demod.py`

| Metric | Value |
| :--- | :--- |
| Configurations | **46** |
| At exactly 100.00% bit accuracy | **46 / 46** |
| Mean / min accuracy | 100.00% / 100.00% |
| BER | 0.0000 |
| Conditions | BPSK & QPSK × 25–250 ksps × α = 0.20/0.35/0.50 × 2 seeds |

Critically, the demodulator was fed the **detected** symbol rate, not the true
one. A version that only passes when handed the answer would prove nothing.

### 2.4 GUI

Verified by **reading widget text**, not by screenshot:

```
input file      : demo_bpsk_100ksps_1msps.iq
symbol rate     : 100.00 ksps        samples/symbol : 10.00
lock            : HIGH (37.7 dB)     modulation     : BPSK / Confidence: measured
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

The recovered carrier offset `+59,998 Hz` independently confirms the estimator:
the test signal was generated with a **60 kHz** offset, so the error is 2 Hz.

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

### 2.5 Filename-independence

Renaming `bpsk_modulated_1msps.iq` → `anonymous_capture.iq` → `random_data.iq`
all yield `BPSK | measured`. Before the fix, the renamed file fell through to
`Digital PSK/FSK / 78.4%` — a fabricated confidence produced by a substring
match on the filename.

---

## 3. Known limitations (unresolved, stated plainly)

### 3.1 Low excess bandwidth (α = 0.20)

BPSK at α = 0.20 (all five rates) and QPSK 200 ksps α = 0.20 seed 7 report
`NO DEMOD`. At low α the envelope spectrum becomes nearly flat and
"strongest bin" is no longer reliable; the estimator detects that it cannot
decide and declines.

**A refusal is correct behaviour. A confident wrong bitstream is the actual
failure mode.**

The real fix is a **Gardner or Müller & Müller timing-error detector** after
matched filtering — a proper closed-loop timing recovery — not another
envelope-spectrum heuristic.

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
# DSP correctness (no GUI, no GNU Radio needed)
& "$env:USERPROFILE\radioconda\python.exe" scratch\run_all.py

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
