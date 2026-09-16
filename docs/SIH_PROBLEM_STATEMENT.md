# Smart India Hackathon (SIH) Problem Statement

**Problem Statement ID:** 6147  
**Title:** Automated model for analysis of .IQ and .wav files along with signal parameter extraction  
**Organization:** National Technical Research Organisation (NTRO)  
**Department:** National Technical Research Organisation (NTRO)  
**Category:** Software  
**Theme:** Space Technology  

---

## 1. Background

The raw data for analysis of signals collected off the air typically ranges from a few kHz to GHz bands. Currently, analysis is often carried out manually to identify signal parameters, and the resultant data is utilized for processing signals in designated sensors.

However, raw collected data is frequently insufficient for fine-grained manual analysis to extract parameters such as:
- Modulation type
- Sampling rate
- Forward Error Correction (FEC)
- Interleaving schemes, etc.

This creates an urgent need for an automated, advanced data processing model to extract observation and intelligence data from signal captures.

---

## 2. Problem Description

Terrestrial and space-borne signals received from various sources include data across HF, VHF, and UHF bands. Raw radio data is recorded in `.wav` or `.IQ` formats to preserve the underlying waveform characteristics:

- **Format Differences:** `.IQ` and `.wav` store information differently (e.g. raw complex binary floats vs. audio container with headers). They require different ingestion and processing pipelines.
- **Varying Capture Parameters:** Signals recorded from different sensors, SDRs, and locations have varied sample rates, bandwidths, and noise levels.
- **Information Gaps:** Files often lack embedded metadata, making it difficult to immediately identify sampling rate, modulation, interleaving, and FEC.
- **Technology Approach:** GNU Radio, Python, and C++ can be combined to build automated signal intelligence pipelines that ingest `.IQ` and `.wav`, extract spectral features, classify modulations, and demodulate the signals down to raw bitstreams.

---

## 3. Core System Requirements (GUI-Based Model)

The GUI-based model takes `.IQ` or `.wav` files as input data and performs the following tasks:

### i. Identify Signal Parameters
- Sampling frequency estimation
- Modulation classification
- FEC scheme identification
- Interleaving type detection
- Additional signal features (SNR, power, bandwidth, constellation, etc.)

### ii. Demodulate Signals
Demodulation support for key digital modulation families:
- **FSK** (Frequency Shift Keying)
- **QAM** (Quadrature Amplitude Modulation)
- **PSK** (Phase Shift Keying: BPSK, QPSK, 8PSK, etc.)

### iii. De-interleaving
Automated detection and de-interleaving across standard modes:
- Block interleaving
- Convolutional interleaving
- Diagonal interleaving
- Pseudo-random interleaving

### iv. Forward Error Correction (FEC)
Decoding and error-correction pipelines:
- Short-constrained convolutional codes with Viterbi decoding
- Reed-Solomon (RS) block codes
- Concatenated codes
- Low-Density Parity-Check (LDPC) codes

### v. Bitstream Processing & Correlation
- Bitstream correlation for identification of packet structure
- Header detection and payload extraction

---

## 4. Expected Solution & Deliverables

1. **Intuitive GUI Application:**
   - Visual signal inspection tools: Time Domain (oscilloscope), RF Spectrum (FFT), Waterfall (time-frequency spectrogram), and Constellation diagram (IQ scatter).
2. **Automated Analysis Pipeline:**
   - Automatic detection of sampling frequency, bandwidth, and modulation type without requiring manual trial-and-error.
3. **End-to-End Processing:**
   - Signal Ingestion (`.IQ` / `.wav`) $\rightarrow$ Parameter Extraction $\rightarrow$ Demodulation $\rightarrow$ De-interleaving $\rightarrow$ FEC Decoding $\rightarrow$ Payload Bitstream Correlation.
