export interface SigmaRecoveryResult {
  analysis_id?: string;
  input_metadata?: {
    filename?: string;
    file_type?: string;
    sample_rate?: number;
    center_frequency?: number;
    duration_seconds?: number;
    num_samples?: number;
  };
  signal_metrics?: {
    snr_str?: string;
    symbol_rate_str?: string;
    symbol_rate_lock?: string;
  };
  classification?: {
    modulation?: string;
    confidence_evidence?: string;
  };
  recovery?: {
    demodulation_status?: string;
    n_symbols?: number;
    bits?: number[];
    diagnostics?: Record<string, unknown>;
  };
  deinterleaving?: { status?: string; mode?: string };
  fec?: { status?: string; fec_type?: string; corrected_errors?: number; output_bits?: number[] };
  correlation?: { status?: string; candidate_headers?: unknown[]; best_match?: Record<string, unknown> };
  overall_status?: string;
}

export interface SigmaPlotData {
  spectrum_db?: number[];
  frequencies_norm?: number[];
  constellation_i?: number[];
  constellation_q?: number[];
  waterfall_db?: number[][];
  snr_db?: number;
  rms_power_dbfs?: number;
}

export interface SigmaAdvancedResult {
  status?: string;
  extracted_parameters?: Record<string, string | number>;
  gui_plots?: SigmaPlotData;
  bitstream_extraction?: Record<string, unknown>;
}

const apiBase = (process.env.NEXT_PUBLIC_SIGMA_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export interface SigmaRAGEvidence {
  id: string;
  source: string;
  title: string;
  kind: string;
  score: number;
  content: string;
}

export interface SigmaRAGAnswer {
  answer: string;
  evidence: SigmaRAGEvidence[];
  uncertainties: string[];
  recommended_analysis: string[];
  retrieval: { strategy: string; candidate_count?: number; generation_model?: string; embedding_model?: string };
}

export async function askSigmaRAG(query: string, signalObject?: SigmaRecoveryResult | null) {
  const response = await fetch(`${apiBase}/rag/ask`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, signal_object: signalObject ?? null, limit: 6 }),
  });
  return readResponse<SigmaRAGAnswer>(response);
}

export async function getSigmaRAGHealth(signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/rag/health`, { signal, cache: 'no-store' });
  return readResponse<{ configured: boolean; documents: number; embedded_documents: number; knowledge_by_type: Record<string, number>; generation_model: string; embedding_model: string }>(response);
}

async function readResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : `Analysis service returned ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

export async function checkSigmaHealth(signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/health`, { signal, cache: 'no-store' });
  return readResponse<{ status: string }>(response);
}

export async function recoverSignal(file: File, settings: { sampleRate: number; centerFrequency: number; modulation?: string }) {
  const form = new FormData();
  form.set('file', file, file.name);
  form.set('sample_rate', String(settings.sampleRate));
  form.set('center_freq', String(settings.centerFrequency));
  if (settings.modulation) form.set('modulation', settings.modulation);
  const response = await fetch(`${apiBase}/recover`, { method: 'POST', body: form });
  return readResponse<SigmaRecoveryResult>(response);
}

export interface UploadedSignal {
  signal_id: string;
  filename: string;
  file_type: string;
  status: string;
  requires_metadata: boolean;
  metadata: Record<string, unknown>;
}

/**
 * Registers a capture with the backend so it can be queued for analysis.
 * Raw IQ is not self-describing, so sample_rate and iq_format are required and
 * are validated server-side.
 */
export async function uploadSignal(
  file: File,
  settings: { sampleRate?: number; iqFormat?: string } = {},
) {
  const form = new FormData();
  form.set('file', file, file.name);
  if (settings.sampleRate) form.set('sample_rate', String(settings.sampleRate));
  if (settings.iqFormat) form.set('iq_format', settings.iqFormat);
  const response = await fetch(`${apiBase}/api/signals/upload`, { method: 'POST', body: form });
  const body = await readResponse<{ success: boolean; data: UploadedSignal }>(response);
  return body.data;
}

export interface AnalysisProbe {
  job?: { status?: string; progress?: number; stage?: string; message?: string; error?: string };
  result?: Record<string, unknown> | null;
}

/**
 * Slim status/result probe. Large plot series are stripped by the API, which
 * keeps this poll cheap even against megabyte-sized results.
 */
export async function getAnalysis(analysisId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/api/analysis/${analysisId}`, { signal, cache: 'no-store' });
  const body = await readResponse<{ success: boolean; data: AnalysisProbe }>(response);
  return body.data;
}

export async function fetchSpectrum(signalId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/api/signals/${signalId}/spectrum`, { signal, cache: 'no-store' });
  const body = await readResponse<{ success: boolean; data: { frequencies: number[]; power: number[]; unit: string } }>(response);
  return body.data;
}

export async function fetchConstellation(signalId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/api/signals/${signalId}/constellation`, { signal, cache: 'no-store' });
  const body = await readResponse<{ success: boolean; data: { i: number[]; q: number[]; samples: number } }>(response);
  return body.data;
}

export async function fetchSpectrogram(signalId: string, signal?: AbortSignal) {
  const response = await fetch(`${apiBase}/api/signals/${signalId}/spectrogram`, { signal, cache: 'no-store' });
  const body = await readResponse<{ success: boolean; data: { time: number[]; frequencies: number[]; power: number[][]; unit: string } }>(response);
  return body.data;
}

export async function analyzeRawIq(file: File, settings: { sampleRate: number; modulation?: string }) {
  const form = new FormData();
  form.set('file', file, file.name);
  form.set('samp_rate', String(settings.sampleRate));
  if (settings.modulation) form.set('modulation', settings.modulation);
  const response = await fetch(`${apiBase}/api/analyze_advanced`, { method: 'POST', body: form });
  return readResponse<SigmaAdvancedResult>(response);
}

export async function generateSignal(settings: {
  modulation: string; sps: number; snr_db: number; cfo_hz: number;
  phase_offset_deg: number; samp_rate: number; num_samples: number;
}) {
  const response = await fetch(`${apiBase}/api/modulate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings),
  });
  return readResponse<{ samples_i: number[]; samples_q: number[]; total_bits: number; total_samples: number }>(response);
}
