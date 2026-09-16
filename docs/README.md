# SIGMA Documentation

Welcome to the technical documentation for **SIGMA** (**S**ignal **I**ntelligence & **G**eneralized **M**odulation **A**nalyzer).

SIGMA is an RF signal intelligence workstation and real-time visualization platform built on **GNU Radio** and **PyQt5**. It provides real-time In-Phase/Quadrature (I/Q) signal analysis across time, frequency, and constellation domains, accompanied by physical signal parameter extraction and audio demodulation/previewing capabilities.

---

## 📚 Documentation Index

| Document | Description |
| :--- | :--- |
| **[SIH Problem Statement 6147](file:///c:/Users/sahil/Downloads/gnu/docs/SIH_PROBLEM_STATEMENT.md)** | Official Smart India Hackathon problem statement from NTRO: objectives, scopes, requirements, and deliverables. |
| **[Architecture Guide](file:///c:/Users/sahil/Downloads/gnu/docs/ARCHITECTURE.md)** | Detailed system architecture, component breakdown, data flow diagrams, thread lifecycle, and subsystem interactions. |
| **[Technologies & Tools Used](file:///c:/Users/sahil/Downloads/gnu/docs/TECHNOLOGIES_USED.md)** | Comprehensive catalog of all programming languages, libraries, DSP toolkits, environments, UI design systems, and data formats used. |
| **[Data Pipeline & Signal Formats](file:///c:/Users/sahil/Downloads/gnu/docs/DATA_PIPELINE_AND_FORMATS.md)** | In-depth explanation of IQ theory, binary data formats, sample rate conversions, WAV-to-IQ conversion algorithms, and the multi-stage DSP pipeline. |
| **[Getting Started & Developer Guide](file:///c:/Users/sahil/Downloads/gnu/docs/GETTING_STARTED_AND_WORKFLOW.md)** | Setup instructions, Radioconda environment configuration, operational workflows, sample signal datasets, and troubleshooting. |

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

- **Truth-in-Metrics Core**: Calculates authentic physical properties (RMS amplitude, peak voltage, dBFS power, peak frequency with FFT windowing) rather than mocked telemetry.
- **GNU Radio 3.10 Integration**: High-performance C++ digital signal processing flowgraph with zero-copy stream processing.
- **Modern Google Stitch / Material Design 3 UI**: Clean dark aesthetic with custom typography, responsive splitters, and real-time visualization widgets.
- **Native Audio Subsystem**: Instant AM/envelope demodulation and baseband audio previewing for RF and acoustic recordings.
