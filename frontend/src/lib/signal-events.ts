export interface EnergyCandidate {
  id: string;
  startSeconds: number;
  endSeconds: number;
  lowMhz: number;
  highMhz: number;
  peakDb: number;
}

export function findEnergyCandidates(
  waterfall: number[][] | undefined,
  frequenciesNorm: number[] | undefined,
  sampleRateHz: number,
  centerFrequencyHz: number,
  durationSeconds: number,
): EnergyCandidate[] {
  if (!waterfall?.length || !frequenciesNorm?.length || !sampleRateHz || !durationSeconds) return [];
  const rows = waterfall.filter((row) => row.length === frequenciesNorm.length);
  if (!rows.length) return [];
  const sorted = rows.flat().filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return [];
  const floor = sorted[Math.floor((sorted.length - 1) * 0.6)];
  const threshold = floor + 8;
  const minBins = Math.max(2, Math.floor(frequenciesNorm.length * 0.008));
  const slices: Array<{ row: number; from: number; to: number; peak: number }> = [];

  rows.forEach((values, rowIndex) => {
    const active = values.map((value, index) => value > threshold ? index : -1).filter((index) => index >= 0);
    if (!active.length) return;
    let from = active[0];
    let to = from;
    for (const bin of active.slice(1)) {
      if (bin <= to + 2) to = bin;
      else {
        if (to - from + 1 >= minBins) slices.push({ row: rowIndex, from, to, peak: Math.max(...values.slice(from, to + 1)) });
        from = to = bin;
      }
    }
    if (to - from + 1 >= minBins) slices.push({ row: rowIndex, from, to, peak: Math.max(...values.slice(from, to + 1)) });
  });

  const groups: Array<{ firstRow: number; lastRow: number; low: number; high: number; peak: number }> = [];
  for (const slice of slices) {
    const match = groups.find((group) => group.lastRow === slice.row - 1 && slice.from <= group.high + minBins && slice.to >= group.low - minBins);
    if (match) {
      match.lastRow = slice.row;
      match.low = Math.min(match.low, slice.from);
      match.high = Math.max(match.high, slice.to);
      match.peak = Math.max(match.peak, slice.peak);
    } else groups.push({ firstRow: slice.row, lastRow: slice.row, low: slice.from, high: slice.to, peak: slice.peak });
  }

  const candidates = groups.filter((group) => group.lastRow - group.firstRow >= 0).slice(0, 12);
  return candidates.map((group, index) => {
    const lowNorm = frequenciesNorm[Math.max(0, group.low)];
    const highNorm = frequenciesNorm[Math.min(frequenciesNorm.length - 1, group.high)];
    const toMhz = (normalized: number) => (centerFrequencyHz + normalized * sampleRateHz) / 1e6;
    return {
      id: `E-${String(index + 1).padStart(2, '0')}`,
      startSeconds: (group.firstRow / rows.length) * durationSeconds,
      endSeconds: ((group.lastRow + 1) / rows.length) * durationSeconds,
      lowMhz: toMhz(lowNorm),
      highMhz: toMhz(highNorm),
      peakDb: group.peak,
    };
  });
}
