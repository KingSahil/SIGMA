# Getting Started & Operational Workflow

This guide walks through configuring your environment, running the application, exploring the included sample signals, and interacting with the workstation.

---

## 1. Quick Start Guide

### Prerequisites
SIGMA requires **Python 3.10+** with **GNU Radio 3.10** and **PyQt5**. On Windows, this is provided in a single package via **[Radioconda](https://github.com/ryanvolz/radioconda)**.

### Running from PowerShell (Recommended)
Open PowerShell in the project directory (`gnu/`) and execute:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" run.py
```

*Or activate the Radioconda environment first:*
```powershell
& "$env:USERPROFILE\radioconda\Scripts\activate"
python run.py
```

*Legacy root launcher (backwards compatible):*
```powershell
& "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
```

---

## 2. Included Sample Signal Datasets

The repository includes several sample signal recordings for testing different modulation schemes and signal conditions:

| File Name | Sample Rate | Format | Description / Modulation |
| :--- | :--- | :--- | :--- |
| **`signal.iq`** | 1 MSps (1,000,000 S/s) | Complex Float32 | Default base signal recording (50,000 samples). |
| **`bpsk_modulated_1msps.iq`** | 1 MSps | Complex Float32 | Binary Phase Shift Keying (2-point constellation across I axis). |
| **`qpsk_modulated_1msps.iq`** | 1 MSps | Complex Float32 | Quadrature Phase Shift Keying (4-point symmetric constellation). |
| **`fm_rds_250k_1Msamples.iq`** | 250 kSps | Complex Float32 | Broadcast FM signal with Radio Data System (RDS) subcarrier. |
| **`decimation_exercise.iq`** | Variable | Complex Float32 | Filter & decimation test capture (10,000 samples). |
| **`sdr_test_stereo.wav`** | Audio Rate | RIFF WAV | Dual-channel stereo IQ audio capture. |
| **`thunderclouds_clip.wav`** | Audio Rate | RIFF WAV | Acoustic recording for testing audio conversion and playback. |

---

## 3. Workstation User Interface Guide

```
+-------------------------------------------------------------------------------+
|  SIGMA  Signal Intelligence & Generalized Modulation Analyzer           [ ⚙ ] |
+-------------------------------------------------------------------------------+
|  INPUT  signal.iq  [fc32] [50,000 smp] [Rate: 1.00 MS/s] [50.00 ms (400 KB)] |
|  [ 📂 Load Signal File ]                         [ 🔊 Play Audio ]           |
+-------------------------------------------------------------------------------+
|  [⊞ 2x2 Grid] [⏱ Time] [📊 Spectrum] [🌊 Waterfall] [✦ Constellation]        |
+-----------------------------------+------------------------------------------+
|  TIME DOMAIN                      |  FREQUENCY SPECTRUM                       |
|  ● I (cyan)   ● Q (magenta)       |  1024-pt FFT • -140 to +10 dB             |
|  📍 Click/Drag to Inspect         |  📍 Click/Drag to Inspect                 |
+-----------------------------------+------------------------------------------+
|  WATERFALL (SPECTROGRAM)          |  CONSTELLATION DIAGRAM                    |
|  Intensity over Time              |  Quadrature (Q) vs In-Phase (I)           |
|  📍 Click/Drag to Inspect         |  📍 Click/Drag to Inspect                 |
+-----------------------------------+------------------------------------------+
|  SIGNAL ANALYSIS & DSP METRICS                |  MODULATION                   |
|  Peak Freq | Center Freq | BW | Power (dBFS)  |  [ Digital PSK/FSK ]          |
|  Noise Flr | SNR         | RMS | Peak Amp     |  Confidence: 78.4%            |
+-------------------------------------------------------------------------------+
|  1. INPUT ✓  →  2. ANALYSIS ✓  →  3. MODULATION ✓  →  4. DEMOD ○  →  5. BITS ○ |
+-------------------------------------------------------------------------------+
```

### Key Operations:
1. **Loading a Signal File**:
   - Click **📂 Load Signal File** to select any `.iq`, `.bin`, `.raw`, `.dat`, `.cfile`, or `.wav` recording.
   - For `.wav` audio or SDR stereo captures, the workstation automatically converts them to an IEEE 754 `complex64` IQ binary file on-the-fly.
   - SIGMA auto-detects sample rate from filenames containing `250k` (→ 250 kSps) or `1msps` / `1m` (→ 1 MSps).
2. **Switching View Mode**:
   - Use the `⊞ 2x2 Grid` / `⏱ Time` / `📊 Spectrum` / `🌊 Waterfall` / `✦ Constellation` toggle buttons to focus on a single plot in full-resolution or see all four simultaneously.
3. **Inspecting Plot Coordinates (HUD Overlay)**:
   - Click or drag inside any plot to see live coordinate readouts in the badge above the plot (time, frequency, amplitude, or I/Q).
   - Right-click inside a plot to unzoom back to the full range.
4. **Adjusting Hardware Parameters**:
   - Click **⚙ Settings** in the top-right corner.
   - Set the correct **Sample Rate** (e.g. `1,000,000 S/s` for 1 MSps files, or `250,000 S/s` for 250 kSps files).
   - Set the **Center Frequency** if your signal has an RF carrier offset.
5. **Listening to the Signal**:
   - Click **🔊 Play Audio** to start instant multi-mode demodulation and playback.
   - The button highlights green (`⏹ Stop Audio`) during playback. Click again to stop.

---

## 4. Troubleshooting & FAQ

### `ModuleNotFoundError: No module named 'gnuradio'` or `'PyQt5'`
- **Cause**: Python was executed using a standard Windows Python installation (e.g. `C:\Python312\python.exe`) rather than the Radioconda environment where GNU Radio is installed.
- **Fix**: Launch using Radioconda's interpreter:
  ```powershell
  & "$env:USERPROFILE\radioconda\python.exe" run.py
  ```

### Plots Look Blank or Flat
- **Cause**: Sample rate in Settings does not match the file's recorded sample rate, or the file contains all-zero samples.
- **Fix**: Open **⚙ Settings** and set the sample rate to match the recorded file rate (refer to the table in Section 2). For FM RDS use `250,000 S/s`; for BPSK/QPSK use `1,000,000 S/s`.

### Window Closes on Startup
- Verify that `signal.iq` exists in `data/iq/`, `data/`, or the current working directory from which you are launching the command.

### HUD Badge Still Shows Default After Clicking Plot
- Some plot types may not expose their `QwtPlotZoomer` as a child object depending on the GNU Radio version. This is cosmetic; the plots themselves will still zoom normally with scroll wheel / drag.
