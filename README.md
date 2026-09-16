# SIGMA IQ Analyzer

A GNU Radio flowgraph and Qt GUI application for analyzing and visualizing raw **I/Q (In-Phase / Quadrature)** RF signals.

---

## 📊 Overview

This application loads complex IQ samples from a binary recording (`signal.iq`) and provides real-time visualization across three domains:
- **Time Domain Display**: Shows raw In-Phase (I) and Quadrature (Q) waveforms over time.
- **Frequency Spectrum (FFT)**: Displays the Power Spectral Density (PSD) and peak frequencies.
- **Constellation Diagram**: Displays IQ scatter plots to inspect digital modulation schemes (e.g., BPSK, QPSK, QAM).

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
│   ├── sigma_analyzer_core.py   # Physical signal metrics & DSP extraction
│   ├── sigma_flowgraph.py       # GNU Radio streaming engine & Qt sinks
│   ├── sigma_iq_analyzer.py     # Main application runner
│   ├── sigma_main_window.py     # Modern Google Stitch / Material Design 3 GUI
│   └── sigma_theme.py           # Color palette & unified QSS stylesheet
├── run.py                  # Convenient root launcher script
├── sigma_iq_analyzer.py    # Root launcher for backward compatibility
├── README.md               # Quick-start guide
└── .gitignore              # Ignored caches and temporary converted files
```

| Folder / File | Description |
| :--- | :--- |
| **`src/`** | Python application packages, GUI window, DSP core, and theme engine. |
| **`data/iq/`** | Sample raw IQ binary captures (`signal.iq`, BPSK, QPSK, FM RDS). |
| **`data/audio/`** | Sample WAV recordings (`sdr_test_stereo.wav`, `thunderclouds_clip.wav`). |
| **`grc/`** | GNU Radio Companion visual flowgraph projects (`SIGMA_IQ_Analyzer.grc`). |
| **`docs/`** | Architectural manuals, data pipelines, technology specs, and guides. |
| **`sigma_iq_analyzer.py` / `run.py`** | Root entry scripts to launch the application. |

---

## ⚙️ Prerequisites & Important Concept

> [!IMPORTANT]
> **GNU Radio cannot be installed with standard `pip install gnuradio`.**  
> GNU Radio is a high-performance C++ DSP framework with Python and Qt5 bindings. On Windows, the official and recommended way to run GNU Radio is through **[Radioconda](https://github.com/ryanvolz/radioconda)**.

If you already have Radioconda installed (typically located at `C:\Users\<YourUsername>\radioconda`), you already have everything needed!

---

## 🚀 Setup & Installation (Step-by-Step)

### Step 1: Install Radioconda (If not already installed)
1. Download the Windows installer from the [Radioconda GitHub Releases](https://github.com/ryanvolz/radioconda/releases).
2. Run the installer and install it to the default user path:
   ```
   C:\Users\<YourUsername>\radioconda
   ```

### Step 2: Configure Your Code Editor (VS Code / Antigravity IDE)
To ensure your editor runs the script using Radioconda instead of any standard Python installation:
1. Press **`Ctrl + Shift + P`** in your editor.
2. Search for and select: **`Python: Select Interpreter`**.
3. Choose **Enter interpreter path...** and paste:
   ```powershell
   C:\Users\<YourUsername>\radioconda\python.exe
   ```
   *(Replace `<YourUsername>` with your Windows user name).*

---

## ▶️ Running the Application

### Option 1: Run directly from PowerShell (Quickest)
Open PowerShell in this project folder (`gnu/`) and execute:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
```

### Option 2: Run via Activated Radioconda Environment
1. In PowerShell, activate the environment:
   ```powershell
   & "$env:USERPROFILE\radioconda\Scripts\activate"
   ```
2. Run the script:
   ```powershell
   python sigma_iq_analyzer.py
   ```

### Option 3: Open in GNU Radio Companion (Visual Editor)
If you want to view or edit the signal processing blocks visually:
1. Open your Start Menu and search for **GNU Radio Companion** (or run `& "$env:USERPROFILE\radioconda\Scripts\gnuradio-companion.exe"` in terminal).
2. In GNU Radio Companion, click **File > Open** and select `grc/SIGMA_IQ_Analyzer.grc`.
3. Press the **Play (▶️)** button (or press `F5`) to execute the flowgraph or generate updated Python code.

---

## 🛠️ Parameters & Customization

The flowgraph comes configured with the following default parameters:
- **Sample Rate (`samp_rate`)**: `1,000,000` (1 MSps)
- **Input Source**: `data/iq/signal.iq` (Repeat: Enabled)
- **FFT Size**: `1024` with Blackman-Harris window

To use your own recorded IQ file:
1. Place your `.iq` or `.bin` recording into the `data/iq/` directory (or click **📂 Load IQ File** in the GUI).
2. In `grc/SIGMA_IQ_Analyzer.grc` (or in `src/sigma_iq_analyzer.py`), change the filename parameter in the **File Source** block.
3. Match the **Sample Rate** variable (`samp_rate`) to the sample rate used when recording the signal.

---

## ❓ Troubleshooting

### Error: `ModuleNotFoundError: No module named 'PyQt5'` or `gnuradio`
- **Cause**: The script was launched with a standard Python installation (such as `C:\Python314\python.exe` or a blank virtual environment) instead of Radioconda.
- **Solution**: Always invoke the script using Radioconda's Python interpreter:
  ```powershell
  & "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
  ```

### Window Closes Immediately
- Verify that `data/iq/signal.iq` exists. The application automatically searches `data/iq/signal.iq`, `data/signal.iq`, and `signal.iq`.
