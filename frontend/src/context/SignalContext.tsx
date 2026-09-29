'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  PipelineStage,
  SystemMode,
  SignalMetadata,
  SpectralAnalysisResult,
  ConstellationPoint,
  WaterfallFrame,
  DemodulationResult,
  DeinterleaveResult,
  FecResult,
  CorrelationResult,
  ModulationType,
  DeinterleaveMethod,
  FecCodeType,
  PresetSignalOption,
} from '../lib/dsp-types';
import {
  PRESET_SIGNALS,
  generateMockSpectrum,
  generateMockConstellation,
  generateMockWaterfall,
  generateMockDemod,
  generateMockDeinterleave,
  generateMockFec,
  generateMockCorrelation,
} from '../lib/dsp-mock';
import { analyzeRawIq, recoverSignal, uploadSignal, getAnalysis, fetchSpectrum, fetchConstellation, fetchSpectrogram, SigmaAdvancedResult, SigmaRecoveryResult } from '../lib/sigma-api';

interface SignalContextType {
  apiStatus: 'checking' | 'connected' | 'disconnected';
  // Navigation & System
  stage: PipelineStage;
  setStage: (stage: PipelineStage) => void;
  mode: SystemMode;
  setMode: (mode: SystemMode) => void;

  // Signal Ingestion
  metadata: SignalMetadata | null;
  presets: PresetSignalOption[];
  loadPreset: (presetId: string) => void;
  uploadCustomSignal: (file: File, sampleRateHz?: number, centerFreqHz?: number) => Promise<void>;
  uploadedFile: File | null;
  apiResult: SigmaRecoveryResult | null;
  apiPlots: SigmaAdvancedResult['gui_plots'] | null;
  apiBusy: boolean;
  apiError: string | null;

  // Analysis State
  spectralData: SpectralAnalysisResult | null;
  waterfallFrames: WaterfallFrame[];
  constellationPoints: ConstellationPoint[];
  isAnalyzing: boolean;
  runSpectralAnalysis: () => Promise<void>;

  // Demodulation State
  demodData: DemodulationResult | null;
  isDemodulating: boolean;
  selectedModulation: ModulationType;
  setSelectedModulation: (mod: ModulationType) => void;
  runDemodulation: (mod?: ModulationType) => Promise<void>;

  // De-interleaving State
  deinterleaveData: DeinterleaveResult | null;
  isDeinterleaving: boolean;
  selectedDeintMethod: DeinterleaveMethod;
  setSelectedDeintMethod: (m: DeinterleaveMethod) => void;
  deintRows: number;
  setDeintRows: (r: number) => void;
  deintCols: number;
  setDeintCols: (c: number) => void;
  runDeinterleave: (method?: DeinterleaveMethod, rows?: number, cols?: number) => Promise<void>;

  // FEC State
  fecData: FecResult | null;
  isDecoding: boolean;
  selectedFecCode: FecCodeType;
  setSelectedFecCode: (c: FecCodeType) => void;
  runFec: (code?: FecCodeType) => Promise<void>;

  // Correlation State
  correlationData: CorrelationResult | null;
  isCorrelating: boolean;
  runCorrelation: () => Promise<void>;

  // Automation
  runFullPipeline: () => Promise<void>;
  resetPipeline: () => void;
}

const SignalContext = createContext<SignalContextType | undefined>(undefined);

export function SignalProvider({ children }: { children: ReactNode }) {
  const apiBase = (process.env.NEXT_PUBLIC_SIGMA_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const wsBase = (process.env.NEXT_PUBLIC_SIGMA_WS_URL || apiBase.replace(/^http/, 'ws')).replace(/\/$/, '');
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  // Navigation
  const [stage, setStage] = useState<PipelineStage>('spectral');
  const [mode, setMode] = useState<SystemMode>('simulation');

  // Metadata
  const [metadata, setMetadata] = useState<SignalMetadata | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [apiResult, setApiResult] = useState<SigmaRecoveryResult | null>(null);
  const [apiPlots, setApiPlots] = useState<SigmaAdvancedResult['gui_plots'] | null>(null);
  const [apiBusy, setApiBusy] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Spectral & Visualizer
  const [spectralData, setSpectralData] = useState<SpectralAnalysisResult | null>(null);
  const [waterfallFrames, setWaterfallFrames] = useState<WaterfallFrame[]>([]);
  const [constellationPoints, setConstellationPoints] = useState<ConstellationPoint[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [backendSignalId, setBackendSignalId] = useState<string | null>(null);
  const [backendAnalysisId, setBackendAnalysisId] = useState<string | null>(null);

  // Demod
  const [demodData, setDemodData] = useState<DemodulationResult | null>(null);
  const [isDemodulating, setIsDemodulating] = useState(false);
  const [selectedModulation, setSelectedModulation] = useState<ModulationType>('QPSK');

  // De-interleave
  const [deinterleaveData, setDeinterleaveData] = useState<DeinterleaveResult | null>(null);
  const [isDeinterleaving, setIsDeinterleaving] = useState(false);
  const [selectedDeintMethod, setSelectedDeintMethod] = useState<DeinterleaveMethod>('block');
  const [deintRows, setDeintRows] = useState<number>(16);
  const [deintCols, setDeintCols] = useState<number>(32);

  // FEC
  const [fecData, setFecData] = useState<FecResult | null>(null);
  const [isDecoding, setIsDecoding] = useState(false);
  const [selectedFecCode, setSelectedFecCode] = useState<FecCodeType>('viterbi');

  // Correlation
  const [correlationData, setCorrelationData] = useState<CorrelationResult | null>(null);
  const [isCorrelating, setIsCorrelating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const checkApi = async () => {
      try {
        const response = await fetch(`${apiBase}/api/health`, { signal: AbortSignal.timeout(2500) });
        if (!response.ok) throw new Error('API health check failed');
        if (!cancelled) setApiStatus('connected');
      } catch {
        if (!cancelled) setApiStatus('disconnected');
      }
    };
    void checkApi();
    return () => { cancelled = true; };
  }, [apiBase]);

  // Auto-load default preset on first launch
  useEffect(() => {
    const timer = window.setTimeout(() => loadPreset('cubesat_qpsk_433'), 0);
    return () => window.clearTimeout(timer);
  }, []);
  const loadPreset = (presetId: string) => {
    const preset = PRESET_SIGNALS.find((p) => p.id === presetId) || PRESET_SIGNALS[0];
    const newMeta: SignalMetadata = {
      id: preset.id,
      name: `${preset.name} (${preset.format})`,
      format: preset.format,
      sizeBytes: preset.sizeBytes,
      sampleRateHz: preset.sampleRateHz,
      centerFreqHz: preset.centerFreqHz,
      durationSeconds: preset.durationSeconds,
      totalSamples: Math.floor(preset.sampleRateHz * preset.durationSeconds),
      isPreset: true,
      presetDescription: preset.description,
    };
    setMetadata(newMeta);
    setUploadedFile(null);
    setApiResult(null);
    setApiPlots(null);
    setApiError(null);
    setSelectedModulation(preset.defaultModulation);

    // Populate initial spectral preview
    const centerMhz = preset.centerFreqHz / 1e6;
    const spec = generateMockSpectrum(centerMhz, preset.bandwidthMhz, preset.snrDb);
    const constPts = generateMockConstellation(preset.defaultModulation, 500, preset.snrDb);
    const wf = generateMockWaterfall(48, 128);

    setSpectralData(spec);
    setConstellationPoints(constPts);
    setWaterfallFrames(wf);

    // Reset downstream stages
    setDemodData(null);
    setDeinterleaveData(null);
    setFecData(null);
    setCorrelationData(null);
  };

  const uploadCustomSignal = async (file: File, sampleRateHz?: number, centerFreqHz?: number) => {
    const lowerName = file.name.toLowerCase();
    const ext = lowerName.endsWith('.wav') ? '.wav' : lowerName.endsWith('.bin') ? '.bin' : '.iq';
    const resolvedRate = sampleRateHz || 0;
    setBackendSignalId(null);
    setBackendAnalysisId(null);
    setUploadedFile(file);
    setApiResult(null);
    setApiPlots(null);
    setApiError(null);
    setMetadata({
      id: `upload-${Date.now()}`, name: file.name, format: ext,
      sizeBytes: file.size, sampleRateHz: resolvedRate,
      centerFreqHz: centerFreqHz || 0, durationSeconds: resolvedRate ? file.size / (ext === '.wav' ? 2 : 8) / resolvedRate : 0,
      totalSamples: Math.floor(file.size / (ext === '.wav' ? 2 : 8)), isPreset: false,
    });
    setSpectralData(null);
    setConstellationPoints([]);
    setWaterfallFrames([]);

    setDemodData(null);
    setDeinterleaveData(null);
    setFecData(null);
    setCorrelationData(null);

    // Register the capture with the backend. Without this the signal id stays
    // null and the queued-analysis path below can never run. IQ format is not
    // guessed: the server rejects raw IQ that declares no encoding.
    try {
      const iqFormat = ext === '.iq' ? (file.name.toLowerCase().includes('int16') || file.name.toLowerCase().includes('sc16') ? 'int16' : 'complex64') : undefined;
      const uploaded = await uploadSignal(file, { sampleRate: resolvedRate || undefined, iqFormat });
      setBackendSignalId(uploaded.signal_id);
      setMetadata((current) => current ? {
        ...current,
        sampleRateHz: Number(uploaded.metadata?.sample_rate) || current.sampleRateHz,
        totalSamples: Number(uploaded.metadata?.num_samples) || current.totalSamples,
        durationSeconds: Number(uploaded.metadata?.duration) || current.durationSeconds,
      } : current);
    } catch (error) {
      setBackendSignalId(null);
      setApiError(error instanceof Error ? error.message : 'Upload failed');
    }
  };

  const runSpectralAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      if (uploadedFile && metadata) {
        setApiBusy(true);
        setApiError(null);
        try {
          const recovered = await recoverSignal(uploadedFile, { sampleRate: metadata.sampleRateHz || 1000000, centerFrequency: metadata.centerFreqHz || 0 });
          setApiResult(recovered);
          setApiPlots(null);
          const input = recovered.input_metadata;
          if (input) setMetadata((current) => current ? {
            ...current,
            sampleRateHz: input.sample_rate || current.sampleRateHz,
            centerFreqHz: input.center_frequency ?? current.centerFreqHz,
            durationSeconds: input.duration_seconds || current.durationSeconds,
            totalSamples: input.num_samples || current.totalSamples,
          } : current);
        } catch (error) {
          setApiError(error instanceof Error ? error.message : 'Signal analysis failed');
          throw error;
        } finally {
          setApiBusy(false);
        }
        return;
      }
      if (!backendSignalId || !metadata) throw new Error('Upload a signal file before starting analysis.');
      const create = await fetch(`${apiBase}/api/analysis`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal_id: backendSignalId, sample_rate: metadata.sampleRateHz || undefined, center_frequency: metadata.centerFreqHz || undefined, iq_format: metadata.format === '.iq' ? 'complex64' : undefined }),
      });
      const created = await create.json();
      if (!create.ok || !created.success) throw new Error(created?.error?.message || created?.detail?.error?.message || 'Analysis could not be queued');
      const analysisId = created.data.analysis_id;
      setBackendAnalysisId(analysisId);
      let result: any = null;
      let socket: WebSocket | null = null;
      let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
      let reconnects = 0;
      const closeSocket = () => {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        socket?.close();
        socket = null;
      };
      const connectProgress = () => {
        if (typeof WebSocket === 'undefined' || reconnects >= 5) return;
        try {
          socket = new WebSocket(`${wsBase}/ws/analysis/${analysisId}`);
          socket.onopen = () => { reconnects = 0; };
          socket.onmessage = (event) => {
            try {
              const update = JSON.parse(event.data);
              if (update.status === 'FAILED') closeSocket();
            } catch { /* status polling remains the source of truth */ }
          };
          socket.onerror = () => socket?.close();
          socket.onclose = () => {
            if (!result && reconnects < 5) {
              reconnects += 1;
              reconnectTimer = setTimeout(connectProgress, Math.min(5000, 500 * 2 ** reconnects));
            }
          };
        } catch {
          reconnects += 1;
        }
      };
      connectProgress();
      // Poll the slim status endpoint. Previously this loop ignored non-OK
      // responses and missing jobs, so a 404 or a FAILED job kept it busy for
      // the full 60 attempts (~5 minutes with large payloads).
      const pollStarted = Date.now();
      const pollLimitMs = 90_000;
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (Date.now() - pollStarted > pollLimitMs) break;
        const status = await fetch(`${apiBase}/api/analysis/${analysisId}`);
        if (status.status === 404) throw new Error('Analysis was not found on the server.');
        const body = await status.json().catch(() => null);
        const job = body?.data?.job;
        if (!job) {
          if (!status.ok) throw new Error(`Analysis status check failed (HTTP ${status.status})`);
          continue;
        }
        if (job.status === 'FAILED') throw new Error(job.error || 'Signal analysis failed');
        if (body.data?.result) { result = body.data.result; break; }
        if (job.status === 'COMPLETED') break;
      }
      closeSocket();
      if (!result) throw new Error('Analysis timed out');

      const spectrum = result.spectrum ?? {};
      const constellation = result.constellation ?? {};
      const spectrogram = result.spectrogram ?? {};

      setApiResult({
        input_metadata: {
          filename: metadata?.name,
          file_type: metadata?.format,
          sample_rate: metadata?.sampleRateHz,
          center_frequency: metadata?.centerFreqHz,
          duration_seconds: result.duration,
          num_samples: result.num_samples,
        },
        signal_metrics: {
          // The analysis engine measures occupied bandwidth, not symbol rate.
          // Labelling bandwidth as symbol rate produced a plausible wrong
          // number, so report the measured quantity under its own name.
          snr_str: Number.isFinite(result.snr) ? `${Number(result.snr).toFixed(1)} dB` : 'Not available',
          symbol_rate_str: 'Not measured by this endpoint',
          symbol_rate_lock: Number.isFinite(result.bandwidth) ? `Occupied bandwidth ${(result.bandwidth / 1e3).toFixed(1)} kHz` : 'Not available',
        },
        classification: {
          modulation: result.classification?.modulation || 'Unclassified',
          confidence_evidence: result.classification?.confidence ?? result.classification?.mode ?? 'Not available',
        },
        recovery: {
          demodulation_status: result.processing_status || 'Completed',
          n_symbols: undefined,
          bits: [],
          diagnostics: {
            carrier_frequency_hz: result.carrier_frequency,
            peak_frequency_hz: result.peak_frequency,
            occupied_bandwidth_hz: result.bandwidth,
          },
        },
        overall_status: result.processing_status || 'Completed',
      });

      // Pull plot series from their dedicated endpoints. They are deliberately
      // excluded from the polled result payload to keep status checks small.
      const signalIdForPlots = backendSignalId;
      if (signalIdForPlots) {
        try {
          const [spec, constel] = await Promise.all([
            fetchSpectrum(signalIdForPlots),
            fetchConstellation(signalIdForPlots),
          ]);
          setApiPlots({
            spectrum_db: Array.isArray(spec.power) ? spec.power : [],
            frequencies_norm: Array.isArray(spec.frequencies) ? spec.frequencies : [],
            constellation_i: Array.isArray(constel.i) ? constel.i : [],
            constellation_q: Array.isArray(constel.q) ? constel.q : [],
            snr_db: typeof result.snr === 'number' ? result.snr : undefined,
            rms_power_dbfs: typeof result.signal_power === 'number' ? result.signal_power : undefined,
          });
        } catch {
          // Plot retrieval is best-effort; measured metrics above stand alone.
          setApiPlots(null);
        }
      }

      setSpectralData({
        frequencies: Array.isArray(spectrum.frequencies) ? spectrum.frequencies.map((f: number) => (f + (result.center_frequency || 0)) / 1e6) : [],
        powerDbfs: Array.isArray(spectrum.power) ? spectrum.power : [],
        peakFreqMhz: (result.peak_frequency || 0) / 1e6,
        estimatedCarrierMhz: result.carrier_frequency ? result.carrier_frequency / 1e6 : 0,
        bandwidthMhz: (result.bandwidth || 0) / 1e6,
        snrDb: typeof result.snr === 'number' ? result.snr : 0,
        noiseFloorDbfs: result.noise_power,
        estimatedModulation: result.classification?.modulation || 'QPSK',
        confidence: result.classification?.confidence || 0,
        rolloffFactor: 0,
      });
      setConstellationPoints(Array.isArray(constellation.i) ? constellation.i.map((i: number, index: number) => ({ i, q: constellation.q[index] })) : []);
      const matrix = Array.isArray(spectrogram.power) ? spectrogram.power : [];
      setWaterfallFrames(matrix[0]?.map((_: number, index: number) => ({ timestamp: spectrogram.time?.[index] || index, bins: matrix.map((row: number[]) => row[index] || -120) })) || []);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const runDemodulation = async (mod?: ModulationType) => {
    if (uploadedFile) return;
    const targetMod = mod || selectedModulation;
    setIsDemodulating(true);
    await new Promise((r) => setTimeout(r, 700));
    const result = generateMockDemod(targetMod);
    setDemodData(result);
    setConstellationPoints(result.constellationPoints);
    setIsDemodulating(false);
  };

  const runDeinterleave = async (method?: DeinterleaveMethod, rows?: number, cols?: number) => {
    if (uploadedFile) return;
    const targetMethod = method || selectedDeintMethod;
    const targetRows = rows || deintRows;
    const targetCols = cols || deintCols;
    const rawBits = demodData?.rawBits || '10101100110100101100101010101010';

    setIsDeinterleaving(true);
    await new Promise((r) => setTimeout(r, 500));
    const result = generateMockDeinterleave(rawBits, targetMethod, targetRows, targetCols);
    setDeinterleaveData(result);
    setIsDeinterleaving(false);
  };

  const runFec = async (code?: FecCodeType) => {
    if (uploadedFile) return;
    const targetCode = code || selectedFecCode;
    const bits = deinterleaveData?.afterBits || demodData?.rawBits || '1010110011010010';

    setIsDecoding(true);
    await new Promise((r) => setTimeout(r, 600));
    const result = generateMockFec(bits, targetCode);
    setFecData(result);
    setIsDecoding(false);
  };

  const runCorrelation = async () => {
    if (uploadedFile) return;
    const bits = fecData?.outputBits || deinterleaveData?.afterBits || demodData?.rawBits || '1010110011010010';

    setIsCorrelating(true);
    await new Promise((r) => setTimeout(r, 500));
    const result = generateMockCorrelation(bits);
    setCorrelationData(result);
    setIsCorrelating(false);
  };

  const runFullPipeline = async () => {
    await runSpectralAnalysis();
    if (uploadedFile) {
      setStage('spectral');
      return;
    }
    await runDemodulation();
    await runDeinterleave();
    await runFec();
    await runCorrelation();
    setStage('report');
  };

  const resetPipeline = () => {
    setDemodData(null);
    setDeinterleaveData(null);
    setFecData(null);
    setCorrelationData(null);
    setStage('spectral');
  };

  return (
    <SignalContext.Provider
      value={{
        apiStatus,
        stage,
        setStage,
        mode,
        setMode,
        metadata,
        presets: PRESET_SIGNALS,
        loadPreset,
        uploadCustomSignal,
        uploadedFile,
        apiResult,
        apiPlots,
        apiBusy,
        apiError,
        spectralData,
        waterfallFrames,
        constellationPoints,
        isAnalyzing,
        runSpectralAnalysis,
        demodData,
        isDemodulating,
        selectedModulation,
        setSelectedModulation,
        runDemodulation,
        deinterleaveData,
        isDeinterleaving,
        selectedDeintMethod,
        setSelectedDeintMethod,
        deintRows,
        setDeintRows,
        deintCols,
        setDeintCols,
        runDeinterleave,
        fecData,
        isDecoding,
        selectedFecCode,
        setSelectedFecCode,
        runFec,
        correlationData,
        isCorrelating,
        runCorrelation,
        runFullPipeline,
        resetPipeline,
      }}
    >
      {children}
    </SignalContext.Provider>
  );
}

export function useSignal() {
  const context = useContext(SignalContext);
  if (!context) {
    throw new Error('useSignal must be used within a SignalProvider');
  }
  return context;
}
