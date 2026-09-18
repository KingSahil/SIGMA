# SIGMA — Signal Intelligence & Generalized Modulation Analyzer

A GNU Radio + PyQt5 desktop workstation for real-time analysis and visualization of raw **I/Q (In-Phase / Quadrature)** RF signal recordings, purpose-built for the **Smart India Hackathon 2024 Problem Statement 6147** (NTRO).

---

## 📊 Overview

SIGMA ingests complex IQ samples from binary (`.iq`) or audio (`.wav`) recordings and provides a full signal intelligence pipeline:

| Stage | Status | Description |
| :--- | :---: | :--- |
| **1. INPUT** | ✅ Done | File ingestion, format detection, WAV-to-IQ conversion |
| **2. ANALYSIS** | ✅ Done | RMS amplitude, peak amplitude, power (dBFS), 99% OBW, SNR, noise floor |
| **3. MODULATION** | ✅ Done | **Symbol rate** + **SPS** measurement, constellation named for all four |
| **4. DEMOD** | ✅ Done | Carrier recovery, RRC matched filter, symbol timing, phase correction |
| **5. BITS** | ✅ Done | Decision slicing and binary bitstream extraction |

**Demodulation covers four constellations**, not two: BPSK, QPSK, 8PSK and 16QAM.

Everything appears in the GUI, not just in logs. The **DEMODULATION & BITSTREAM**
card shows the demodulator's actual output:

| Shown | Example | What it proves |
| :--- | :--- | :--- |
| State | `LOCKED` / `DECLINED` | whether demodulation ran at all |
| Method | `BPSK · RRC matched filter` | which constellation and filter were used |
| Symbols / Bits | `6000 / 6000` | how much was recovered |
| EVM | `26.6%` | constellation quality (lower is better) |
| Carrier offset | `+59,998 Hz` | the frequency offset found and removed |
| SPS used | `10.00` | driven by the **measured** symbol rate, not a constant |
| Recovered bits | `0110 0101 1001 1100 …` | the actual bitstream |

> [!IMPORTANT]
> **Stages 4–5 are live but gated on measurement quality.** If the symbol-rate
> lock is only `LOW`, the app refuses to demodulate and says why — demodulating
> on an untrusted clock yields a *plausible but wrong* bitstream, which is worse
> than no output. This is deliberate; see
> [Verified results](#-verified-results-read-this-before-quoting-any-number).

---

## 🎯 Verified Results (read this before quoting any number)

All DSP stages were scored against **generated ground truth** (known symbol
rate, known modulation, known transmitted bits) — not eyeballed on a plot.
Reproduce with `scratch/run_all.py`; see [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

| Metric | Result | Conditions |
| :--- | :--- | :--- |
| **Symbol rate estimation** | **10/10 locked, 9 at 0.00% error** | 25–250 ksps, α = 0.15–0.50 |
| **Constellation identification** | **144/144 correct**, noise refused 3/3 | 4 modulations × 4 rates × 3 α × 3 seeds |
| **Demodulation (bit accuracy)** | **72/72 locked, 0 refused** — BPSK/QPSK/8PSK **100.00%**, 16QAM **99.98%** | 4 modulations × 25–250 ksps × α = 0.20/0.35/0.50 × 2 seeds |
| **Analogue signals refused** | **5/5** refused (incl. a real FM/RDS capture) | CW, AM, ASK, audio baseband |

**Honest limitations, stated up front:**

- The one symbol-rate failure (500 ksps, SPS=2) self-reports `LOW` confidence
  instead of a wrong number — correct behaviour, not a crash.
- **16QAM sits at 99.97–99.98%** — roughly 2 bit errors per 6000 bits. That is a
  consistent noise floor, disclosed rather than rounded up to 100%.
- **Sample rate cannot be measured from the samples — it is resolved and
  labelled instead.** There is no absolute time reference in an IQ file, so a
  capture of 1000 samples with a clock every 10 samples is byte-identical to one
  recorded at twice the rate with a clock every 20. `f_s` therefore comes from
  outside the data, ranked **operator > recognised standard > filename > default**,
  and the GUI shows which. A rate read from a filename token is displayed as
  `INFERRED`, never as if it had been measured.
  *Verified:* `SPS` itself is measurable with no knowledge of `f_s` to
  **0.001%** error, which is what makes the demodulator work regardless.
- The bundled `data/iq/signal.iq` is **synthetic with no recoverable symbol
  clock**, so it always stops at stage 3. This is why the app ships with a
  separate demo capture (below).

---

## 🖥️ Visualization Suite

Four real-time GNU Radio QtGUI plot sinks embedded in a modern dark-theme desktop UI:

| View | Description |
| :--- | :--- |
| **Time Domain** | Oscilloscope display of I (cyan) and Q (magenta) waveforms |
| **Frequency Spectrum** | 1024-point FFT with Blackman-Harris windowing, `-140` to `+10 dB` |
| **Waterfall (Spectrogram)** | Time-frequency intensity heatmap — visualizes signal drift and hopping |
| **Constellation Diagram** | IQ scatter plot for symbol pattern inspection (BPSK, QPSK, QAM clusters) |

**View Mode Switcher**: Toggle buttons (`⊞ 2x2 Grid` · `⏱ Time` · `📊 Spectrum` · `🌊 Waterfall` · `✦ Constellation`) switch between 2×2 multi-sink monitoring and full-resolution single-sink inspection.

**Interactive HUD Overlay**: Click or drag inside any plot to get live coordinate readouts (time in µs/ms, frequency in kHz/MHz, amplitude, or I/Q values). Right-click to unzoom.

---

## 📁 Repository Structure

```
gnu/
├── data/
│   ├── audio/              # Sample RF audio & demodulated recordings (.wav)
│   └── iq/                 # Raw complex IQ binary recordings (.iq)
│       ├── demo_bpsk_100ksps_1msps.iq   # ← app opens on this (full pipeline)
│       └── signal.iq                    # synthetic, stops at stage 3 by design
├── docs/                   # Full system & architecture documentation
├── grc/                    # GNU Radio Companion source flowgraphs (.grc)
├── scratch/                # Verification harnesses (not shipped; see below)
├── src/                    # Core Python application modules
│   ├── __init__.py
│   ├── sigma_analyzer_core.py   # Physical signal metrics & DSP extraction (NumPy)
│   ├── sigma_symbol_rate.py     # Symbol rate estimator (envelope cyclostationarity)
│   ├── sigma_sample_rate.py     # Sample rate f_s resolution + provenance labelling
│   ├── sigma_demod.py           # Digital demodulator → bitstream
│   ├── sigma_flowgraph.py       # GNU Radio streaming engine, 4 QtGUI sinks
│   ├── sigma_iq_analyzer.py     # Application entry point (QApplication bootstrap)
│   ├── sigma_main_window.py     # Full GUI — header, input bar, viz suite, results
│   └── sigma_theme.py           # Color palette & unified QSS stylesheet
├── run.py                  # Root launcher (recommended entry point)
├── sigma_iq_analyzer.py    # Root launcher for backward compatibility
├── README.md               # This file — quick-start guide
└── .gitignore              # Ignored caches and temporary converted files
```

| Folder / File | Description |
| :--- | :--- |
| **`src/`** | Python application packages, GUI window, DSP core, and theme engine. |
| **`src/sigma_symbol_rate.py`** | Symbol rate `R_s` from envelope periodicity (Welch-averaged). |
| **`src/sigma_sample_rate.py`** | Resolves `f_s` with ranked provenance (operator > protocol > filename > default). |
| **`src/sigma_demod.py`** | Carrier recovery → RRC matched filter → timing → decisions → bits. |
| **`data/iq/`** | Sample raw IQ captures. `demo_bpsk_100ksps_1msps.iq` is the startup file. |
| **`data/audio/`** | Sample WAV recordings for testing audio ingestion. |
| **`grc/`** | GNU Radio Companion visual flowgraph projects (`SIGMA_IQ_Analyzer.grc`). |
| **`docs/`** | Architecture, data pipelines, technology specs, and workflow guides. |
| **`scratch/`** | Ground-truth generators and verification probes. Dev-only — safe to ignore, but do not delete if you want to re-run the proofs. |
| **`run.py`** | Recommended root entry script to launch the application. |

### Which file does the app open on?

`resolve_sample_path()` in `sigma_main_window.py` picks, in order:

1. An **explicitly supplied path** — if you click *Load Signal File*, your choice
   always wins and is never second-guessed.
2. `data/iq/demo_bpsk_100ksps_1msps.iq` — chosen as the startup default so the
   app opens on a capture the **whole pipeline can complete on**.
3. `data/iq/signal.iq` — fallback.

To see the refusal path for yourself, open `signal.iq` manually: stages 4–5
stay unticked and the tooltip explains the `LOW` lock that caused it.

---

## ⚙️ Prerequisites & Important Concept

> [!IMPORTANT]
> **GNU Radio cannot be installed with standard `pip install gnuradio`.**  
> GNU Radio is a high-performance C++ DSP framework with Python and Qt5 bindings. On Windows, the official and recommended way to run GNU Radio is through **[Radioconda](https://github.com/ryanvolz/radioconda)**.

If you already have Radioconda installed (typically at `C:\Users\<YourUsername>\radioconda`), you already have everything needed.

---

## 🚀 Setup & Installation (Step-by-Step)

### Step 1: Install Radioconda (if not already installed)
1. Download the Windows installer from the [Radioconda GitHub Releases](https://github.com/ryanvolz/radioconda/releases).
2. Run the installer and install to the default user path:
   ```
   C:\Users\<YourUsername>\radioconda
   ```

### Step 2: Configure Your Code Editor (VS Code / Antigravity IDE)
To ensure your editor uses Radioconda instead of a standard Python installation:
1. Press **`Ctrl + Shift + P`** → **`Python: Select Interpreter`**.
2. Choose **Enter interpreter path...** and paste:
   ```powershell
   C:\Users\<YourUsername>\radioconda\python.exe
   ```
   *(Replace `<YourUsername>` with your Windows user name.)*

---

## ▶️ Running the Application

### Option 1: Run via `run.py` from PowerShell (Recommended)
Open PowerShell in this project folder (`gnu/`) and execute:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" run.py
```

### Option 2: Run the legacy root launcher
```powershell
& "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
```

### Option 3: Activate Radioconda environment first
```powershell
& "$env:USERPROFILE\radioconda\Scripts\activate"
python run.py
```

### Option 4: Open in GNU Radio Companion (Visual Editor)
To view or edit the signal processing blocks visually:
1. Open your Start Menu and search for **GNU Radio Companion** (or run `& "$env:USERPROFILE\radioconda\Scripts\gnuradio-companion.exe"` in terminal).
2. Click **File > Open** and select `grc/SIGMA_IQ_Analyzer.grc`.
3. Press **Play (▶️)** (`F5`) to run the flowgraph.

---

## 📐 DSP Metrics Computed

All metrics are calculated from real sample data — no mocked values:

| Metric | Method |
| :--- | :--- |
| **RMS Amplitude** | Square root of mean squared magnitude |
| **Peak Amplitude** | Maximum sample magnitude |
| **Signal Power (dBFS)** | 10·log₁₀ of RMS power |
| **Peak Frequency** | Blackman-windowed FFT bin offset from center freq |
| **99% Occupied Bandwidth** | Cumulative spectral power at 0.5% and 99.5% thresholds |
| **Noise Floor** | Mean power of lowest-quartile FFT bins (dBFS) |
| **SNR** | Ratio of upper-75% to lower-25% FFT bin powers (dB) |
| **Symbol Rate `R_s`** | Envelope cyclostationarity: Welch-averaged FFT of \|x[n]\|², 16384-pt, parabolic sub-bin interpolation |
| **Samples per Symbol** | `SPS = f_s / R_s` — the bridge to the ML model |
| **Symbol Rate Lock** | Peak prominence over the local envelope noise floor, in dB |
| **PSK Order** | 2nd- vs 4th-power carrier-line prominence (3 dB margin required) |
| **Modulation Class** | Phase variance + amplitude variance + PSK order, measurement-driven |

> [!NOTE]
> Confidences report `measured` / `indeterminate` / `filename hint, unverified`.
> There are no fabricated percentage scores. Renaming a file cannot change the
> reported modulation unless the measurement was already indeterminate — in
> which case the result is explicitly labelled as an unverified hint.
>
> **Be precise about what `measured` means.** It is a **provenance** label —
> *"this came from the signal, not the filename"* — not a confidence value. The
> modulation card shows one class and this word; it does not show the runner-up,
> and there is no per-class probability. The actual confidence is the **EVM**,
> displayed after demodulation (e.g. *"8PSK is the simplest that fits (EVM 3.3%;
> the classifier said BPSK)"*), which is a physical measurement with a known
> noise floor.

---

## 🎧 Audio Playback

Click **🔊 Play Audio** to listen to the loaded signal. SIGMA uses a multi-mode demodulator:
- **FM / FSK content**: FM discriminator (instantaneous phase derivative)
- **AM / ASK content**: Envelope detector (amplitude)
- **Digital PSK / CW**: BFO heterodyne mixer (shifts baseband IQ to a 1.2 kHz audible pitch)

The demodulator auto-selects the blend based on phase variance and amplitude modulation depth, then resamples to 44.1 kHz 16-bit PCM for low-latency playback via `winsound`.

Click **⏹ Stop Audio** (same button, highlighted green during playback) to stop.

---

## 🛠️ Parameters & Customization

Default configuration:
- **Sample Rate (`samp_rate`)**: `1,000,000` (1 MSps)
- **Input Source**: `data/iq/demo_bpsk_100ksps_1msps.iq` (loop: enabled)
- **FFT Size**: `1024` with Blackman-Harris window
- **Center Frequency**: `0 Hz` (baseband)

To use your own IQ recording:
1. Place your `.iq` or `.bin` file in `data/iq/` (or click **📂 Load Signal File** to browse).
2. SIGMA reads the sample rate from the most trustworthy available source:
   `1msps`/`250k`/`2mhz` tokens in the filename, or a recognised standard symbol
   rate if the measured `R_s` matches one closely. The **Sample rate** line under
   the input card says which, and how much to trust it:
   | Shown | Meaning |
   |---|---|
   | `MEASURED - operator set` | You entered it in **⚙ Settings**. Trust it. |
   | `MEASURED - GSM / GMSK` | Derived from a matched standard. `R_s` was corrected to match. |
   | `INFERRED - filename token "1msps"` | A guess from the filename. Breaks if the file was renamed. |
   | `ASSUMED - no rate found` | Falling back to 1 MSps. Set it manually. |
3. **If the filename carries no rate, set it manually** in **⚙ Settings**. An
   incorrect `f_s` scales every downstream metric — including symbol rate — by
   the same factor. An implausible `SPS` (say 0.5 or 9000) is flagged as a
   probable renamed file.

---

## ❓ Troubleshooting

### `ModuleNotFoundError: No module named 'PyQt5'` or `gnuradio`
- **Cause**: Script launched with a standard Python installation instead of Radioconda.
- **Solution**: Always use Radioconda's interpreter:
  ```powershell
  & "$env:USERPROFILE\radioconda\python.exe" run.py
  ```

### Plots Look Blank or Flat
- **Cause**: Sample rate mismatch, or the file contains all-zero samples.
- **Fix**: Open **⚙ Settings** → set sample rate to match the file (e.g., `250,000 S/s` for FM RDS, `1,000,000 S/s` for BPSK/QPSK).

### Stage 4 (DEMOD) and 5 (BITS) Stay Unticked
This is usually **correct behaviour**, not a failure. Hover the `4. DEMOD`
label — it states the reason. The common causes:

| Tooltip says | Meaning | What to do |
| :--- | :--- | :--- |
| "No symbol rate lock" | No symbol clock is present in the samples — likely noise, or a non-pulse-shaped signal | Nothing to fix; the file has no digital modulation to recover |
| "Symbol rate lock is only LOW (n.n dB)…Declined" | A clock was suspected but sits too close to the noise floor to trust | Correct refusal. Re-record with better SNR if you need bits |
| "Detected 8PSK…" / "Digital PSK/FSK" | No supported constellation explains the recovered symbols | Correct refusal — a wrong constellation order gives wrong bits |
| "No digital constellation explains the symbols" | The signal is analogue, unmodulated, or a modulation outside BPSK/QPSK/8PSK/16QAM | Correct refusal. CW, AM/ASK, FM/RDS and audio baseband all land here by design |
| Nothing wrong, but still unticked | Sample rate is wrong, so `SPS` is wrong | Check the **Sample rate** line under the input card; if it says `INFERRED` or `ASSUMED`, set the true rate in **⚙ Settings** |

A label naming two possibilities (`BPSK / 2-FSK`) is **not** refused: the
demodulator is tried and its own lock decides, so a false positive costs
nothing and reports a measured reason instead of a string mismatch.

Demodulating on an untrusted clock produces a bitstream that *looks* fine and
is wrong. The app deliberately declines instead.

### Window Closes Immediately
- Verify that a startup file exists. The app searches, in order:
  `data/iq/demo_bpsk_100ksps_1msps.iq`, `data/iq/signal.iq`, `data/signal.iq`,
  `signal.iq`, and the same names relative to `src/`.

---

## 📚 Documentation

Full technical documentation is in the [`docs/`](docs/) directory:

| Document | Description |
| :--- | :--- |
| [`SIH_PROBLEM_STATEMENT.md`](docs/SIH_PROBLEM_STATEMENT.md) | SIH 6147 objectives, requirements, and deliverables |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System tiers, data flow diagrams, threading model, component breakdown |
| [`L1_L2_L3_ARCHITECTURE.md`](docs/L1_L2_L3_ARCHITECTURE.md) | Layer boundaries and the CNN interface contract (for ML work) |
| [`VERIFICATION.md`](docs/VERIFICATION.md) | **How every DSP result was proven** — ground truth, sweep harnesses, limitations |
| [`TECHNOLOGIES_USED.md`](docs/TECHNOLOGIES_USED.md) | Full technology stack catalog |
| [`DATA_PIPELINE_AND_FORMATS.md`](docs/DATA_PIPELINE_AND_FORMATS.md) | IQ theory, binary format, WAV ingestion, audio demodulation pipeline |
| [`GETTING_STARTED_AND_WORKFLOW.md`](docs/GETTING_STARTED_AND_WORKFLOW.md) | Setup, sample datasets, UI guide, troubleshooting |
