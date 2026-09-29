import {
  PresetSignalOption,
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
} from './dsp-types';

export const PRESET_SIGNALS: PresetSignalOption[] = [
  {
    id: 'cubesat_qpsk_433',
    name: 'CubeSat Telemetry Downlink',
    description: 'QPSK UHF beacon captured at 433.92 MHz with RRC pulse shaping and rate 1/2 FEC framing.',
    format: '.iq',
    sampleRateHz: 2400000,
    centerFreqHz: 433920000,
    sizeBytes: 42600000, // 42.6 MB
    durationSeconds: 4.43,
    defaultModulation: 'QPSK',
    snrDb: 18.4,
    bandwidthMhz: 1.8,
  },
  {
    id: 'noaa_apt_fsk_137',
    name: 'NOAA-19 Weather Sat APT',
    description: 'VHF Analog/FSK transmission recording at 137.1 MHz with frequency shift keying subcarrier.',
    format: '.wav',
    sampleRateHz: 1200000,
    centerFreqHz: 137100000,
    sizeBytes: 15400000, // 15.4 MB
    durationSeconds: 6.41,
    defaultModulation: '2FSK',
    snrDb: 14.2,
    bandwidthMhz: 0.04,
  },
  {
    id: 'tactical_16qam_868',
    name: 'Tactical UAV Telemetry',
    description: '16-QAM high-throughput link captured in the 868 MHz ISM band with block interleaving.',
    format: '.iq',
    sampleRateHz: 4000000,
    centerFreqHz: 868000000,
    sizeBytes: 68200000, // 68.2 MB
    durationSeconds: 4.26,
    defaultModulation: '16QAM',
    snrDb: 22.8,
    bandwidthMhz: 2.4,
  },
];

// Helper: Gaussian random number (Box-Muller)
function gaussianRandom(mean = 0, stdev = 1): number {
  const u = 1 - Math.random();
  const v = Math.random();
  const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return z * stdev + mean;
}

/**
 * Generate simulated FFT Power Spectrum (dBFS vs Frequency)
 */
export function generateMockSpectrum(
  centerFreqMhz: number,
  bandwidthMhz: number,
  snrDb: number,
  numPoints = 256
): SpectralAnalysisResult {
  const spanMhz = bandwidthMhz * 2.5;
  const startFreq = centerFreqMhz - spanMhz / 2;
  const step = spanMhz / (numPoints - 1);
  const noiseFloor = -85;
  const signalPeak = noiseFloor + snrDb;

  const frequencies: number[] = [];
  const powerDbfs: number[] = [];

  for (let i = 0; i < numPoints; i++) {
    const f = startFreq + i * step;
    frequencies.push(Number(f.toFixed(4)));

    // Base noise with slight random fluctuation
    const noise = noiseFloor + (Math.random() * 6 - 3);

    // Raised-cosine-like spectral hump around center frequency
    const deltaF = Math.abs(f - centerFreqMhz);
    let signalPower = 0;

    if (deltaF < bandwidthMhz / 2) {
      // In-band signal
      const rollOff = Math.cos((Math.PI * deltaF) / bandwidthMhz);
      signalPower = (signalPeak - noiseFloor) * Math.pow(rollOff, 0.5);
    } else if (deltaF < bandwidthMhz * 0.7) {
      // Transition skirt
      const rollOff = Math.cos((Math.PI * (deltaF - bandwidthMhz / 2)) / (bandwidthMhz * 0.4));
      signalPower = Math.max(0, (signalPeak - noiseFloor) * 0.2 * rollOff);
    }

    const totalPower = noise + signalPower + (Math.random() * 2 - 1);
    powerDbfs.push(Number(totalPower.toFixed(2)));
  }

  return {
    frequencies,
    powerDbfs,
    peakFreqMhz: centerFreqMhz,
    estimatedCarrierMhz: centerFreqMhz,
    bandwidthMhz,
    snrDb,
    noiseFloorDbfs: noiseFloor,
    estimatedModulation: 'QPSK',
    confidence: 0.94,
    rolloffFactor: 0.35,
  };
}

/**
 * Generate simulated Constellation Points (I/Q scatter)
 */
export function generateMockConstellation(
  modType: ModulationType,
  numPoints = 600,
  snrDb = 18
): ConstellationPoint[] {
  const points: ConstellationPoint[] = [];
  const noiseStdev = Math.pow(10, -snrDb / 20) * 0.5;

  let idealSymbols: [number, number][] = [];

  switch (modType) {
    case 'BPSK':
      idealSymbols = [[-1, 0], [1, 0]];
      break;
    case 'QPSK':
      idealSymbols = [
        [1, 1], [-1, 1], [-1, -1], [1, -1]
      ].map(([i, q]) => [i * 0.707, q * 0.707]);
      break;
    case '8PSK':
      for (let k = 0; k < 8; k++) {
        const theta = (k * 2 * Math.PI) / 8 + Math.PI / 8;
        idealSymbols.push([Math.cos(theta), Math.sin(theta)]);
      }
      break;
    case '16QAM':
      for (const i of [-3, -1, 1, 3]) {
        for (const q of [-3, -1, 1, 3]) {
          idealSymbols.push([i / 3.16, q / 3.16]);
        }
      }
      break;
    case '64QAM':
      for (const i of [-7, -5, -3, -1, 1, 3, 5, 7]) {
        for (const q of [-7, -5, -3, -1, 1, 3, 5, 7]) {
          idealSymbols.push([i / 6.48, q / 6.48]);
        }
      }
      break;
    case '2FSK':
    case '4FSK':
      // FSK shows as ring/frequency circle in baseband
      for (let k = 0; k < (modType === '2FSK' ? 2 : 4); k++) {
        const angle = (k * 2 * Math.PI) / (modType === '2FSK' ? 2 : 4);
        idealSymbols.push([Math.cos(angle), Math.sin(angle)]);
      }
      break;
  }

  for (let i = 0; i < numPoints; i++) {
    const symIndex = Math.floor(Math.random() * idealSymbols.length);
    const [idealI, idealQ] = idealSymbols[symIndex];
    points.push({
      i: idealI + gaussianRandom(0, noiseStdev),
      q: idealQ + gaussianRandom(0, noiseStdev),
      symbolIndex: symIndex,
    });
  }

  return points;
}

/**
 * Generate simulated Waterfall Frames (Spectrogram Heatmap)
 */
export function generateMockWaterfall(
  numFrames = 64,
  binsPerFrame = 128,
  carrierCenterRatio = 0.5,
  bwRatio = 0.25
): WaterfallFrame[] {
  const frames: WaterfallFrame[] = [];
  const now = Date.now();

  for (let f = 0; f < numFrames; f++) {
    const bins: number[] = [];
    for (let b = 0; b < binsPerFrame; b++) {
      const pos = b / binsPerFrame;
      // Background noise baseline (20-60 in 0-255 scale)
      let val = Math.floor(Math.random() * 35 + 20);

      // Signal band energy
      const distFromCenter = Math.abs(pos - carrierCenterRatio);
      if (distFromCenter < bwRatio / 2) {
        // High energy signal in band (160 - 240)
        const envelope = Math.cos((Math.PI * distFromCenter) / (bwRatio / 2));
        val = Math.floor(val + (180 + Math.random() * 40) * Math.max(0, envelope));
      }
      bins.push(Math.min(255, Math.max(0, val)));
    }
    frames.push({
      timestamp: now - (numFrames - f) * 100,
      bins,
    });
  }

  return frames;
}

/**
 * Generate simulated Demodulation Output
 */
export function generateMockDemod(modType: ModulationType = 'QPSK'): DemodulationResult {
  const points = generateMockConstellation(modType, 500, 18.4);
  const recoveredSymbols = points.map((p) => p.symbolIndex ?? 0);

  // Generate deterministic bit pattern containing sync word + telemetry
  const syncWord = '1010110011010010'; // 0xACD2
  let bitStream = syncWord;

  // Generate 1024 realistic bits
  for (let i = 0; i < 1024; i++) {
    bitStream += Math.random() > 0.5 ? '1' : '0';
  }

  return {
    modulation: modType,
    symbolRateBaud: 1200000,
    constellationPoints: points,
    recoveredSymbols: recoveredSymbols.slice(0, 128),
    rawBits: bitStream,
    bitLength: bitStream.length,
    evmPercent: 4.82,
  };
}

/**
 * Generate simulated De-interleaving Output (Matrix Transpose / Convolution)
 */
export function generateMockDeinterleave(
  inputBits: string,
  method: DeinterleaveMethod = 'block',
  rows = 16,
  cols = 32
): DeinterleaveResult {
  const totalLength = rows * cols;
  const stream = (inputBits + '0'.repeat(totalLength)).slice(0, totalLength);

  // Create Matrix
  const matrix: number[][] = [];
  let index = 0;
  for (let r = 0; r < rows; r++) {
    const row: number[] = [];
    for (let c = 0; c < cols; c++) {
      row.push(stream[index] === '1' ? 1 : 0);
      index++;
    }
    matrix.push(row);
  }

  // Deinterleave: read column by column
  let deinterleaved = '';
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) {
      deinterleaved += matrix[r][c].toString();
    }
  }

  // Count bit changes (positions that differ)
  let changes = 0;
  for (let i = 0; i < totalLength; i++) {
    if (stream[i] !== deinterleaved[i]) changes++;
  }

  return {
    method,
    rows,
    cols,
    beforeBits: stream,
    afterBits: deinterleaved,
    matrixPreview: matrix.slice(0, 8).map((r) => r.slice(0, 16)), // preview 8x16
    bitChangesCount: changes,
  };
}

/**
 * Generate simulated Forward Error Correction (FEC) Output
 */
export function generateMockFec(
  inputBits: string,
  codeType: FecCodeType = 'viterbi'
): FecResult {
  const bitCount = inputBits.length || 1024;
  // Simulate correcting ~1.2% errors
  const correctedErrors = Math.floor(bitCount * 0.0134) + 4;
  const ber = (correctedErrors / bitCount) * 100;

  // Clean the output bits (remove noise)
  const outputBits = inputBits;

  return {
    code: codeType,
    decoder: codeType === 'viterbi' ? 'Soft-Decision Viterbi (K=7, Rate 1/2)' : 'Berlekamp-Massey RS(255,223)',
    inputBitsCount: bitCount,
    correctedErrors,
    outputBits,
    outputBitsCount: bitCount,
    estimatedBer: Number((ber / 100).toFixed(5)),
    frameValid: true,
    syndromeHistory: [0, 0, 1, 0, 0, 0, 2, 0, 0, 1, 0, 0],
  };
}

/**
 * Generate simulated Bit Stream Correlation
 */
export function generateMockCorrelation(inputBits: string): CorrelationResult {
  const syncWord = '1010110011010010'; // 0xACD2
  const syncWordHex = '0xACD2';
  const numSteps = 120;
  const peakIndex = 48;

  const correlationScores: number[] = [];
  for (let i = 0; i < numSteps; i++) {
    if (i === peakIndex) {
      correlationScores.push(0.967); // 96.7% peak match
    } else {
      const dist = Math.abs(i - peakIndex);
      if (dist <= 3) {
        correlationScores.push(Number((0.967 / (dist + 1) + Math.random() * 0.1).toFixed(3)));
      } else {
        correlationScores.push(Number((Math.random() * 0.35 + 0.1).toFixed(3)));
      }
    }
  }

  const streamA = inputBits.slice(0, 64) || '1010110011010010110110001010011010010110101001011010110101010110';
  const streamB = syncWord + streamA.slice(syncWord.length);

  return {
    targetSyncWord: syncWord,
    syncWordHex,
    correlationScores,
    peakCorrelation: 0.967,
    peakIndex,
    detectedHeaderHex: 'AC D2 88 01',
    extractedPayloadHex: '48 65 6C 6C 6F 20 53 61 74 65 6C 6C 69 74 65 20 54 65 6C 65 6D 65 74 72 79',
    extractedPayloadAscii: 'Hello Satellite Telemetry',
    streamAExcerpt: streamA,
    streamBExcerpt: streamB,
  };
}

