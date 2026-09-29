# SIGMA — Feature Status vs Learning Curriculum

Curriculum roadmap (Levels 1–5) mapped to current SIGMA implementation status. Grounded
in the actual codebase (`src/`) — not in assumptions.

Legend: ✅ done · ⚠️ partial · ❌ not implemented · 🔍 verifiable in API/UI

---

## Level 1 — IQ, complex numbers, sampling, FFT _(Must learn)_ ✅

| Feature | Status | Where it lives |
|---|---|---|
| IQ complex-baseband load | ✅ | `src/sigma_analyzer_core.py` (`SignalMetadata`), `src/backend/signal_io.py` |
| WAV → IQ conversion (stereo-aware) | ✅ | `load_and_convert_wav` in `sigma_analyzer_core.py:464` |
| `np.fft.fft` + `fftshift` spectrum | ✅ | `sigma_analyzer_core.py:277-280` |
| `f_s` (sample-rate) provenance | ✅ | `src/sigma_sample_rate.py` (multi-source ranking) |
| M-th-power carrier offset (BPSK² / QPSK⁴) | ✅ | `sigma_api.py:215` |
| API endpoint | 🔍 | `POST /api/analyze_advanced`, `POST /analyze` |

**Left:** Nothing critical. Educationally: time-frequency dual of FFT (the chirp/DFT
matrix) is implicit, not a separate code path.

---

## Level 2 — Filtering, PSD, spectrogram, SNR, bandwidth _(Must learn)_ ✅

| Feature | Status | Where it lives |
|---|---|---|
| Welch PSD (averaged FFT, 50% overlap) | ✅ | `sigma_symbol_rate.py:15,142`, `sigma_demod.py:162` |
| Waterfall / spectrogram sink | ✅ | `sigma_flowgraph.py:129` Waterfall Sink; desktop card in `sigma_main_window.py:663` |
| SNR (PSD-based median noise-floor) | ✅ | `backend/analysis_engine.py:34`, `sigma_analyzer_core.py:305-312` |
| 99 % Occupied Bandwidth | ✅ | `sigma_sample_rate.py:13` (`OBW = f_s * occupied`), `sigma_analyzer_core.py:290-302` |
| RRC pulse shaping filter | ✅ | `sigma_api.py:156` `modulate_bitstream` |
| API endpoints | 🔍 | `GET /signals/{id}/spectrum`, `/spectrogram` |

**Left:** Nothing critical. Possible additions: instantaneous-frequency tracking,
instantaneous-bandwidth, higher-order spectra (bispectrum) — purely educational/
research-grade, not needed for the SIH pipeline.

---

## Level 3 — Modulation, synchronization, symbol rate, demodulation _(Must learn)_ ✅

| Feature | Status | Where it lives |
|---|---|---|
| Symbol-rate estimation (cyclostationary envelope) | ✅ | `src/sigma_symbol_rate.py` |
| Constellations: BPSK, QPSK, 8PSK, 16QAM, BFSK, 4FSK | ✅ | `sigma_api.py:76-90` `CONSTELLATIONS` dict |
| PSK-order detection (2/4/8 line scores) | ✅ | `sigma_analyzer_core.py:160,218` |
| Symbol timing sync (Gardner-style) | ✅ | `sigma_api.py` `symbol_timing_sync` |
| Carrier phase recovery (decision-directed) | ✅ | `sigma_api.py` `carrier_phase_recovery` |
| Soft demodulation + EVM | ✅ | `soft_demodulate_symbols` (`sigma_api.py:399`) |
| Multi-phase occupancy guard | ✅ | `_occupies_multiple_phases` (`sigma_demod.py:903`) |
| API endpoints | 🔍 | `/api/modulate`, `/api/synchronize`, `/api/demodulate`, `/recover` |

**Left:** Nothing critical. Could add: **64QAM, 32QAM** if higher-order modems become a
target (currently capped at 16QAM). AM/FM is mentioned in the recovery orchestrator
docstring but not implemented as a full classifier.

---

## Level 4 — FEC, interleaving, advanced synchronization _(Learn selectively)_ ⚠️ mostly

| Feature | Status | Where it lives |
|---|---|---|
| Convolutional + Viterbi (hard & soft) | ✅ | `src/fec/convolutional.py`, `sigma_coding.py:150` |
| Reed-Solomon block code | ✅ | `src/fec/reed_solomon.py` |
| LDPC | ✅ | `src/fec/ldpc.py` |
| Concatenated RS + Convolutional | ✅ | `src/fec/concatenated.py` |
| Hamming (7,4) | ✅ | `sigma_api.py:608` |
| **Turbo codes** | ❌ | — |
| Block interleaver | ✅ | `src/deinterleaving/block.py` |
| Convolutional interleaver | ✅ | `src/deinterleaving/convolutional.py` |
| Diagonal / helical interleaver | ✅ | `src/deinterleaving/diagonal.py` |
| Pseudo-random interleaver | ✅ | `src/deinterleaving/pseudo_random.py` |
| Blind convolutional-code search | ✅ | `search_convolutional_code` (`sigma_coding.py:403`) |
| Header / payload correlation | ✅ | `src/correlation/` (alignment, header_detection, payload_detection, scoring) |
| **Adaptive equalizer (CMA / LMS / DD)** | ❌ | — |
| **Channel estimation / pilot-aided sync** | ❌ | — |

**Left to do in Level 4:**
1. **Turbo codes** (encoder + BCJR/soft-input Viterbi iterative decoder)
2. **Adaptive equalizer** — at minimum a constant-modulus algorithm (CMA) blind equalizer
   and an LMS decision-directed equalizer. Without these, ISI-heavy channels (e.g. cellular,
   HF multipath) cannot be reliably recovered.
3. **Pilot-aided channel estimation** — needed for any coherent detection in time-selective
   fading.

API endpoints for everything implemented: `/api/deinterleave`, `/api/fec_decode`,
`/deinterleave`, `/fec/decode`, `/correlate`.

---

## Level 5 — Advanced communication theory _(Not necessary initially)_ ❌

| Feature | Status |
|---|---|
| OFDM (FFT-based multicarrier demod, CP removal, equalization) | ❌ |
| MIMO / space-time coding (Alamouti, V-BLAST) | ❌ |
| DSSS / FHSS spread-spectrum despreading | ❌ |
| Adaptive coding & modulation (ACM) | ❌ |
| Information-theoretic decoding (LDPC belief-propagation deep dive, polar codes) | partial via LDPC |
| Full-duplex / self-interference cancellation | ❌ |
| Network-layer stacks (MAC, ARQ, routing on top) | ❌ |

**Left — entire Level 5 is open.** Per the curriculum ("Not necessary initially"),
this is expected. If SIGMA ever targets cellular / Wi-Fi / modern wideband waveforms,
OFDM is the single highest-impact addition.

---

## One-screen summary

```
Level 1  IQ / sampling / FFT                    [████████████████████] DONE
Level 2  Filtering / PSD / SNR / OBW            [████████████████████] DONE
Level 3  Modulation / sync / symbol / demod     [████████████████████] DONE
Level 4  FEC / interleaving / adv. sync         [██████████████░░░░░░] PARTIAL  ← turbo + adaptive EQ missing
Level 5  OFDM / MIMO / spread-spec / turbo      [░░░░░░░░░░░░░░░░░░░░] NOT STARTED
```

## Concrete "left" backlog (priority order)

1. **Adaptive equalizer (CMA / LMS-DD)** — Level 4 gap, blocks ISI-heavy real-world IQ.
2. **Turbo codes** — Level 4 gap, only block/convolutional/LDPC families covered.
3. **64QAM** — Level 3 extension if higher spectral-efficiency targets appear.
4. **OFDM demod** — Level 5, only needed if the waveform target list expands.
5. **MIMO / spread-spectrum** — Level 5, opt-in by mission profile.