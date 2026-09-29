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
    'FEC and interleaving: Not established in this frontend preview',
    '',
    'DETECTED SIGNALS',
    ...details.signals.map((signal) =>
      `${signal.id} | ${signal.modulation} | ${signal.frequency} | ${signal.bandwidth} | ${signal.snr} | ${signal.state}`,
    ),
    '',
    'METHOD & LIMITATIONS',
    'This dossier was generated from the current web frontend state.',
    'Illustrative sample records are not measurements from the uploaded file.',
    'Connect the analysis API to replace preview values with measured results.',
    '',
    'VISUAL DIAGNOSTICS',
    'Spectrum, waterfall, waveform and constellation views are available in the workbench.',
    'Their current frontend rendering is illustrative and is not embedded as measured evidence.',
  ].flatMap(wrapLine);

  const pageRows: string[][] = [];
  for (let i = 0; i < rows.length; i += 45) pageRows.push(rows.slice(i, i + 45));

  const objects: string[] = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pageRows.map((_, i) => `${4 + i * 2} 0 R`).join(' ')}] /Count ${pageRows.length} >>`,
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
