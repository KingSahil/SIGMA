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
| **`demo_bpsk_100ksps_1msps.iq`** | 1 MSps | Complex Float32 | **Startup file.** RRC-shaped BPSK, 100 ksps, SPS = 10, α = 0.35, 6000 symbols. The full 5-stage pipeline completes on this file. |
| **`signal.iq`** | 1 MSps (1,000,000 S/s) | Complex Float32 | Default legacy capture (50,000 samples). **Synthetic — carries no recoverable symbol clock**, so it always stops at stage 3. Useful for demonstrating the refusal path. |
| **`bpsk_modulated_1msps.iq`** | 1 MSps | Complex Float32 | Synthetic BPSK capture. Reports `LOW` symbol-rate lock. |
| **`qpsk_modulated_1msps.iq`** | 1 MSps | Complex Float32 | Synthetic QPSK capture. Reports `LOW` symbol-rate lock. |
| **`fm_rds_250k_1Msamples.iq`** | 250 kSps | Complex Float32 | Broadcast FM signal with Radio Data System (RDS) subcarrier. |
| **`decimation_exercise.iq`** | Variable | Complex Float32 | Filter & decimation test capture (10,000 samples). |
| **`test_bpsk_100ksps_1msps.iq`**, `test_qpsk_50ksps_1msps.iq`, `test_bpsk_200ksps_1msps.iq` | 1 MSps | Complex Float32 | Small generated test captures at known symbol rates. |

> [!NOTE]
> **The bundled captures are synthetic.** Their 4th-power spectral peaks all sit
> at exactly `f_s × 0.4` regardless of content — no real pulse-shaped signal
> behaves that way. Only `demo_bpsk_100ksps_1msps.iq` has a genuine, recoverable
> symbol clock. To generate more, use `scratch/make_ground_truth.py`.

---

## 3. Workstation User Interface Guide

```
+-------------------------------------------------------------------------------+
|  SIGMA  Signal Intelligence & Generalized Modulation Analyzer           [ ⚙ ] |
+-------------------------------------------------------------------------------+
|  INPUT  demo_bpsk_100ksps_1msps.iq  [fc32] [60,000 smp] [Rate: 1.00 MS/s]     |
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
|  SIGNAL ANALYSIS & DSP METRICS                                |  MODULATION   |
|  Peak Freq | Center Freq | BW | Power (dBFS)                   |  [ BPSK ]     |
|  Noise Flr | SNR         | RMS | Peak Amp                      |  Source:      |
|  SYMBOL RATE | SAMPLES/SYMBOL | SYMBOL RATE LOCK               |   measured    |
|  100.00 ksps | 10.00          | HIGH (37.7 dB)                 |               |
+---------------------------------------------------------------+---------------+
|  DEMODULATION & BITSTREAM                                     LOCKED         |
|  Symbols: 6000   Bits: 6000   EVM: 26.6%                  BPSK · RRC matched |
|  Carrier offset: +59,998 Hz   SPS used: 10.00   Timing: searched             |
|  RECOVERED BITSTREAM (first bits)                                            |
|  0110 0101 1001 1100 0110 1101 0010 1111 1000 0100 1100 0000 ...             |
+-------------------------------------------------------------------------------+
|  1. INPUT ✓  →  2. ANALYSIS ✓  →  3. MODULATION ✓  →  4. DEMOD ✓  →  5. BITS ✓ |
+-------------------------------------------------------------------------------+
```

When the demodulator declines (weak symbol-rate lock), the same card shows why
instead of a bitstream:

```
|  DEMODULATION & BITSTREAM                                   DECLINED          |
|  --                                                                          |
|  Symbol rate lock is only LOW (7.0 dB over the noise floor), so the          |
|  bitstream would be sampled on an untrusted clock. Declined.                 |
|  RECOVERED BITSTREAM (first bits)                                            |
|  --                                                                          |
```

### Key Operations:
1. **Loading a Signal File**:
   - Click **📂 Load Signal File** to select any `.iq`, `.bin`, `.raw`, `.dat`, `.cfile`, or `.wav` recording.
   - For `.wav` audio or SDR stereo captures, the workstation automatically converts them to an IEEE 754 `complex64` IQ binary file on-the-fly.
   - SIGMA infers sample rate from filenames containing `250k` (→ 250 kSps) or `1msps` / `1m` (→ 1 MSps). **If the filename carries no rate token, set it manually in ⚙ Settings** — an incorrect `f_s` scales symbol rate and SPS proportionally.
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
6. **Reading the DEMODULATION & BITSTREAM Card**:
   - This is the Stage 4/5 output — the actual result of demodulation, not just a status light.
   - `LOCKED` / `DECLINED` / `NO CLOCK` / `UNSUPPORTED` / `NOT RUN` — the state of the demodulator.
   - **Symbols / Bits / EVM** — how many symbols were recovered, how many bits, and the error-vector magnitude (a constellation quality score; lower is better).
   - **Carrier offset** — the residual frequency offset the 4th-power estimator found and removed. On a test signal built with a 60 kHz offset it reports ~+59,998 Hz.
   - **SPS used** — proof that the demodulator was driven by the *measured* symbol rate, not a hardcoded value.
   - **RECOVERED BITSTREAM (first bits)** — the leading 48 bits, grouped in nibbles. Ellipsis means more bits follow.
   - When declined, the bitstream shows `--` and the card states the measured reason instead.
7. **Reading the Pipeline Stepper**:
   - `✓` = stage completed. `○` = not completed.
   - **Hover the `4. DEMOD` label** for a one-line summary (e.g. `BPSK, 6000 symbols, EVM 26.6%`).
   - Stages 4–5 require a `MEDIUM` or better symbol-rate lock; on a weak lock the app declines rather than emitting an untrustworthy bitstream.

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
