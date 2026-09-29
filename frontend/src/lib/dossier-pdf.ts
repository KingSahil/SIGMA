import type { SigmaPlotData } from './sigma-api';

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

export function downloadDossierPdf(details: DossierDetails) {
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
    details.plotData?.spectrum_db?.length ? 'The next page contains spectrum and waterfall data returned for this capture.' : 'Spectrum and waterfall data were not returned for this capture.',
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
    'BT /F1 18 Tf 40 748 Td (VISUAL DIAGNOSTICS) Tj ET',
    `BT /F1 9 Tf 40 730 Td (${details.plotData ? 'MEASURED DATA RETURNED BY THE ANALYSIS API' : 'NO PLOT DATA RETURNED FOR THIS CAPTURE'}) Tj ET`,
  ];
  const panel = (x: number, y: number, title: string) => {
    plot.push(`0.08 0.09 0.12 rg ${x} ${y} 250 270 re f`, `0.22 0.25 0.30 RG 0.6 w ${x} ${y} 250 270 re S`);
    plot.push(`BT /F1 11 Tf ${x + 12} ${y + 246} Td (${title}) Tj ET`);
    for (let i = 1; i <= 4; i++) plot.push(`0.18 0.20 0.24 RG 0.35 w ${x + 18} ${y + 24 + i * 38} m ${x + 234} ${y + 24 + i * 38} l S`);
    plot.push(`0.18 0.20 0.24 RG 0.35 w ${x + 18} ${y + 24} m ${x + 18} ${y + 214} l S`);
  };
  panel(40, 422, details.plotData?.spectrum_db?.length ? 'Measured spectrum' : 'Spectrum not returned');
  const spectrum = details.plotData?.spectrum_db;
  if (spectrum?.length) {
    const low = Math.min(...spectrum), span = Math.max(1, Math.max(...spectrum) - low);
    const stride = Math.max(1, Math.floor(spectrum.length / 100));
    let trace = `0.15 0.75 0.85 RG 1.1 w 58 ${(452 + (1 - (spectrum[0] - low) / span) * 190).toFixed(1)} m`;
    for (let index = stride; index < spectrum.length; index += stride) {
      const x = 58 + ((index / (spectrum.length - 1)) * 216);
      const y = 452 + (1 - (spectrum[index] - low) / span) * 190;
      trace += ` ${x.toFixed(1)} ${y.toFixed(1)} l`;
    }
    plot.push(`${trace} S`);
  } else plot.push('BT /F1 9 Tf 58 535 Td (Not returned for this file type) Tj ET');
  panel(322, 422, details.plotData?.waterfall_db?.length ? 'Measured waterfall' : 'Waterfall not returned');
  const waterfall = details.plotData?.waterfall_db;
  if (waterfall?.length) {
    const values = waterfall.flat(); const low = Math.min(...values), span = Math.max(1, Math.max(...values) - low);
    const rowStep = Math.max(1, Math.floor(waterfall.length / 10));
    const colStep = Math.max(1, Math.floor(Math.min(...waterfall.map((row) => row.length)) / 18));
    let drawnRow = 0;
    for (let row = 0; row < waterfall.length; row += rowStep) {
      let drawnCol = 0;
      for (let col = 0; col < waterfall[row].length; col += colStep) {
        const t = Math.max(0, Math.min(1, (waterfall[row][col] - low) / span));
        plot.push(`${(0.05 + t * 0.25).toFixed(2)} ${(0.12 + t * 0.7).toFixed(2)} ${(0.22 + t * 0.7).toFixed(2)} rg ${340 + drawnCol * 11} ${448 + drawnRow * 19} 10 17 re f`);
        drawnCol++;
      }
      drawnRow++;
    }
  } else plot.push('BT /F1 9 Tf 340 535 Td (Not returned for this file type) Tj ET');
  panel(40, 112, 'IQ waveform');
  plot.push('BT /F1 9 Tf 58 215 Td (Not returned by the current analysis API) Tj ET');
  panel(322, 112, details.plotData?.constellation_i?.length ? 'Returned I/Q samples' : 'Constellation not returned');
  plot.push('0.28 0.31 0.36 RG 0.6 w 447 136 m 447 326 l S 340 231 m 556 231 l S');
  const iSamples = details.plotData?.constellation_i;
  const qSamples = details.plotData?.constellation_q;
  if (iSamples?.length && qSamples?.length) {
    const extent = Math.max(1, ...iSamples.map((i, index) => Math.max(Math.abs(i), Math.abs(qSamples[index] ?? 0))));
    for (let index = 0; index < Math.min(iSamples.length, qSamples.length, 180); index++) {
      const x = 448 + iSamples[index] / extent * 94;
      const y = 231 + qSamples[index] / extent * 88;
      plot.push(`0.25 0.85 0.90 rg ${x.toFixed(1)} ${y.toFixed(1)} 2 2 re f`);
    }
  } else plot.push('BT /F1 9 Tf 362 215 Td (No I/Q series returned) Tj ET');
  plot.push('BT /F1 8 Tf 40 85 Td (No generated placeholder plots are included.) Tj ET');
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

  const blob = new Blob([pdf], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${details.fileName.replace(/\.[^.]+$/, '') || 'signal-analysis'}-dossier.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}
