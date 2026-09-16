# Technologies, Libraries & Tools Used

This document outlines the complete technology stack, third-party libraries, toolkits, runtime environments, and signal processing standards powering the **SIGMA** platform.

---

## 🛠️ Technology Stack Summary

| Category | Technology / Library | Version / Target | Purpose in SIGMA |
| :--- | :--- | :--- | :--- |
| **Language** | **Python** | 3.10+ (64-bit) | Application logic, UI controllers, metadata calculations, and glue code. |
| **DSP Framework** | **GNU Radio** | 3.10.x | Core C++ signal processing runtime, flowgraph topology, and streaming blocks. |
| **GUI Framework** | **PyQt5** | 5.15.x | Native desktop GUI, layout management, event handling, and dialogs. |
| **C++ / Python Bridge**| **SIP** (`sip.wrapinstance`) | v4 / v6 | Wrapping GNU Radio C++ QtGUI / Qwt widget pointers into PyQt5 widgets. |
| **Visual Sinks** | **GNU Radio QtGUI (Qwt)** | Bundled | Hardware-accelerated Time Domain, Frequency (FFT), and Constellation plots. |
| **Math & Vectors** | **NumPy** | >= 1.22.x | Vectorized sample analysis, complex64 arrays, RMS amplitude, peak detection. |
| **Scientific I/O** | **SciPy** (`scipy.io.wavfile`) | >= 1.9.x | Reading, validating, and writing 16-bit PCM RIFF WAV audio files. |
| **Audio Playback** | **Windows Multimedia (`winsound`)** | Standard Library | Asynchronous, low-latency audio playback on Windows OS without external drivers. |
| **Distribution** | **Radioconda** | Conda-forge SDR stack | Precompiled Windows distribution packaging GNU Radio, PyQt5, and all DSP dependencies. |
| **Visual Design** | **Custom QSS (Material Design 3)** | Custom | Custom Qt stylesheet implementing Google Stitch dark aesthetic with custom typography. |
| **Data Formats** | **Raw IQ (`complex64`) & WAV** | IEEE 754 / RIFF | 32-bit floating point complex In-Phase/Quadrature files and 16-bit PCM WAVs. |

---

## 📦 Detailed Breakdown of Components

### 1. GNU Radio Framework (`gnuradio`)
* **What it is**: The industry-standard open-source Software Defined Radio (SDR) and Digital Signal Processing (DSP) toolkit.
* **Why it is used**:
  - Delivers multi-threaded C++ streaming execution with high throughput.
  - Implements circular memory ring buffers between blocks.
  - Provides tested, high-speed blocks for file sourcing (`blocks.file_source`) and QtGUI visualization sinks (`qtgui.time_sink_c`, `qtgui.freq_sink_c`, `qtgui.const_sink_c`).
* **Key Modules Employed**:
  - `gnuradio.gr`: Base classes (`gr.top_block`, `gr.sizeof_gr_complex`).
  - `gnuradio.blocks`: I/O blocks (`file_source`).
  - `gnuradio.qtgui`: Real-time plot widgets.
  - `gnuradio.fft.window`: Windowing functions (e.g. `WIN_BLACKMAN_hARRIS`).
  - `pmt`: Polymorphic Type library for passing tags and stream metadata.

---

### 2. PyQt5 Desktop GUI Suite
* **What it is**: Python bindings for the Qt application framework by Riverbank Computing.
* **Why it is used**:
  - Provides cross-platform desktop UI components (`QMainWindow`, `QSplitter`, `QFrame`, `QGridLayout`, `QDialog`).
  - Enables CSS-like declarative styling through **Qt Style Sheets (QSS)**.
  - Features robust signal/slot inter-widget communication for responsive user actions.
* **Key Modules Employed**:
  - `PyQt5.QtWidgets`: Core windowing and layout widgets (`QApplication`, `QLabel`, `QPushButton`, `QSplitter`, `QDialog`, `QFormLayout`).
  - `PyQt5.QtCore`: Event handling, timers (`QTimer`), window flags, and alignment constants.
  - `PyQt5.QtGui`: Fonts, color palettes (`QPalette`), and visual drawing primitives.

---

### 3. SIP C++ Python Bridge (`sip`)
* **What it is**: A tool by Riverbank Computing for creating Python bindings for C and C++ libraries.
* **Why it is used**:
  - GNU Radio's QtGUI sinks are implemented in C++ and return raw memory addresses/pointers to `QWidget` or `QwtPlot` instances via `.qwidget()`.
  - Python cannot directly treat a C++ memory address as a PyQt5 widget without SIP.
  - `sip.wrapinstance(sink.qwidget(), QtWidgets.QWidget)` wraps the C++ pointer into a fully-functional PyQt5 widget that can be inserted into layouts.

---

### 4. NumPy (`numpy`)
* **What it is**: The fundamental library for array computing and linear algebra in Python.
* **Why it is used**:
  - Rapidly ingests binary files directly into memory using `np.fromfile(filepath, dtype=np.complex64)`.
  - Performs vectorized mathematical transformations across tens of thousands of samples simultaneously in C speeds:
    - Absolute value / Magnitude: `np.abs(data)`
    - Root-Mean-Square (RMS): `np.sqrt(np.mean(magnitudes ** 2))`
    - Fast Fourier Transform for peak detection: `np.fft.fft` and `np.fft.fftshift`
    - Blackman window generation: `np.blackman(N)`

---

### 5. SciPy (`scipy.io.wavfile`)
* **What it is**: Open-source scientific computing algorithms for Python.
* **Why it is used**:
  - Reads RIFF WAV audio files (`wavfile.read()`) to extract raw sample arrays, channel counts (mono vs stereo), and sampling rates.
  - Writes synthesized baseband audio files (`wavfile.write()`) formatted as 16-bit signed PCM integers (`np.int16`).

---

### 6. Windows Multimedia & Audio Engine (`winsound`)
* **What it is**: Built-in Python standard library module interfacing directly with the Windows Multimedia API (`winmm.dll`).
* **Why it is used**:
  - Zero external dependencies: requires no PortAudio, PyAudio, or SDL installations.
  - `PlaySound(target, SND_ASYNC | SND_FILENAME)` offloads audio streaming to the Windows OS kernel sound server without blocking the Qt main loop.
  - `PlaySound(None, SND_PURGE)` provides instant, glitch-free audio termination.

---

### 7. Runtime Environment: Radioconda
* **What it is**: A specialized, self-contained Conda-forge distribution curated by Ryan Volz for Software Defined Radio on Windows, Linux, and macOS.
* **Why it is used**:
  - GNU Radio cannot be reliably installed on Windows using standard `pip install gnuradio` due to complex C++ compiler toolchains, Boost libraries, and Qt5 dependencies.
  - Radioconda includes precompiled, binary-compatible builds of:
    - GNU Radio 3.10
    - Python 3.10 / 3.11
    - PyQt5 & SIP
    - NumPy, SciPy, Matplotlib
    - Volk (Vector-Optimized Library of Kernels) for SIMD acceleration

---

### 8. Custom Design System & Qt Style Sheets (QSS)
* **What it is**: A bespoke design system implemented in `sigma_theme.py` inspired by **Google Stitch** and **Material Design 3**.
* **Key Design Characteristics**:
  - **Dark Slate Palette**: `#0d1117` base workspace, `#161b24` elevated card containers, `#1d2430` inner metric cells.
  - **Google Accent Colors**: Sky Blue (`#38bdf8`), Emerald Green (`#34d399`), and Coral/Rose (`#f43f5e`).
  - **High-Contrast Typography**: Monospaced font stacks (`Consolas`, `JetBrains Mono`) for telemetry values with large 22px bold weights.
  - **Interactive Micro-States**: Distinct visual styling for `:hover`, `:pressed`, and active playback state transitions.
