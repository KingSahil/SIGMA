# SIGMA — Signal Intelligence & Generalized Modulation Analyzer

A GNU Radio + PyQt5 desktop workstation for real-time analysis and visualization of raw **I/Q (In-Phase / Quadrature)** RF signal recordings, purpose-built for the **Smart India Hackathon 2024 Problem Statement 6147** (NTRO).

---

## 📊 Overview

SIGMA ingests complex IQ samples from binary (`.iq`) or audio (`.wav`) recordings and provides a full signal intelligence pipeline:

| Stage | Status | Description |
| :--- | :---: | :--- |
| **1. INPUT** | ✅ Done | File ingestion, format detection, WAV-to-IQ conversion |
| **2. ANALYSIS** | ✅ Done | RMS amplitude, peak amplitude, power (dBFS), 99% OBW, SNR, noise floor |
| **3. MODULATION** | ✅ Done | Multi-feature classifier (AM, FM, ASK, FSK, BPSK, QPSK, 8PSK, QAM) |
| **4. DEMOD** | 🔄 Planned | Carrier recovery, symbol synchronization, matched filtering |
| **5. BITS** | 🔄 Planned | Decision slicing and binary bitstream extraction |

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
├── docs/                   # Full system & architecture documentation
├── grc/                    # GNU Radio Companion source flowgraphs (.grc)
├── src/                    # Core Python application modules
│   ├── __init__.py
│   ├── sigma_analyzer_core.py   # Physical signal metrics & DSP extraction (NumPy)
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
| **`data/iq/`** | Sample raw IQ binary captures (`signal.iq`, BPSK, QPSK, FM RDS). |
| **`data/audio/`** | Sample WAV recordings (`sdr_test_stereo.wav`, `thunderclouds_clip.wav`). |
| **`grc/`** | GNU Radio Companion visual flowgraph projects (`SIGMA_IQ_Analyzer.grc`). |
| **`docs/`** | Architecture, data pipelines, technology specs, and workflow guides. |
| **`run.py`** | Recommended root entry script to launch the application. |

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
| **Modulation Class** | Phase variance + amplitude variance feature classifier |

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
- **Input Source**: `data/iq/signal.iq` (loop: enabled)
- **FFT Size**: `1024` with Blackman-Harris window
- **Center Frequency**: `0 Hz` (baseband)

To use your own IQ recording:
1. Place your `.iq` or `.bin` file in `data/iq/` (or click **📂 Load Signal File** to browse).
2. SIGMA auto-detects sample rate from the filename (`250k` → 250 kSps, `1msps` → 1 MSps).
3. Otherwise, open **⚙ Settings** and set **Sample Rate** and **Center Frequency** manually.

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

### Window Closes Immediately
- Verify that `data/iq/signal.iq` exists. The app searches `data/iq/signal.iq`, `data/signal.iq`, and `signal.iq` at startup.

---

## 📚 Documentation

Full technical documentation is in the [`docs/`](docs/) directory:

| Document | Description |
| :--- | :--- |
| [`SIH_PROBLEM_STATEMENT.md`](docs/SIH_PROBLEM_STATEMENT.md) | SIH 6147 objectives, requirements, and deliverables |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System tiers, data flow diagrams, threading model, component breakdown |
| [`TECHNOLOGIES_USED.md`](docs/TECHNOLOGIES_USED.md) | Full technology stack catalog |
| [`DATA_PIPELINE_AND_FORMATS.md`](docs/DATA_PIPELINE_AND_FORMATS.md) | IQ theory, binary format, WAV ingestion, audio demodulation pipeline |
| [`GETTING_STARTED_AND_WORKFLOW.md`](docs/GETTING_STARTED_AND_WORKFLOW.md) | Setup, sample datasets, UI guide, troubleshooting |
