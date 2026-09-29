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
  // Navigation & System
  stage: PipelineStage;
  setStage: (stage: PipelineStage) => void;
  mode: SystemMode;
  setMode: (mode: SystemMode) => void;

  // Signal Ingestion
  metadata: SignalMetadata | null;
  presets: PresetSignalOption[];
  loadPreset: (presetId: string) => void;
  uploadCustomSignal: (file: File) => void;

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

  const uploadCustomSignal = (file: File) => {
    const ext = file.name.endsWith('.wav') ? '.wav' : file.name.endsWith('.bin') ? '.bin' : '.iq';
    const sampleRate = ext === '.wav' ? 1200000 : 2400000;
    const centerFreq = 433920000;
    const duration = Number((file.size / (sampleRate * 4)).toFixed(2)) || 2.5;

    const newMeta: SignalMetadata = {
      id: `custom_${Date.now()}`,
      name: file.name,
      format: ext,
      sizeBytes: file.size,
      sampleRateHz: sampleRate,
      centerFreqHz: centerFreq,
      durationSeconds: duration,
      totalSamples: Math.floor(sampleRate * duration),
      isPreset: false,
    };

    setMetadata(newMeta);

    // Initial mock analysis for custom file
    const spec = generateMockSpectrum(centerFreq / 1e6, 1.8, 18.0);
    const constPts = generateMockConstellation('QPSK', 500, 18.0);
    const wf = generateMockWaterfall(48, 128);

    setSpectralData(spec);
    setConstellationPoints(constPts);
    setWaterfallFrames(wf);

    setDemodData(null);
    setDeinterleaveData(null);
    setFecData(null);
    setCorrelationData(null);
  };

  const runSpectralAnalysis = async () => {
    setIsAnalyzing(true);
    await new Promise((r) => setTimeout(r, 600)); // realistic compute delay
    if (metadata) {
      const centerMhz = metadata.centerFreqHz / 1e6;
      setSpectralData(generateMockSpectrum(centerMhz, 1.8, 18.4));
      setConstellationPoints(generateMockConstellation(selectedModulation, 600, 18.4));
      setWaterfallFrames(generateMockWaterfall(64, 128));
    }
    setIsAnalyzing(false);
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

