# SIGMA RAG backend

SIGMA RAG is an evidence and explanation layer after DSP/recovery. It never reads raw IQ/WAV samples, changes DSP outputs, or makes a classifier decision. `/recover` stores a structured signal observation in a local SQLite index; the raw capture stays in the existing upload path. RF reference Markdown/PDF/text can be indexed separately.

## Setup

1. Install the RAG dependencies in the same Python environment used to run the SIGMA API:

   ```powershell
   python -m pip install -r requirements-rag.txt
   ```

2. Create a Google AI Studio Gemini API key. Copy `.env.example` to `.env`, add the key as `GEMINI_API_KEY`, and optionally set `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, and `GEMINI_EMBEDDING_MODEL`. Defaults are `gemini-3.8-flash` with `gemini-3.5-flash-lite` as the transient-load fallback, and `gemini-embedding-001`. The key is loaded by the backend only and is not read by or sent from the browser. `.env` is ignored by Git.

   ```powershell
   python run_api.py
   ```

3. Open the AI analyst view and ask a question. The first question indexes the core signal-processing, ML, and architecture references and computes their embeddings. The index is persisted at `data/sigma_rag.sqlite3` by default. `SIGMA_RAG_DB` can point to a different location.

## API

- `GET /rag/health` — key configuration, indexed/embedded counts, and selected model names (never the key).
- `POST /rag/ask` — `{ "query": "...", "signal_object": <optional /recover response>, "limit": 6 }`; returns a grounded answer, source excerpts, uncertainty notes, and retrieval details.
- `POST /rag/index-project` — indexes selected files in `docs/` for retrieval.
- `POST /rag/knowledge/upload` — multipart PDF, Markdown, or plain-text ingestion (`kind=technical_reference` or `analyst_note`, max 10 MB). Text-based PDFs are supported; scanned PDFs require OCR before ingestion.
- `POST /rag/knowledge` — ingest a text reference or analyst note as JSON.

Retrieval combines Gemini semantic embeddings with exact-token overlap for technical strings. Retrieved passages are given to Gemini with an untrusted-evidence instruction and a strict JSON response schema. Citations are accepted only when they reference an item in the retrieved set; an uncited generated answer is withheld. Technical sources explain RF concepts, while only DSP/recovery observations are authoritative for the current recording.

Gemini receives the analyst’s question, indexed reference passages, and the structured measurements needed for the answer. Raw IQ/WAV samples are not sent to Gemini by this RAG service. Use an approved Gemini deployment and data policy appropriate for the recordings and references being analyzed.
