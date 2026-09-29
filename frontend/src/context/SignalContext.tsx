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
  uploadCustomSignal: (file: File, sampleRateHz?: number) => Promise<void>;

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
    loadPreset('cubesat_qpsk_433');
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

  const uploadCustomSignal = async (file: File, sampleRateHz?: number) => {
    const form = new FormData();
    form.append('file', file);
    if (file.name.toLowerCase().endsWith('.iq')) {
      form.append('iq_format', 'complex64');
      if (sampleRateHz && sampleRateHz > 0) form.append('sample_rate', String(sampleRateHz));
    }
    const response = await fetch(`${apiBase}/api/signals/upload`, { method: 'POST', body: form });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload?.error?.message || payload?.detail?.error?.message || 'Signal upload failed');
    const uploaded = payload.data;
    const info = uploaded.metadata;
    const ext = file.name.toLowerCase().endsWith('.wav') ? '.wav' : '.iq';
    setBackendSignalId(uploaded.signal_id);
    setBackendAnalysisId(null);
    setMetadata({
      id: uploaded.signal_id, name: uploaded.filename, format: ext,
      sizeBytes: file.size, sampleRateHz: info.sample_rate || 0,
      centerFreqHz: info.center_frequency || 0, durationSeconds: info.duration || 0,
      totalSamples: info.num_samples || 0, isPreset: false,
    });
    setSpectralData(null);
    setConstellationPoints([]);
    setWaterfallFrames([]);

    setDemodData(null);
    setDeinterleaveData(null);
    setFecData(null);
    setCorrelationData(null);
  };

  const runSpectralAnalysis = async () => {
    setIsAnalyzing(true);
    try {
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
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        const status = await fetch(`${apiBase}/api/analysis/${analysisId}`);
        const body = await status.json();
        if (body.data?.job?.status === 'FAILED') throw new Error(body.data.job.error || 'Signal analysis failed');
        if (body.data?.result) { result = body.data.result; break; }
      }
      closeSocket();
      if (!result) throw new Error('Analysis timed out');
      const spectrum = result.spectrum;
      setSpectralData({
        frequencies: spectrum.frequencies.map((f: number) => (f + (result.center_frequency || 0)) / 1e6),
        powerDbfs: spectrum.power, peakFreqMhz: (result.peak_frequency || 0) / 1e6,
        estimatedCarrierMhz: result.carrier_frequency ? result.carrier_frequency / 1e6 : 0,
        bandwidthMhz: (result.bandwidth || 0) / 1e6, snrDb: result.snr,
        noiseFloorDbfs: result.noise_power, estimatedModulation: result.classification.modulation || 'QPSK', confidence: result.classification.confidence || 0, rolloffFactor: 0,
      });
      setConstellationPoints(result.constellation.i.map((i: number, index: number) => ({ i, q: result.constellation.q[index] })));
      const matrix = result.spectrogram.power;
      setWaterfallFrames(matrix[0]?.map((_: number, index: number) => ({ timestamp: result.spectrogram.time[index] || index, bins: matrix.map((row: number[]) => row[index] || -120) })) || []);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const runDemodulation = async (mod?: ModulationType) => {
    const targetMod = mod || selectedModulation;
    setIsDemodulating(true);
    await new Promise((r) => setTimeout(r, 700));
    const result = generateMockDemod(targetMod);
    setDemodData(result);
    setConstellationPoints(result.constellationPoints);
    setIsDemodulating(false);
  };

  const runDeinterleave = async (method?: DeinterleaveMethod, rows?: number, cols?: number) => {
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
    const targetCode = code || selectedFecCode;
    const bits = deinterleaveData?.afterBits || demodData?.rawBits || '1010110011010010';

    setIsDecoding(true);
    await new Promise((r) => setTimeout(r, 600));
    const result = generateMockFec(bits, targetCode);
    setFecData(result);
    setIsDecoding(false);
  };

  const runCorrelation = async () => {
    const bits = fecData?.outputBits || deinterleaveData?.afterBits || demodData?.rawBits || '1010110011010010';

    setIsCorrelating(true);
    await new Promise((r) => setTimeout(r, 500));
    const result = generateMockCorrelation(bits);
    setCorrelationData(result);
    setIsCorrelating(false);
  };

  const runFullPipeline = async () => {
    await runSpectralAnalysis();
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
        stage,
        setStage,
        mode,
        setMode,
        metadata,
        presets: PRESET_SIGNALS,
        loadPreset,
        uploadCustomSignal,
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

