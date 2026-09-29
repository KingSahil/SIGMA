# SIGMA — Complete System Architecture

**SIGMA** = **S**ignal **I**ntelligence & **G**eneralized **M**odulation **A**nalyzer
(SIH 2026, Problem Statement 6147 — NTRO / RF signal analysis)

> Scope: this document describes the **whole repository** — desktop app, web frontend,
> API backend, DSP core, RAG subsystem, and storage. For the deep desktop-only detail
> (symbol-rate estimator internals, demodulation gating, audio subsystem, threading
> model) see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. What SIGMA does, in one paragraph

You hand it a raw RF capture (`.iq` or `.wav`). It measures the signal, figures out how
fast it is ticking and what modulation it uses, locks onto that clock, demodulates it
into bits, undoes any interleaving, decodes forward error correction, hunts for
structure in the resulting bitstream, and reports everything back — **including an
explicit refusal when a stage cannot be trusted**, rather than a plausible-looking wrong
answer. Three different front-ends (desktop, web, raw API) all drive the same pipeline.

---

## 2. The big picture — five layers

```
┌─ Layer 1 ── CLIENTS ────────────────────────────────────────────────┐
│  Desktop workstation   │  SignalForge web      │  REST / WS clients │
│  PyQt5 + GNU Radio     │  Next.js 16 + Canvas  │  scripts, tests    │
└────────────────────────────────┬────────────────────────────────────┘
                                 ▼  HTTP / WebSocket
┌─ Layer 2 ── API GATEWAY ────────────────────────────────────────────┐
│  FastAPI (uvicorn :8000) · REST + WebSocket · CORS                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 ▼
┌─ Layer 3 ── SERVICES ───────────────────────────────────────────────┐
│  Measurement engine    │  Deep pipeline        │  RAG service       │
│  FFT·PSD·SNR·OBW       │  L1→L2→L3 orchestr.   │  retrieval+answers │
└──────────────┬─────────────────┬───────────────────────┬────────────┘
               ▼                 ▼                       ▼
┌─ Layer 4 ── SIGNAL PROCESSING CORE (src/) ──────────┐   ┌──────────┐
│  L1 ingest │ L2 analyze │ L3 demod · deint · FEC     │   │ Gemini   │
└────────────────────────┬────────────────────────────┘   └────┬─────┘
                         ▼                                     ▼
┌─ Layer 5 ── DATA LAYER ─────────────────────────────────────────────┐
│  sigma.db · sigma_rag.sqlite3 · data/iq · data/wav · uploads · docs │
└─────────────────────────────────────────────────────────────────────┘
```

A rendered version of this diagram is saved as
[`sigma_full_architecture.svg`](../sigma_full_architecture.svg).

---

## 3. Layer 1 — Clients

Three completely independent front-ends. You can run any one of them, or all three at
once, against the same backend.

### 3.1 Desktop workstation (PyQt5 + GNU Radio)

| Piece | File | Role |
|---|---|---|
| Launcher | `run.py` → `src/sigma_iq_analyzer.py` | Adds `src/` to `sys.path`, sets a Windows AppUserModelID, installs SIGINT/SIGTERM handlers, 500 ms `QTimer` heartbeat so Ctrl+C works |
| Main window | `src/sigma_main_window.py` (1794 LOC) | The "RF Intelligence Workstation": input bar, 4 live plots, metrics grid, 5-stage pipeline stepper, demodulation/bitstream card |
| Flowgraph | `src/sigma_flowgraph.py` | `gr.top_block` wrapping GNU Radio: `blocks.file_source` → `blocks.throttle` → 4 `qtgui` sinks |
| GRC definition | `grc/SIGMA_IQ_Analyzer.grc` | Same flowgraph in GNU Radio Companion form |
| Theme | `src/sigma_theme.py` | Dark palette (`#0b0f17` bg, `#38bdf8` accent), unified QSS, custom app icon |

**The four live plots** are GNU Radio QtGUI widgets bridged into PyQt5 with
`sip.wrapinstance(sink.qwidget(), Qt.QWidget)`:

| Sink | Shows |
|---|---|
| `qtgui.time_sink_c` | I (cyan) and Q (magenta) vs time |
| `qtgui.freq_sink_c` | 1024-pt FFT, Blackman-harris window, dB |
| `qtgui.waterfall_sink_c` | Time-frequency spectrogram |
| `qtgui.const_sink_c` | IQ scatter / constellation |

**Pipeline stepper** — `1 INPUT → 2 ANALYSIS → 3 MODULATION → 4 DEMOD → 5 BITS`.
Stages 4 and 5 are **gated on symbol-rate lock quality**: a `LOW` confidence clock means
demodulation is declined, because a bitstream sampled on an untrusted clock is
*plausible and wrong*, which is worse than an honest refusal.

**Audio subsystem** (`AudioManager`) — three auto-selected demod paths so you can
*listen* to RF: FM discriminator (phase std > 0.15), envelope detector (amp std > 0.12),
or BFO heterodyne mixer (PSK/CW). Decimates to 44.1 kHz, plays via `winsound.SND_ASYNC`.

### 3.2 SignalForge — web frontend

`frontend/` — Next.js 16.3.5, React 19.2.8, TypeScript 5, Tailwind v4, three.js.

| Piece | File | Role |
|---|---|---|
| Page | `src/app/page.tsx` | Single-page RF laboratory |
| State | `src/context/SignalContext.tsx` | Central store: stage, mode, metadata, all stage results |
| Live client | `src/lib/sigma-api.ts` | Typed HTTP client → `http://127.0.0.1:8000` (override with `NEXT_PUBLIC_SIGMA_API_URL`) |
| Sim client | `src/lib/dsp-mock.ts` | Client-side mock DSP — generates plausible spectra/constellations/bits |
| Types | `src/lib/dsp-types.ts` | Shared domain types |
| Visualizers | `src/components/visualizers/` | `InstrumentSpectrum`, `InstrumentConstellation`, `InstrumentWaterfall`, `Waterfall3D` |
| Workbench | `src/components/workbench/` | `LabWorkbench`, `IntelligenceWorkspace`, `ErrorControlLab`, `HammingDemo`, `SignalGeneratorPanel`, `BlockchainFingerprintWorkspace`, `PdfComparison` |
| Editorial | `src/components/hero/`, `sections/` | `EditorialHero`, `PipelineFlow`, `SpecSheet`, `IngestionModal` |

**The dual-engine design is the key idea.** The frontend runs in one of two modes:

- **SIMULATION** (default) — `dsp-mock.ts` fabricates spectra, constellations and
  bitstreams entirely in the browser. The UI is fully explorable with **no backend
  running at all**.
- **FASTAPI LIVE** — `sigma-api.ts` calls the real backend. `SignalContext` tracks
  `apiStatus: 'checking' | 'connected' | 'disconnected'` and falls back gracefully.

### 3.3 REST / WebSocket clients

Anything that speaks HTTP: `curl`, the `tests/` suite, or your own scripts.
`frontend/src/lib/sigma-api.ts` is itself the best reference client.

---

## 4. Layer 2 — API gateway (FastAPI)

Two interchangeable entry points:

| File | Behaviour |
|---|---|
| `api.py` | Inserts `src/` into `sys.path`, `from sigma_api import app`, `uvicorn.run(app, host="127.0.0.1", port=8000)` |
| `run_api.py` | Same, with argparse `--host` / `--port` / `--reload` |

`src/sigma_api.py` (1389 LOC) builds the app, defines the DSP routes, and mounts the
modular router from `src/backend/api_routes.py`. **CORS is enabled**, which is what lets
the Next.js dev server call the backend directly from the browser.

> PyTorch is deliberately **not** imported at startup — `sigma_api.py` probes with
> `importlib.util.find_spec` first, so boot stays fast even with torch installed.

### Route map

**Modular REST** (`src/backend/api_routes.py`) — signal registry and job tracking:

```
GET    /health
POST   /signals/upload            multipart ingest → registers in sigma.db
GET    /signals                   list
GET    /signals/{id}
POST   /analysis                  enqueue analysis job
GET    /analysis/{id}             job status (stage, progress, message)
GET    /analysis/{id}/results     finished result JSON
POST   /analysis/{id}/demodulate
GET    /signals/{id}/spectrum     live visualization payloads
GET    /signals/{id}/spectrogram
GET    /signals/{id}/constellation
GET    /reports/{id}
GET    /history
WS     /ws/analysis/{id}          real-time progress stream
```

**DSP routes** (direct in `sigma_api.py`) — the actual signal work:

```
POST /api/analyze_advanced   full guided pipeline (modulation, sync, demod, deint, FEC)
POST /api/modulate           generate a synthetic IQ signal from bits or text
POST /api/synchronize        carrier + clock + frame sync
POST /api/demodulate         IQ → hard/soft bits, with EVM
POST /api/deinterleave       undo block/convolutional/diagonal/pseudo-random
POST /api/fec_decode         Viterbi / Hamming decode

POST /analyze        POST /demodulate     POST /deinterleave
POST /fec/decode     POST /correlate      POST /recover        (short-form aliases)
```

**RAG routes:**

```
GET  /rag/health          is Gemini configured? how many docs embedded?
POST /rag/index-project   index docs/ + uploads/
POST /rag/knowledge       add a technical reference or analyst note
POST /rag/knowledge/upload  upload PDF / Markdown / text
POST /rag/ask             evidence-grounded RF analyst Q&A
```

Interactive docs: `http://127.0.0.1:8000/docs`.

---

## 5. Layer 3 — Application services

### 5.1 Measurement engine — `src/backend/analysis_engine.py` (40 LOC)

The **fast, always-succeeds** path. One function, `analyze(samples, sample_rate,
center_frequency)`:

- Blackman-windowed FFT → shifted spectrum
- `scipy.signal.stft` → spectrogram (time × frequency power matrix)
- Median power as noise floor → **SNR**
- 99 % **occupied bandwidth** from the power quantile
- Decimated IQ subsample → constellation

It explicitly reports `"classification": {"modulation": None, ...}` with the note
`"measurement-only; trained model unavailable"`. This is honest: there is no trained
classifier loaded on this path. It powers the web UI's spectrum/spectrogram/constellation
endpoints and drives job progress (`QUEUED → FFT_ANALYSIS → … → COMPLETED`).

### 5.2 Deep pipeline — `src/sigma_recovery.py` → `orchestrate_signal_recovery()`

The **real intelligence path**. Chains everything into one `SignalResult`:

```
.iq / .wav
   ↓ 1  preprocess          WAV→IQ, sample loading
   ↓ 2  identify            SNR, OBW, noise floor, peak freq, symbol rate
   ↓ 3  classify            BPSK / QPSK / 8PSK / 16QAM / FSK / AM-FM
   ↓ 4  synchronize         carrier offset, symbol timing phase
   ↓ 5  demodulate          decision slicing → symbols → bits + EVM
   ↓ 6  de-interleave       block / convolutional / diagonal / pseudo-random
   ↓ 7  FEC decode          Viterbi / RS / concatenated / LDPC
   ↓ 8  correlate           candidate headers & payload regions
   ↓
SignalResult
```

**Strict gating rules** (the defining characteristic of this codebase):

- No symbol-rate lock → demodulation **declined**, not sampled on an untrusted clock.
- Modulation unidentifiable → reports `UNKNOWN`, does not guess a decoder.
- FEC unidentifiable → reports `NOT DETECTED`, does not invent a payload.

### 5.3 RAG service — `src/sigma_rag.py` (400 LOC)

An evidence-grounded RF analyst that can explain results in plain language.

| Aspect | Detail |
|---|---|
| Embeddings | `gemini-embedding-001` |
| Generation | `gemini-3.8-flash` (fallback `gemini-3.5-flash-lite`) |
| Corpus | `docs/` (14 technical docs) + `uploads/` |
| Index | `data/sigma_rag.sqlite3` — documents, embeddings, `rag_settings` |
| Retrieval | `_chunk_markdown` → `_embed` → cosine similarity, top-k |
| Env | `GEMINI_API_KEY`, `SIGMA_RAG_DB` |

`ask()` returns `{ answer, evidence[], uncertainties[], recommended_analysis[],
retrieval }` — it surfaces **what it is unsure about**, which is rare and valuable.
It also stores per-analysis observations (`store_observation`) so past results become
future context.

---

## 6. Layer 4 — Signal processing core (`src/`)

Organized as **L1 / L2 / L3** (see [`L1_L2_L3_ARCHITECTURE.md`](L1_L2_L3_ARCHITECTURE.md)).

### L1 — Ingest

| Concern | File |
|---|---|
| IQ / WAV reading, format detection | `backend/signal_io.py` — `read_iq` handles `complex64`, `float32` interleaved, `int16` interleaved; `read_wav` maps stereo L→I, R→Q |
| Sidecar metadata | `backend/signal_io.py::_sidecar` — reads `*_telemetry.json` / `*_meta.json` next to the capture |
| Sample-rate provenance | `sigma_sample_rate.py` — resolves `f_s` from competing sources with an explicit ranking |
| Metadata object + WAV→IQ | `sigma_analyzer_core.py` — `SignalMetadata`, `load_and_convert_wav` |

### L2 — Analysis

| Concern | File |
|---|---|
| Symbol rate | `sigma_symbol_rate.py` — envelope cyclostationarity. Welch-averaged `nfft=16384`, sub-harmonic rejection, confidence `HIGH/MEDIUM/LOW` |
| PSK order | `sigma_analyzer_core.py` — compares 2nd- vs 4th-power carrier-line prominence |
| OBW / noise floor / SNR | `sigma_analyzer_core.py` |
| Modulation classification | `sigma_demod.py` (978 LOC) |
| Coding-layer analysis | `sigma_coding.py` (1026 LOC) — blind convolutional-code identification |

> Two measured findings are load-bearing here: **Welch averaging is mandatory** (a single
> FFT has ~100 % spectral variance, so a noise bin can outrank the real clock line), and
> **`nfft` must be large** — moving from 1024 → 16384 at 1 Msps took symbol-rate error
> from ±42 % to 0.00 %.

### L3 — Demodulation and recovery

| Subsystem | Files |
|---|---|
| Sync + demod | `recovery/synchronizer.py`, `recovery/demodulators.py`, `recovery/bit_mapper.py`, `recovery/recovery_pipeline.py` |
| De-interleaving | `deinterleaving/` — `block`, `convolutional`, `diagonal`, `pseudo_random`, `dispatcher` |
| FEC | `fec/` — `convolutional` (Viterbi), `reed_solomon`, `concatenated` (RS+Conv), `ldpc`, `dispatcher` |
| Correlation | `correlation/` — `alignment`, `bitstream`, `header_detection`, `payload_detection`, `scoring` |
| Export | `export/` — `csv_export`, `json_export`, `report_export` |

Carrier recovery uses the M-th power method (`x²` for BPSK, `x⁴` for QPSK/16QAM,
`x⁸` for 8PSK). Symbol timing picks the sampling phase that **tightens the constellation
cluster**, not the one with the largest envelope. Verified: **72/72 configurations
locked, 0 refused** — 100.00 % bit accuracy on BPSK/QPSK/8PSK, 99.98 % on 16QAM.

---

## 7. The data model — `src/models/signal_result.py`

Every path converges on one `SignalResult` dataclass:

```
SignalResult
├── input_metadata        file type, f_s, center freq, N samples, duration
├── signal_metrics        SNR, noise floor, power, symbol rate, SPS, lock label
├── classification        modulation + candidates + confidence evidence
├── recovery              demod status, sync status, EVM, offsets, symbols, bits
├── deinterleaving        status, mode, hypotheses, output bits
├── fec                   status, type, corrected errors, residual, decoded bits
├── correlation           status, alignment offset, candidate headers/payloads
└── overall_status
```

Serialization: `to_dict()` (NumPy-safe via `_to_serializable`), `to_json()`,
`summary()` (human-readable).

**The status vocabulary is the contract.** Legal values include `LOCKED`, `COARSE`,
`SUCCESS`, `SUPPORTED`, `MATCH FOUND`, `NOT DETECTED`, `DECLINED`,
`INSUFFICIENT DATA`, `DECODING FAILED`, `UNSUPPORTED`, `NOT RUN`, `UNKNOWN`.
Nothing is ever silently upgraded from a refusal to a guess.

---

## 8. Layer 5 — Data layer

| Store | Contents | Owner |
|---|---|---|
| `data/sigma.db` | `signals`, `analysis_jobs`, `analysis_results`, `reports` | `backend/db.py` |
| `data/sigma_rag.sqlite3` | documents, embeddings, `rag_settings` | `sigma_rag.py` |
| `data/iq/`, `data/wav/` | signal captures | — |
| `data/metadata/`, `data/test_vectors/`, `data/ml/` | sidecars, fixtures, model artifacts | — |
| `uploads/` | analyst-supplied PDF/Markdown/text | RAG |
| `docs/` | 14 technical documents — also the RAG corpus | — |

Two **separate** SQLite databases, deliberately: operational job state and the RAG
vector index have different lifecycles and should not contend.

---

## 9. Repository map

```
gnu/
├── run.py                    desktop launcher
├── run_api.py / api.py       backend launchers
├── sigma_iq_analyzer.py      desktop entry (delegates to src/)
├── src/
│   ├── sigma_api.py          FastAPI app + DSP routes       (1389)
│   ├── sigma_main_window.py  PyQt5 workstation UI           (1794)
│   ├── sigma_flowgraph.py    GNU Radio top_block + sinks
│   ├── sigma_theme.py        dark palette + QSS + icon
│   ├── sigma_analyzer_core.py metadata, metrics, PSK order
│   ├── sigma_symbol_rate.py  cyclostationary symbol rate
│   ├── sigma_sample_rate.py  f_s provenance
│   ├── sigma_demod.py        classification + demodulation   (978)
│   ├── sigma_coding.py       coding layer, blind code ID    (1026)
│   ├── sigma_recovery.py     orchestrate_signal_recovery()
│   ├── sigma_rag.py          Gemini RAG service
│   ├── backend/              api_routes, analysis_engine, db, signal_io, config
│   ├── recovery/             synchronizer, demodulators, bit_mapper, pipeline
│   ├── deinterleaving/       block, convolutional, diagonal, pseudo_random
│   ├── fec/                  convolutional, reed_solomon, concatenated, ldpc
│   ├── correlation/          alignment, header/payload detection, scoring
│   ├── models/               signal_result.py
│   └── export/               csv, json, report
├── frontend/                 SignalForge — Next.js 16
├── grc/                      SIGMA_IQ_Analyzer.grc
├── docs/                     14 technical documents (RAG corpus)
├── tests/                    8 test modules
├── data/                     iq, wav, metadata, ml, *.db
└── uploads/                  analyst documents
```

---

## 10. Running the whole thing

```bash
# 1. Backend  (Radioconda Python)
python run_api.py --reload          # → http://127.0.0.1:8000/docs

# 2. Web frontend
cd frontend && npm run dev          # → http://localhost:3000
#   optional: NEXT_PUBLIC_SIGMA_API_URL=http://127.0.0.1:8000

# 3. Desktop workstation
python run.py

# 4. RAG (needs a key)
export GEMINI_API_KEY=...
curl -X POST http://127.0.0.1:8000/rag/index-project
```

> **Runtime note:** the real runtime for the desktop app is **Radioconda Python**
> (`C:\Users\sahil\radioconda\python.exe`) — it is the only interpreter with PyQt5 and
> GNU Radio. The managed WorkBuddy Python cannot import the app's modules.

---

## 11. Design principles

1. **Measurement over assertion.** Every metric is computed from the samples. Anything
   not computed renders as `--`, never as a plausible default.
2. **Refusal over fabrication.** A stage that cannot be trusted *declines with a measured
   reason*. A wrong number is more damaging than an honest "I don't know".
3. **The frontend must work alone.** The SIMULATION engine means no backend is required
   to explore the UI.
4. **Layer discipline.** L1 never guesses `f_s`; L3 never samples on an untrusted clock;
   the classifier never overrides a measurement.
5. **Two databases, two lifecycles.** Operational state and the RAG index stay separate.

---

## 12. Known gaps (honest status)

| Gap | Detail |
|---|---|
| No trained classifier | `analysis_engine.py` returns `modulation: None`. The CNN interface contract is defined in `CNN_INPUT_AND_TRAINING.md` but **no model is trained or loaded**. |
| AM/FM | Mentioned in the `sigma_recovery.py` docstring but not wired as a real classifier path. |
| Turbo codes | Not implemented — only convolutional, RS, concatenated, LDPC, Hamming. |
| Adaptive equalizer | No CMA / LMS / decision-directed equalizer, so ISI-heavy channels are not recoverable. |
| OFDM / MIMO / spread-spectrum | Not implemented at all. |

See [`FEATURE_STATUS_BY_LEVEL.md`](FEATURE_STATUS_BY_LEVEL.md) for the full
curriculum-mapped breakdown.
