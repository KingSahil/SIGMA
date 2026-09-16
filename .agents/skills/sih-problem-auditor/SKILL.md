---
name: sih-problem-auditor
description: >-
  Use this skill to audit, track, and guide the development of SIGMA against the Smart India Hackathon (SIH 6147) Problem Statement for automated .IQ and .wav analysis, parameter extraction, demodulation, FEC, and bitstream correlation.
---

# SIH 6147 Problem Statement Auditor & Roadmap

This skill provides requirement tracking, compliance criteria, and development blueprints for **Smart India Hackathon (SIH) Problem Statement ID 6147** by the **National Technical Research Organisation (NTRO)**.

---

## 1. Official Problem Statement Overview

- **Title**: Automated model for analysis of .IQ and .wav files along with signal parameter extraction
- **Organization**: National Technical Research Organisation (NTRO)
- **Theme**: Space Technology
- **Category**: Software

---

## 2. Requirement Compliance Matrix

| SIH Requirement | Status | Current Code State | Next Action Required |
| :--- | :--- | :--- | :--- |
| **Ingestion of .IQ & .wav** | **Done (100%)** | `load_and_convert_wav()` in [`src/sigma_analyzer_core.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_analyzer_core.py) handles stereo IQ & mono audio. | Expand to support 8-bit unsigned / 16-bit signed raw IQ binaries. |
| **Time Domain Plot** | **Done (100%)** | `qtgui.time_sink_c` embedded in [`src/sigma_flowgraph.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_flowgraph.py). | Add trigger stabilization controls. |
| **Frequency Spectrum (FFT)** | **Done (100%)** | `qtgui.freq_sink_c` with Blackman-Harris window in [`src/sigma_flowgraph.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_flowgraph.py). | Add peak marker overlay. |
| **Constellation Diagram** | **Done (100%)** | `qtgui.const_sink_c` embedded in [`src/sigma_flowgraph.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_flowgraph.py). | Add symbol sync for clean constellation locking. |
| **Waterfall (Spectrogram)** | **Missing (0%)** | Not in UI or flowgraph. | Integrate `qtgui.waterfall_sink_c` into `SigmaFlowgraph` & UI splitter. |
| **Automatic Sample Rate Estimation** | **Missing (0%)** | Hardcoded to default `1,000,000 S/s` in UI. | Implement cyclostationary or energy transition rate estimator. |
| **Bandwidth & SNR Extraction** | **Missing (0%)** | Displays `--` fallback in metric cells. | Implement 99% / -3dB power bandwidth & noise-floor estimation. |
| **Modulation Classification** | **Missing (0%)** | Displays "Not analyzed". | Implement higher-order cumulants ($C_{40}, C_{42}$) or ML classifier. |
| **Digital Demodulation** | **Missing (0%)** | Only audio envelope preview exists; Stage 4 pending. | Add FSK, QAM, and PSK (BPSK, QPSK, 8PSK) demodulation blocks. |
| **De-interleaving** | **Missing (0%)** | Not implemented. | Implement matrix de-interleaving and convolutional de-interleaver. |
| **Forward Error Correction (FEC)** | **Missing (0%)** | Not implemented. | Implement Viterbi decoder (CC) and Reed-Solomon $(255, 223)$ decoder. |
| **Bitstream Correlation** | **Missing (0%)** | Stage 5 pending. | Implement sync-word / preamble correlator and frame extractor. |

---

## 3. Reference Implementation Steps

### Phase 1: Visual & Metric Enhancements (Quick Wins)
1. **Add Waterfall Sink**:
   In `src/sigma_flowgraph.py`, instantiate `qtgui.waterfall_sink_c(1024, window.WIN_BLACKMAN_hARRIS, center_freq, samp_rate)`.
2. **Compute Occupied Bandwidth & SNR**:
   In `SignalMetadata._analyze_file()`, compute 99% power spectral density bandwidth from FFT bins and calculate $SNR = 10 \log_{10}(P_{\text{signal}} / P_{\text{noise}})$.

### Phase 2: Signal Classification & Demodulation
1. **Higher-Order Cumulant Classifier**:
   Calculate cumulants $C_{20}, C_{21}, C_{40}, C_{41}, C_{42}$ to distinguish PSK, QAM, and FSK.
2. **Symbol Recovery**:
   Feed signal through Costas loop and Mueller-Müller symbol synchronizer to lock constellation points.

### Phase 3: Intelligence & FEC Decoding
1. **Demodulated Slicer**: Convert constellation symbols to hard bit decisions.
2. **Framing & Correlation**: Cross-correlate bitstream with standard sync preambles (e.g. Barker codes, CCSDS sync marker `0x1ACFFC1D`).
