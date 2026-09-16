# Getting Started & Operational Workflow

This guide walks through configuring your environment, running the application, exploring the included sample signals, and interacting with the workstation.

---

## 1. Quick Start Guide

### Prerequisites
SIGMA requires **Python 3.10+** with **GNU Radio 3.10** and **PyQt5**. On Windows, this is provided in a single package via **[Radioconda](https://github.com/ryanvolz/radioconda)**.

### Running from PowerShell
Open PowerShell in the project directory (`gnu/`) and execute:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
```

*Or activate the Radioconda environment first:*
```powershell
& "$env:USERPROFILE\radioconda\Scripts\activate"
python sigma_iq_analyzer.py
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
|  SIGMA  Signal Intelligence & Generalized Modulation Analyzer             [ ⚙ ] |
+-------------------------------------------------------------------------------+
|  INPUT SIGNAL                                                                 |
|  signal.iq  [Format: fc32] [Samples: 50,000] [Rate: 1.00 MS/s] [Duration: ...] |
|  [ 📂 Load Signal File ]                         [ 🔊 Play Audio ]            |
+-------------------------------------------------------------------------------+
|  TIME DOMAIN                       |  FREQUENCY SPECTRUM                      |
|  (In-Phase & Quadrature Waves)     |  (1024-pt FFT Spectrum in dB)            |
+------------------------------------+------------------------------------------+
|  CONSTELLATION DIAGRAM                                                        |
|  (I vs Q scatter plot for symbol decoding)                                    |
+-------------------------------------------------------------------------------+
|  SIGNAL ANALYSIS                   |  MODULATION                              |
|  Peak Freq | Bandwidth | Power ... |  [ Not analyzed ]  Confidence: --        |
+-------------------------------------------------------------------------------+
|  1. INPUT ✓   →   2. ANALYSIS ✓   →   3. MODULATION ○   →   4. DEMOD ○  ...   |
+-------------------------------------------------------------------------------+
```

### Key Operations:
1. **Loading a Signal File**:
   - Click **📂 Load Signal File** to select any `.iq`, `.bin`, `.raw`, `.dat`, or `.wav` recording.
   - For `.wav` audio or SDR stereo captures, the workstation automatically converts them into an IEEE 754 `complex64` IQ binary file on-the-fly.
2. **Adjusting Hardware Parameters**:
   - Click **⚙ Settings** in the top-right corner.
   - Set the correct **Sample Rate** (e.g. `1,000,000 S/s` for 1 MSps files, or `250,000 S/s` for 250 kSps files).
   - Set the **Center Frequency** if your signal has an RF carrier offset.
3. **Listening to the Signal**:
   - Click **🔊 Play Audio** to start instant baseband/envelope playback.
   - The button will highlight in green (`⏹ Stop Audio`) during playback. Click again to stop.

---

## 4. Troubleshooting & FAQ

### `ModuleNotFoundError: No module named 'gnuradio'` or `'PyQt5'`
- **Cause**: Python was executed using a standard Windows Python installation (e.g. `C:\Python312\python.exe`) rather than the Radioconda environment where GNU Radio is installed.
- **Fix**: Launch using Radioconda's interpreter:
  ```powershell
  & "$env:USERPROFILE\radioconda\python.exe" sigma_iq_analyzer.py
  ```

### Sinks Look Blank or Flat
- **Cause**: Sample rate in Settings does not match the file's recorded sample rate, or the file contains all-zero samples.
- **Fix**: Open **⚙ Settings** and set the sample rate to match the recorded file rate (refer to the table in Section 2).

### Window Closes on Startup
- Verify that `signal.iq` exists in the current working directory from which you are launching the command.
