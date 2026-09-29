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
    'Demodulation and synchronization: Not established',
    'FEC and de-interleaving: Not established in this frontend preview',
    'BER / CRC / correlation: Not available',
    '',
    'DETECTED SIGNALS',
    ...details.signals.map((signal) =>
      `${signal.id} | ${signal.modulation} | ${signal.frequency} | ${signal.bandwidth} | ${signal.snr} | ${signal.state}`,
    ),
    'Classification confidence: Not available',
    'Anomaly findings: Not available',
    'Analyst review: Not included in this capture',
    '',
    'METHOD & LIMITATIONS',
    'This dossier was generated from the current web frontend state.',
    'Illustrative sample records are not measurements from the uploaded file.',
    'Connect the analysis API to replace preview values with measured results.',
    '',
    'VISUAL DIAGNOSTICS',
    'The next page contains spectrum, waterfall, waveform and constellation previews.',
    'All plots are illustrative and are not measurements from the recording.',
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
    'BT /F1 9 Tf 40 730 Td (ILLUSTRATIVE PREVIEW - NOT MEASURED RECORDING DATA) Tj ET',
  ];
  const panel = (x: number, y: number, title: string) => {
    plot.push(`0.08 0.09 0.12 rg ${x} ${y} 250 270 re f`, `0.22 0.25 0.30 RG 0.6 w ${x} ${y} 250 270 re S`);
    plot.push(`BT /F1 11 Tf ${x + 12} ${y + 246} Td (${title}) Tj ET`);
    for (let i = 1; i <= 4; i++) plot.push(`0.18 0.20 0.24 RG 0.35 w ${x + 18} ${y + 24 + i * 38} m ${x + 234} ${y + 24 + i * 38} l S`);
    plot.push(`0.18 0.20 0.24 RG 0.35 w ${x + 18} ${y + 24} m ${x + 18} ${y + 214} l S`);
  };
  panel(40, 422, 'Spectrum / PSD');
  plot.push('0.15 0.75 0.85 RG 1.4 w 58 465 m 75 468 l 90 472 l 106 478 l 120 485 l 133 505 l 145 562 l 153 623 l 160 568 l 174 517 l 185 491 l 201 481 l 220 474 l 244 470 l 274 468 S');
  panel(322, 422, 'Waterfall');
  for (let row = 0; row < 9; row++) for (let col = 0; col < 18; col++) {
    const hot = (col > 5 && col < 8) || (col > 13 && (row + col) % 3 === 0);
    const red = hot ? 0.16 + ((row + col) % 4) * 0.12 : 0.05;
    const green = hot ? 0.40 + ((row * 3 + col) % 4) * 0.1 : 0.12;
    plot.push(`${red.toFixed(2)} ${green.toFixed(2)} 0.48 rg ${340 + col * 10} ${452 + row * 19} 9 17 re f`);
  }
  panel(40, 112, 'IQ waveform');
  let wave = '0.15 0.75 0.85 RG 1.2 w 58 245 m';
  for (let i = 1; i <= 54; i++) wave += ` ${58 + i * 4} ${207 + Math.round(Math.sin(i * 0.56) * 27)} l`;
  plot.push(`${wave} S`);
  panel(322, 112, 'Constellation');
  plot.push('0.28 0.31 0.36 RG 0.6 w 447 136 m 447 326 l S 340 231 m 556 231 l S');
  for (const [x, y] of [[384, 168], [384, 294], [510, 168], [510, 294]]) plot.push(`0.25 0.85 0.90 rg ${x} ${y} 6 6 re f`);
  plot.push('BT /F1 8 Tf 40 85 Td (Plots are visual placeholders until analysis-service measurements are connected.) Tj ET');
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
