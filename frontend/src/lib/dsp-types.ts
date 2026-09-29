export type PipelineStage = 
  | 'ingest'
  | 'spectral'
  | 'demod'
  | 'deinterleave'
  | 'fec'
  | 'correlate'
  | 'report';

export type SystemMode = 'simulation' | 'live';

export type ModulationType = 'BPSK' | 'QPSK' | '8PSK' | '16QAM' | '64QAM' | '2FSK' | '4FSK';

export type DeinterleaveMethod = 'block' | 'convolution' | 'diagonal' | 'pseudorandom';

export type FecCodeType = 'viterbi' | 'reed-solomon' | 'concatenated' | 'ldpc';

export interface SignalMetadata {
  id: string;
  name: string;
  format: '.iq' | '.wav' | '.bin';
  sizeBytes: number;
  sampleRateHz: number;      // e.g. 2,400,000 (2.4 MSps)
  centerFreqHz: number;      // e.g. 433,920,000 (433.92 MHz)
  durationSeconds: number;
  totalSamples: number;
  isPreset?: boolean;
  presetDescription?: string;
}

export interface SpectralAnalysisResult {
  frequencies: number[];     // Frequency points in MHz
  powerDbfs: number[];       // Power in dBFS (-100 to 0 dB)
  peakFreqMhz: number;
  estimatedCarrierMhz: number;
  bandwidthMhz: number;
  snrDb: number;
  noiseFloorDbfs: number;
  estimatedModulation: ModulationType;
  confidence: number;        // AI classification confidence 0.0 - 1.0
  rolloffFactor: number;     // e.g., 0.35 (RRC filter beta)
}

export interface ConstellationPoint {
  i: number;
  q: number;
  symbolIndex?: number;
}

export interface WaterfallFrame {
  timestamp: number;
  bins: number[];            // Power array (normalized 0 to 255 for color mapping)
}

export interface DemodulationResult {
  modulation: ModulationType;
  symbolRateBaud: number;
  constellationPoints: ConstellationPoint[];
  recoveredSymbols: number[];
  rawBits: string;           // '1010011...'
  bitLength: number;
  evmPercent: number;        // Error Vector Magnitude (%)
}

export interface DeinterleaveResult {
  method: DeinterleaveMethod;
  rows: number;
  cols: number;
  beforeBits: string;
  afterBits: string;
  matrixPreview: number[][]; // Visual representation of matrix
  bitChangesCount: number;
}

export interface FecResult {
  code: FecCodeType;
  decoder: string;
  inputBitsCount: number;
  correctedErrors: number;
  outputBits: string;
  outputBitsCount: number;
  estimatedBer: number;      // e.g. 0.0013 (0.13%)
  frameValid: boolean;
  syndromeHistory?: number[];
}

export interface CorrelationResult {
  targetSyncWord: string;    // e.g. "1010101111001010"
  syncWordHex: string;
  correlationScores: number[]; // Sliding correlation array (0 - 1.0)
  peakCorrelation: number;     // e.g. 0.965 (96.5%)
  peakIndex: number;
  detectedHeaderHex: string;
  extractedPayloadHex: string;
  extractedPayloadAscii: string;
  streamAExcerpt: string;
  streamBExcerpt: string;
}

export interface PresetSignalOption {
  id: string;
  name: string;
  description: string;
  format: '.iq' | '.wav' | '.bin';
  sampleRateHz: number;
  centerFreqHz: number;
  sizeBytes: number;
  durationSeconds: number;
  defaultModulation: ModulationType;
  snrDb: number;
  bandwidthMhz: number;
}

