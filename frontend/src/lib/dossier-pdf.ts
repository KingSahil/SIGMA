import type { SigmaPlotData } from './sigma-api';
import type { SpectralAnalysisResult } from './dsp-types';

export interface DossierSignal {
  id: string;
  modulation: string;
  frequency: string;
  bandwidth: string;
  snr: string;
  state: string;
}

export interface DossierDetails {
  fileName: string;
  format: string;
  sampleRate: string;
  centerFrequency: string;
  duration: string;
  modulation: string;
  bandwidth: string;
  snr: string;
  signals: DossierSignal[];
  plotData?: SigmaPlotData | null;
  spectralData?: SpectralAnalysisResult | null;
  classificationEvidence?: string;
  demodulationStatus?: string;
  deinterleavingStatus?: string;
  fecStatus?: string;
  correlationStatus?: string;
  bitCount?: number;
  isPreview?: boolean;
  analystNotes?: string[];
}

function escapePdfText(value: string) {
  return value
    .normalize('NFKD')
    .replace(/[^\x20-\x7E]/g, '')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');
}

function wrapLine(line: string, max = 88) {
  const words = line.split(/\s+/);
  const result: string[] = [];
  let current = '';
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > max && current) {
      result.push(current);
      current = word;
    } else current = next;
  }
  if (current) result.push(current);
  return result;
}

export function createDossierPdf(details: DossierDetails) {
  // The regular spectral analysis is available for both preview and live captures.
  // Prefer API FFT frames, but never leave the dossier without the measured spectrum
  // already visible in the workbench.
  const spectrum = details.plotData?.spectrum_db?.length
    ? details.plotData.spectrum_db
    : details.spectralData?.powerDbfs ?? [];
  const spectrumSource = details.plotData?.spectrum_db?.length
    ? 'ANALYSIS API FFT FRAME'
    : details.spectralData?.powerDbfs?.length
      ? 'WORKBENCH SPECTRAL ANALYSIS'
      : 'NO SPECTRUM RETURNED';
  const rows = [
    'SIGNAL ANALYSIS DOSSIER',
    `Generated ${new Date().toLocaleString()}`,
    '',
    'RECORDING',
    `File: ${details.fileName}`,
    `Format: ${details.format}`,
    `Sample rate: ${details.sampleRate}`,
    `Center frequency: ${details.centerFrequency}`,
    `Duration: ${details.duration}`,
    '',
    'SIGNAL CHARACTERIZATION',
    `Modulation: ${details.modulation}`,
    `Bandwidth: ${details.bandwidth}`,
    `SNR: ${details.snr}`,
    'Symbol rate: Not available',
    'Carrier frequency offset: Not available',
    `Classification evidence: ${details.classificationEvidence ?? 'Not available'}`,
    `Demodulation: ${details.demodulationStatus ?? 'Not established'}`,
    `De-interleaving: ${details.deinterleavingStatus ?? 'Not established'}`,
    `FEC: ${details.fecStatus ?? 'Not established'}`,
    `Correlation: ${details.correlationStatus ?? 'Not established'}`,
    `Recovered bit count: ${details.bitCount ?? 'Not available'}`,
    '',
    'DETECTED SIGNALS',
    ...details.signals.map((signal) =>
      `${signal.id} | ${signal.modulation} | ${signal.frequency} | ${signal.bandwidth} | ${signal.snr} | ${signal.state}`,
    ),
    'Classification confidence: Not available',
    'Anomaly findings: Not available',
    details.analystNotes?.length ? `Analyst reviews: ${details.analystNotes.length} included below` : 'Analyst review: None recorded for this capture',
    '',
    'METHOD & LIMITATIONS',
    `This dossier was generated from ${details.isPreview ? 'an illustrative frontend preview.' : 'the current SIGMA analysis API response.'}`,
    ...(details.analystNotes?.length ? ['ANALYST NOTES', ...details.analystNotes] : ['Analyst notes: None attached']),
    '',
    'VISUAL DIAGNOSTICS',
    spectrum.length ? 'The next page contains measured visual diagnostics for this capture.' : 'No measured visual diagnostic series was returned for this capture.',
    'IQ waveform is unavailable because the current API does not return a waveform series.',
    details.plotData?.constellation_i?.length ? 'Constellation points are returned I/Q samples, not symbol-sliced classification evidence.' : 'Constellation points were not returned by the analysis API.',
  ].flatMap(wrapLine);

  const pageRows: string[][] = [];
  for (let i = 0; i < rows.length; i += 45) pageRows.push(rows.slice(i, i + 45));

  const objects: string[] = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${[...pageRows.map((_, i) => `${4 + i * 2} 0 R`), `${4 + pageRows.length * 2} 0 R`].join(' ')}] /Count ${pageRows.length + 1} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];

  pageRows.forEach((page, index) => {
    const pageObject = 4 + index * 2;
    const contentObject = pageObject + 1;
    const stream = [
      'BT',
      '/F1 10 Tf',
      '48 748 Td',
      '14 TL',
      ...page.flatMap((line, row) => [
        row === 0 && index === 0 ? '/F1 18 Tf' : row === 0 ? '/F1 10 Tf' : '',
        `(${escapePdfText(line)}) Tj`,
        'T*',
      ]).filter(Boolean),
      'ET',
    ].join('\n');
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentObject} 0 R >>`);
    objects.push(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
  });

  const plotObject = 4 + pageRows.length * 2;
  const plotContentObject = plotObject + 1;
  const plot = [
    '0.04 0.05 0.07 rg 0 0 612 792 re f',
    '0.92 0.95 0.98 rg BT /F1 18 Tf 40 748 Td (VISUAL DIAGNOSTICS) Tj ET',
    `0.35 0.82 0.92 rg BT /F1 9 Tf 40 730 Td (${spectrumSource}) Tj ET`,
  ];
  const panel = (x: number, y: number, width: number, height: number, title: string, subtitle: string) => {
    plot.push(`0.08 0.09 0.12 rg ${x} ${y} ${width} ${height} re f`, `0.22 0.25 0.30 RG 0.6 w ${x} ${y} ${width} ${height} re S`);
    plot.push(`0.94 0.96 0.99 rg BT /F1 11 Tf ${x + 14} ${y + height - 22} Td (${escapePdfText(title)}) Tj ET`);
    plot.push(`0.48 0.53 0.60 rg BT /F1 8 Tf ${x + 14} ${y + height - 36} Td (${escapePdfText(subtitle)}) Tj ET`);
    const chartBottom = y + 32; const chartTop = y + height - 60;
    for (let i = 1; i <= 4; i++) plot.push(`0.18 0.20 0.24 RG 0.35 w ${x + 28} ${(chartBottom + i * (chartTop - chartBottom) / 5).toFixed(1)} m ${x + width - 20} ${(chartBottom + i * (chartTop - chartBottom) / 5).toFixed(1)} l S`);
    plot.push(`0.30 0.34 0.40 RG 0.45 w ${x + 28} ${chartBottom} m ${x + 28} ${chartTop} l S`, `0.30 0.34 0.40 RG 0.45 w ${x + 28} ${chartBottom} m ${x + width - 20} ${chartBottom} l S`);
  };
  const waterfall = details.plotData?.waterfall_db;
  const iSamples = details.plotData?.constellation_i;
  const qSamples = details.plotData?.constellation_q;
  const hasWaterfall = Boolean(waterfall?.length);
  const hasConstellation = Boolean(iSamples?.length && qSamples?.length);
  const spectrumHeight = hasWaterfall || hasConstellation ? 286 : 590;
  const spectrumY = hasWaterfall || hasConstellation ? 402 : 92;
  panel(40, spectrumY, 532, spectrumHeight, spectrum.length ? 'MEASURED SPECTRUM' : 'SPECTRUM UNAVAILABLE', spectrum.length ? 'Power (dBFS) across the captured band' : 'No FFT values were returned for this capture');
  if (spectrum?.length) {
    const low = Math.min(...spectrum), span = Math.max(1, Math.max(...spectrum) - low);
    const stride = Math.max(1, Math.floor(spectrum.length / 100));
    const chartBottom = spectrumY + 32; const chartHeight = spectrumHeight - 92;
    let trace = `0.15 0.75 0.85 RG 1.2 w 68 ${(chartBottom + (spectrum[0] - low) / span * chartHeight).toFixed(1)} m`;
    for (let index = stride; index < spectrum.length; index += stride) {
      const x = 68 + ((index / (spectrum.length - 1)) * 484);
      const y = chartBottom + (spectrum[index] - low) / span * chartHeight;
      trace += ` ${x.toFixed(1)} ${y.toFixed(1)} l`;
    }
    plot.push(`${trace} S`);
    plot.push(`0.48 0.53 0.60 rg BT /F1 8 Tf 68 ${spectrumY + 14} Td (${escapePdfText(details.spectralData?.frequencies?.length ? `${details.spectralData.frequencies[0].toFixed(3)} MHz` : 'Band start')}) Tj ET`);
    plot.push(`0.48 0.53 0.60 rg BT /F1 8 Tf 470 ${spectrumY + 14} Td (${escapePdfText(details.spectralData?.frequencies?.length ? `${details.spectralData.frequencies.at(-1)?.toFixed(3)} MHz` : 'Band end')}) Tj ET`);
  }
  if (waterfall?.length) {
    panel(40, 92, hasConstellation ? 250 : 532, 270, 'MEASURED WATERFALL', 'Time-frequency power');
    const values = waterfall.flat(); const low = Math.min(...values), span = Math.max(1, Math.max(...values) - low);
    const rowStep = Math.max(1, Math.floor(waterfall.length / 10));
    const colStep = Math.max(1, Math.floor(Math.min(...waterfall.map((row) => row.length)) / (hasConstellation ? 18 : 42)));
    let drawnRow = 0;
    for (let row = 0; row < waterfall.length; row += rowStep) {
      let drawnCol = 0;
      for (let col = 0; col < waterfall[row].length; col += colStep) {
        const t = Math.max(0, Math.min(1, (waterfall[row][col] - low) / span));
        const cellWidth = hasConstellation ? 11 : 11.4;
        plot.push(`${(0.05 + t * 0.25).toFixed(2)} ${(0.12 + t * 0.7).toFixed(2)} ${(0.22 + t * 0.7).toFixed(2)} rg ${(68 + drawnCol * cellWidth).toFixed(1)} ${118 + drawnRow * 19} ${(cellWidth - 1).toFixed(1)} 17 re f`);
        drawnCol++;
      }
      drawnRow++;
    }
  }
  if (iSamples?.length && qSamples?.length) {
    const xOffset = hasWaterfall ? 322 : 40;
    const panelWidth = hasWaterfall ? 250 : 532;
    panel(xOffset, 92, panelWidth, 270, 'I/Q CONSTELLATION', 'Returned complex samples');
    const centerX = xOffset + panelWidth / 2; const centerY = 212;
    plot.push(`0.28 0.31 0.36 RG 0.6 w ${centerX} 118 m ${centerX} 302 l S ${xOffset + 28} ${centerY} m ${xOffset + panelWidth - 20} ${centerY} l S`);
    const extent = Math.max(1, ...iSamples.map((i, index) => Math.max(Math.abs(i), Math.abs(qSamples[index] ?? 0))));
    for (let index = 0; index < Math.min(iSamples.length, qSamples.length, 180); index++) {
      const x = centerX + iSamples[index] / extent * (panelWidth / 2 - 36);
      const y = centerY + qSamples[index] / extent * 74;
      plot.push(`0.25 0.85 0.90 rg ${x.toFixed(1)} ${y.toFixed(1)} 2 2 re f`);
    }
  }
  if (!spectrum.length && !hasWaterfall && !hasConstellation) plot.push('0.65 0.68 0.74 rg BT /F1 10 Tf 58 380 Td (Run a capture analysis to include measured spectrum, waterfall, and constellation visuals.) Tj ET');
  plot.push('0.48 0.53 0.60 rg BT /F1 8 Tf 40 62 Td (Plots use values returned by the analysis pipeline. No synthetic chart data is added.) Tj ET');
  const plotStream = plot.join('\n');
  objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${plotContentObject} 0 R >>`);
  objects.push(`<< /Length ${plotStream.length} >>\nstream\n${plotStream}\nendstream`);

  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefOffset = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.slice(1).forEach((offset) => {
    pdf += `${offset.toString().padStart(10, '0')} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  return new Blob([pdf], { type: 'application/pdf' });
}

export function downloadDossierPdf(details: DossierDetails) {
  const blob = createDossierPdf(details);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${details.fileName.replace(/\.[^.]+$/, '') || 'signal-analysis'}-dossier.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}
