# SIGMA Documentation

Welcome to the technical documentation for **SIGMA** (**S**ignal **I**ntelligence & **G**eneralized **M**odulation **A**nalyzer).

SIGMA is an RF signal intelligence workstation and real-time visualization platform built on **GNU Radio** and **PyQt5**. It provides real-time In-Phase/Quadrature (I/Q) signal analysis across time, frequency, and constellation domains, accompanied by physical signal parameter extraction and audio demodulation/previewing capabilities.

---

## 📚 Documentation Index

| Document                                                                                                           | Description                                                                                                                                         |
| :----------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[SIH Problem Statement 6147](file:///c:/Users/sahil/Downloads/gnu/docs/SIH_PROBLEM_STATEMENT.md)**               | Official Smart India Hackathon problem statement from NTRO: objectives, scopes, requirements, and deliverables.                                     |
| **[Architecture Guide](file:///c:/Users/sahil/Downloads/gnu/docs/ARCHITECTURE.md)**                                | Detailed system architecture, component breakdown, data flow diagrams, thread lifecycle, and subsystem interactions.                                |
| **[L1 / L2 / L3 Architecture](file:///c:/Users/sahil/Downloads/gnu/docs/L1_L2_L3_ARCHITECTURE.md)**                | Layer boundaries for the analytics pipeline and the interface contract handed to the ML model.                                                      |
| **[Team Tasks & Owners](file:///c:/Users/sahil/Downloads/gnu/docs/TEAM_TASKS.md)**                                 | Remaining work broken down by owner, with measured evidence, root causes, and a suggested sequence.                                                |
| **[Notion Plan vs. Reality](file:///c:/Users/sahil/Downloads/gnu/docs/NOTION_RECONCILIATION.md)**                   | The team's Notion plan audited against the measured state of the code: what matches, what diverges, and the decisions that need a human.            |
| **[CNN Input & Training](file:///c:/Users/sahil/Downloads/gnu/docs/CNN_INPUT_AND_TRAINING.md)**                     | What the model eats and how it is trained, with a working dataset builder and a measured baseline (97.7% on generated ground truth).               |
| **[Verification & Proven Results](file:///c:/Users/sahil/Downloads/gnu/docs/VERIFICATION.md)**                     | **How every DSP result was proven** against generated ground truth, plus the known limitations and the one approach that was measured and rejected. |
| **[Technologies & Tools Used](file:///c:/Users/sahil/Downloads/gnu/docs/TECHNOLOGIES_USED.md)**                    | Comprehensive catalog of all programming languages, libraries, DSP toolkits, environments, UI design systems, and data formats used.                |
| **[Data Pipeline & Signal Formats](file:///c:/Users/sahil/Downloads/gnu/docs/DATA_PIPELINE_AND_FORMATS.md)**       | In-depth explanation of IQ theory, binary data formats, sample rate conversions, WAV-to-IQ conversion algorithms, and the multi-stage DSP pipeline. |
| **[Getting Started & Developer Guide](file:///c:/Users/sahil/Downloads/gnu/docs/GETTING_STARTED_AND_WORKFLOW.md)** | Setup instructions, Radioconda environment configuration, operational workflows, sample signal datasets, and troubleshooting.                       |



---

## 📌 Current Status at a Glance

| Stage                         | State                 | Evidence                                                                |
| :---------------------------- | :-------------------- | :---------------------------------------------------------------------- |
| 1. INPUT                      | ✅ Done                | File ingestion, WAV→IQ conversion                                       |
| 2. ANALYSIS                   | ✅ Done                | Real metrics, no mock values                                            |
| 3. MODULATION                 | ✅ Done                | Symbol rate **10/10 locked**, PSK order from the M-th power test, filename-independent |
| 4. DEMOD                      | ✅ Done, quality-gated | **46/46 at 100.00%** bit accuracy                                       |
| 5. BITS                       | ✅ Done, quality-gated | 6000 bits recovered in the GUI on the demo capture                      |
| Sampling-frequency estimation | ⚠️ **Impossible; resolved not measured** | `f_s` has no observable in the samples. Resolved by `sigma_sample_rate.py` with ranked provenance, shown in the GUI |
| CNN modulation classifier     | 🟡 **Features + dataset done, model not trained** | **97.7%** on 360 generated captures (chance 25%) via `scratch/train_baseline_model.py`. No ML framework installed yet. See [CNN_INPUT_AND_TRAINING.md](CNN_INPUT_AND_TRAINING.md) |
| 16QAM demodulation            | 🟢 **Works, gate blocks it** | **99.98%** bit accuracy measured; the GUI gate refuses it |
| 8PSK demodulation             | 🔴 **Broken, cause known** | 51.70% (random). Cause: carrier recovery exponent hardcoded to `x⁴` |
| De-interleaving, FEC          | ❌ Not started         | Required by the problem statement                                       |

"Quality-gated" means the stage refuses to run when the symbol-rate lock is  
untrustworthy, and explains why in the UI tooltip. Refusing is the correct  
behaviour: a bitstream sampled on the wrong clock looks valid and is not.

---

## 🗺️ System Map at a Glance

```
  +-------------------------------------------------------------------------+
  |                             SIGMA WORKSTATION                           |
  |                                                                         |
  |  +-----------------------+     +-------------------+     +-----------+  |
  |  |      Input Signal     |     |   DSP Flowgraph   |     |    GUI    |  |
  |  |  (.iq / .bin / .wav)  | --> |    (GNU Radio)    | --> |  (PyQt5)  |  |
  |  +-----------------------+     +-------------------+     +-----------+  |
  |              |                           |                     |        |
  |              v                           v                     v        |
  |      +---------------+           +---------------+     +-------------+  |
  |      |   Metadata    |           | Visual Sinks  |     |   Audio     |  |
  |      |  Extraction   |           | Time/Freq/    |     | Demodulator |  |
  |      | (NumPy Core)  |           | Constellation |     |  (winsound) |  |
  |      +---------------+           +---------------+     +-------------+  |
  +-------------------------------------------------------------------------+
```

---

## ⚡ Key Highlights

- **Truth-in-Metrics Core**: All physical DSP metrics (RMS amplitude, peak amplitude, dBFS power, peak frequency, 99% OBW, noise floor, SNR, symbol rate, and modulation class) are computed from real sample data using NumPy — no mocked values, and no fabricated confidence percentages.
- **Complete 5-Stage Pipeline**: Input → Analysis → Modulation → **Demodulation** → **Bitstream**. Symbol rate measured from envelope cyclostationarity; carrier recovery, RRC matched filtering, and symbol timing in `sigma_demod.py`.
- **Verified Against Ground Truth**: Symbol rate 10/10 locked (9 at 0.00% error); demodulation **46/46 configurations at exactly 100.00% bit accuracy, BER 0.0000**. See [`VERIFICATION.md`](VERIFICATION.md).
- **Honest Refusal Over Plausible Nonsense**: When the symbol-rate lock is too weak, stages 4–5 decline and explain why in the tooltip, rather than emitting a bitstream sampled on a clock it does not trust.
- **Four Real-Time GNU Radio Sinks**: Time Domain, Frequency Spectrum (FFT), Waterfall (spectrogram), and Constellation Diagram — all in a 2×2 resizable grid.
- **View Mode Switcher + HUD Overlay**: Five toggle buttons collapse the 2×2 grid into a single full-resolution sink. Interactive click/drag on any plot shows live coordinate readouts.
- **Multi-Mode Audio Demodulator**: FM discriminator, envelope detector, and BFO heterodyne mixer auto-blend based on signal characteristics, outputting 44.1 kHz 16-bit PCM for low-latency Windows playback.
- **GNU Radio 3.10 Integration**: High-performance C++ DSP flowgraph with throttle-controlled stream processing and thread-safe dynamic file reloading.
- **Modern Google Stitch / Material Design 3 UI**: Clean dark aesthetic with custom QSS typography, resizable splitters, and preview capture for instant frozen plot display on startup.
