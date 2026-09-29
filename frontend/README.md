# 🛰️ SignalForge — RF Signal Intelligence & Demodulation Platform

> **Advanced web-based RF laboratory for parameter extraction, blind demodulation, de-interleaving, and forward error correction of `.iq` and `.wav` signal captures.**

---

## 📌 Problem Statement Context (PS 26147)

Traditional RF analysis pipelines often treat signal classification as a "black-box AI" problem. **SignalForge** takes a deterministic, defense-grade digital communications approach:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        SIGNALFORGE PIPELINE                            │
│                                                                        │
│   RAW FILE INPUT              SPECTRAL & PARAMETER EXTRACTION          │
│   (.IQ / .WAV / .BIN)  ➔     • Power Spectrum Density (FFT dBFS)       │
│                               • Time-Frequency Waterfall (Spectrogram) │
│                               • I/Q Constellation Scatter Scope        │
│                               • Carrier (Fc), Bandwidth & SNR Bounds   │
│                                               │                        │
│                                               ▼                        │
│   BURST DE-INTERLEAVING                 DEMODULATION STUDIO            │
│   • Block Interleaver (Matrix M×N)    • FSK (2-FSK, 4-FSK)           │
│   • Convolutional Interleaver         • PSK (BPSK, QPSK, 8-PSK)        │
│   • Diagonal & Pseudo-Random          • QAM (16-QAM, 64-QAM)           │
│   • Before/After Bit Diff View        • Recovered Bitstream Extraction │
│                 │                                                      │
│                 ▼                                                      │
│   FORWARD ERROR CORRECTION (FEC)        FRAME CORRELATION & SYNC       │
│   • Soft-Decision Viterbi (K=7)   ➔    • Preamble Cross-Correlation    │
│   • Reed-Solomon RS(255, 223)          • Barker 11/13 & Sync Vectors   │
│   • Syndrome & Residual BER Check      • Telemetry Payload Extraction  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. 📂 Signal Ingestion Console
* **Dual Ingestion:** Drag-and-drop raw complex floating-point captures (`.iq`, `.bin`) or baseband audio (`.wav`).
* **Pre-calibrated Benchmarks:** Instant access to pre-recorded aerospace signals (*CubeSat UHF 433.92 MHz*, *NOAA Weather Sat 137.10 MHz*, *Tactical UAV 868.00 MHz*).
* **Sample Format Support:** Interleaved IEEE-754 complex64 (Float32 I + Float32 Q) and linear PCM audio.

### 2. 📊 High-Performance Canvas Visualizers (60 FPS)
* **FFT Power Spectrum:** Dynamic dBFS power curve with peak carrier detection and 3dB bandwidth markers.
* **Time-Frequency Waterfall:** Real-time scrolling STFT spectrogram with scientific heat-energy color mapping.
* **I/Q Constellation Scope:** Orthogonal complex plane scatter plot with decision boundary targets and Error Vector Magnitude (EVM) readout.

### 3. 📡 Demodulation Studio
* **Multi-Family Slicing:** BPSK, QPSK, 8-PSK, 16-QAM, 64-QAM, 2-FSK, and 4-FSK.
* **Symbol & Bitstream Viewer:** Live extraction of thousands of recovered bits with one-click clipboard copy.

### 4. 🔄 Matrix De-interleaver
* **4 Supported Schemes:** Block Interleaving, Convolutional Interleaving, Diagonal, and Pseudo-Random.
* **Tunable Parameters:** Interactive Matrix Depth (Rows) and Matrix Width (Columns) controls.
* **Bit Diff Inspector:** Side-by-side comparison of interleaved input vs. de-interleaved output with reordered bit counting.

### 5. 🧮 FEC & Error Correction
* **Decoders:** Soft-decision Viterbi trellis decoding ($K=7$, Rate $1/2$) and Reed-Solomon $RS(255, 223)$ over Galois Field $GF(2^8)$.
* **Telemetry:** Total input bits, corrected errors counter, estimated post-FEC Bit Error Rate (BER), and parity syndrome status.

### 6. 🔗 Frame Correlation & Preamble Extraction
* **Sliding Correlation:** Normalized cross-correlation $R_{xy}$ against known sync preambles (Barker codes, `0xACD2`, CCSDS markers).
* **Payload Hunter:** Discards transmission flush bits and automatically decodes recovered hex/ASCII telemetry payloads.

---

## ⚡ Dual-Engine Architecture

The frontend is architected with a **Dual-Mode Engine** so it never blocks during backend development:

| Mode | Purpose | How It Works |
|---|---|---|
| **SIMULATION** (Default) | Demo & Testing | Generates mathematically authentic RF signals, Gaussian AWGN noise, and real matrix permutations client-side. Zero backend required. |
| **FASTAPI LIVE** | Live Production | Sends asynchronous REST/WebSocket requests directly to the Python/GNU Radio backend (`http://localhost:8000/api/...`). |

---

## 🛠️ Tech Stack

* **Framework:** Next.js 16 (App Router) + Turbopack
* **Language:** TypeScript 5 (Strictly Typed)
* **Styling:** Tailwind CSS v4
* **Typography:** Plus Jakarta Sans & JetBrains Mono
* **DSP Graphics:** Native HTML5 Canvas 2D (zero heavy third-party plotting dependencies)
* **Icons:** Lucide React

---

## 📁 Project Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx             # Root layout with fonts & metadata
│   │   ├── page.tsx               # Main landing & workbench router
│   │   └── globals.css            # Dark theme, glow effects & custom scrollbars
│   ├── components/
│   │   ├── hero/
│   │   │   ├── HeroSection.tsx    # Primary landing page hero
│   │   │   ├── HeroNavbar.tsx     # Brand navigation header
│   │   │   ├── HeroProductPreview.tsx # 4-quadrant oscilloscope preview
│   │   │   ├── MiniSpectrumPlot.tsx   # Canvas power spectrum
│   │   │   ├── MiniWaterfallPlot.tsx  # Canvas spectrogram heatmap
│   │   │   └── MiniConstellationPlot.tsx # Canvas I/Q scatter plot
│   │   ├── workbench/
│   │   │   └── LabWorkbench.tsx   # Full 5-stage interactive RF laboratory
│   │   ├── modules/
│   │   │   └── IngestionModal.tsx # Preset benchmarks & raw file dropzone
│   │   ├── visualizers/
│   │   │   ├── InstrumentSpectrum.tsx      # Precision FFT analyzer
│   │   │   ├── InstrumentWaterfall.tsx     # Precision spectrogram
│   │   │   └── InstrumentConstellation.tsx # Precision I/Q scope
│   │   ├── sections/
│   │   │   ├── PipelineFlow.tsx   # Mathematical pipeline anatomy
│   │   │   └── SpecSheet.tsx      # Aerospace capability matrix
│   │   └── layout/
│   │       ├── Header.tsx         # Technical header with telemetry
│   │       └── Footer.tsx         # Technical system footer
│   ├── context/
│   │   └── SignalContext.tsx      # Global state for files, telemetry & pipeline
│   └── lib/
│       ├── dsp-types.ts           # Shared TypeScript interfaces for RF stages
│       ├── dsp-mock.ts            # Mathematical simulation generators
│       └── utils.ts               # Class merging utilities (cn)
├── public/                        # Static assets
├── package.json                   # Dependencies & build scripts
└── tsconfig.json                  # TypeScript compiler settings
```

---

## 🚦 Getting Started

### Prerequisites
* **Node.js:** v18.18.0 or later (v20+ recommended)
* **npm:** v9+

### Installation
```bash
# Clone or navigate to the frontend directory
cd SignalForge/frontend

# Install dependencies
npm install
```

### Running Locally (Development Mode)
```bash
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

### Creating a Production Build
```bash
# Build the optimized production bundle with Turbopack
npm run build

# Start the production server
npm start
```

---

## 🤝 Integration with Backend (GNU Radio / Radioconda)

If your backend team is running the **SIGMA IQ Analyzer** via GNU Radio / Radioconda:

1. **Input Match:** Ensure the backend reads the same raw binary format (`complex64`, 32-bit float $I$ and $Q$).
2. **API Handshake:** Point the frontend API client (`src/services/api.ts`) to the backend server (typically `http://localhost:8000`).
3. **Toggle Live Mode:** Switch the header toggle from `SIMULATION` to `FASTAPI LIVE` to stream live GNU Radio frames into the web interface.

---

## 📜 License
Developed for the **SignalForge RF Communications & Signal Intelligence Project (PS 26147)**.
