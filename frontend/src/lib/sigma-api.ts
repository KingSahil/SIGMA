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
  phase_offset_deg: number; samp_rate: number;
}) {
  const response = await fetch(`${apiBase}/api/modulate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings),
  });
  return readResponse<{ samples_i: number[]; samples_q: number[]; total_bits: number; total_samples: number }>(response);
}
