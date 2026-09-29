export interface PdfFinding {
  key: string;
  label: string;
  value: string;
  normalized?: number;
  unit?: string;
}

const patterns: Array<{ key: string; label: string; regex: RegExp; factor?: number; unit?: string }> = [
  { key: 'modulation', label: 'Modulation', regex: /(?:modulation(?:\s+type)?|class(?:ification)?)\s*[:=\-]?\s*(BPSK|QPSK|8\s*PSK|16\s*QAM|64\s*QAM|BFSK|2\s*FSK|4\s*FSK|GMSK|OFDM|UNKNOWN)/i },
  { key: 'sampleRate', label: 'Sample rate', regex: /(?:sample\s*rate|sampling\s*rate)\s*[:=\-]?\s*(\d+(?:[.,]\d+)?)\s*(MSPS|MS\/S|KSPS|KS\/S|SPS|HZ|KHZ|MHZ)?/i },
  { key: 'centerFrequency', label: 'Center frequency', regex: /(?:center\s*frequency|centre\s*frequency|carrier\s*frequency|frequency)\s*[:=\-]?\s*(\d+(?:[.,]\d+)?)\s*(GHZ|MHZ|KHZ|HZ)?/i },
  { key: 'bandwidth', label: 'Bandwidth', regex: /(?:occupied\s+)?bandwidth\s*[:=\-]?\s*(\d+(?:[.,]\d+)?)\s*(GHZ|MHZ|KHZ|HZ)?/i },
  { key: 'snr', label: 'SNR', regex: /(?:signal\s*[- ]?to\s*[- ]?noise(?:\s+ratio)?|SNR)\s*[:=\-]?\s*(-?\d+(?:[.,]\d+)?)\s*(DB)?/i },
  { key: 'symbolRate', label: 'Symbol rate', regex: /(?:symbol\s*rate|baud\s*rate)\s*[:=\-]?\s*(\d+(?:[.,]\d+)?)\s*(MBAUD|KBAUD|BAUD|MSYM\/S|KSYM\/S|SYM\/S|MSPS|KSPS|SPS)?/i },
  { key: 'carrierOffset', label: 'Carrier offset', regex: /(?:carrier\s*(?:frequency\s*)?offset|frequency\s*offset|CFO)\s*[:=\-]?\s*(-?\d+(?:[.,]\d+)?)\s*(KHZ|HZ)?/i },
  { key: 'fec', label: 'FEC', regex: /(?:FEC|forward\s*error\s*correction|decoder)\s*[:=\-]?\s*(Hamming|Viterbi|Reed\s*[- ]?Solomon|LDPC|Convolutional|None)/i },
  { key: 'ber', label: 'BER', regex: /(?:bit\s*error\s*rate|BER)\s*[:=\-]?\s*(\d+(?:[.,]\d+)?(?:e[-+]?\d+)?)/i },
];

function numericUnit(value: string, unit = '') {
  const number = Number(value.replace(',', '.'));
  const normalizedUnit = unit.toLowerCase();
  let factor = 1;
  if (['ghz'].includes(normalizedUnit)) factor = 1e9;
  else if (['mhz', 'msps', 'mbaud', 'msym/s'].includes(normalizedUnit)) factor = 1e6;
  else if (['khz', 'ksps', 'kbaud', 'ksym/s'].includes(normalizedUnit)) factor = 1e3;
  else if (['sps', 'baud', 'sym/s'].includes(normalizedUnit)) factor = 1;
  return number * factor;
}

export function parsePdfFindings(text: string): PdfFinding[] {
  const normalizedText = text.replace(/\s+/g, ' ');
  return patterns.flatMap((pattern) => {
    const match = normalizedText.match(pattern.regex);
    if (!match) return [];
    const value = (match[1] ?? '').replace(/\s+/g, ' ').trim();
    if (!value) return [];
    const unit = (match[2] ?? '').toUpperCase();
    const numeric = /^-?\d/.test(value);
    let canonicalUnit: string | undefined;
    let normalized: number | undefined;
    if (numeric) {
      normalized = numericUnit(value, unit);
      canonicalUnit = pattern.key === 'sampleRate' || pattern.key === 'symbolRate' ? 's⁻¹' :
        ['centerFrequency', 'bandwidth', 'carrierOffset'].includes(pattern.key) ? 'Hz' :
          pattern.key === 'snr' ? 'dB' : undefined;
    }
    return [{ key: pattern.key, label: pattern.label, value: `${value}${unit ? ` ${unit}` : ''}`, normalized, unit: canonicalUnit }];
  });
}

export async function extractPdfText(file: File): Promise<{ text: string; pages: number }> {
  const pdfjs = await import('pdfjs-dist');
  pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
  const document = await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
  const pages: string[] = [];
  for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber++) {
    const page = await document.getPage(pageNumber);
    const content = await page.getTextContent();
    pages.push(content.items.map((item) => ('str' in item ? item.str : '')).join(' '));
  }
  return { text: pages.join('\n'), pages: document.numPages };
}
