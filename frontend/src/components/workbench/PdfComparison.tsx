'use client';

import { useMemo, useRef, useState } from 'react';
import { AlertCircle, Check, FileText, LoaderCircle, Upload } from 'lucide-react';
import type { SignalMetadata } from '../../lib/dsp-types';
import type { SigmaRecoveryResult } from '../../lib/sigma-api';
import { extractPdfText, parsePdfFindings, type PdfFinding } from '../../lib/pdf-findings';

type Comparison = { label: string; pdfValue: string; sigmaValue: string; status: 'match' | 'mismatch' | 'pdf-only' | 'sigma-only' | 'no-result' };
const fieldLabels: Record<string, string> = {
  modulation: 'Modulation', sampleRate: 'Sample rate', centerFrequency: 'Center frequency',
  bandwidth: 'Bandwidth', snr: 'SNR', symbolRate: 'Symbol rate', carrierOffset: 'Carrier offset', fec: 'FEC', ber: 'BER',
};

function parseNumber(value?: string) {
  if (!value) return undefined;
  const match = value.replace(/,/g, '').match(/-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/i);
  return match ? Number(match[0]) : undefined;
}

function sigmaFindings(result: SigmaRecoveryResult | null, metadata: SignalMetadata | null): Map<string, PdfFinding> {
  const values = new Map<string, PdfFinding>();
  if (metadata) {
    values.set('sampleRate', { key: 'sampleRate', label: 'Sample rate', value: `${metadata.sampleRateHz} Hz`, normalized: metadata.sampleRateHz, unit: 's⁻¹' });
    values.set('centerFrequency', { key: 'centerFrequency', label: 'Center frequency', value: `${metadata.centerFreqHz} Hz`, normalized: metadata.centerFreqHz, unit: 'Hz' });
  }
  if (!result) return values;
  const modulation = result.classification?.modulation;
  if (modulation && !['--', 'Not analyzed', 'Unknown'].includes(modulation)) values.set('modulation', { key: 'modulation', label: 'Modulation', value: modulation });
  const snr = result.signal_metrics?.snr_str;
  const snrNumber = parseNumber(snr);
  if (snr && snrNumber !== undefined) values.set('snr', { key: 'snr', label: 'SNR', value: snr, normalized: snrNumber, unit: 'dB' });
  const symbolRate = result.signal_metrics?.symbol_rate_str;
  const symbolRateNumber = parseNumber(symbolRate);
  if (symbolRate && symbolRateNumber !== undefined) values.set('symbolRate', { key: 'symbolRate', label: 'Symbol rate', value: symbolRate, normalized: symbolRateNumber, unit: 's⁻¹' });
  const fec = result.fec?.fec_type;
  if (fec && fec !== '--' && fec !== 'None') values.set('fec', { key: 'fec', label: 'FEC', value: fec });
  return values;
}

function compareValue(pdf: PdfFinding, sigma: PdfFinding) {
  if (pdf.normalized !== undefined && sigma.normalized !== undefined) {
    const tolerance = Math.max(Math.abs(pdf.normalized) * 0.03, pdf.key === 'snr' ? 0.5 : 1);
    return Math.abs(pdf.normalized - sigma.normalized) <= tolerance;
  }
  const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '');
  return normalize(pdf.value) === normalize(sigma.value);
}

export function PdfComparison({ result, metadata }: { result: SigmaRecoveryResult | null; metadata: SignalMetadata | null }) {
  const input = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState('');
  const [findings, setFindings] = useState<PdfFinding[]>([]);
  const [pages, setPages] = useState(0);
  const [isReading, setIsReading] = useState(false);
  const [error, setError] = useState('');
  const sigma = useMemo(() => sigmaFindings(result, metadata), [result, metadata]);

  const comparisons = useMemo<Comparison[]>(() => {
    const fromPdf = new Map(findings.map((finding) => [finding.key, finding]));
    const keys = new Set([...fromPdf.keys(), ...sigma.keys()]);
    return [...keys].map((key) => {
      const pdf = fromPdf.get(key);
      const local = sigma.get(key);
      const status = !result ? 'no-result' : pdf && local ? (compareValue(pdf, local) ? 'match' : 'mismatch') : pdf ? 'pdf-only' : 'sigma-only';
      return { label: fieldLabels[key] ?? key, pdfValue: pdf?.value ?? 'Not listed', sigmaValue: local?.value ?? 'Not measured', status };
    });
  }, [findings, result, sigma]);

  const readFile = async (file?: File) => {
    setError('');
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) { setError('Choose a PDF file.'); return; }
    if (file.size > 25 * 1024 * 1024) { setError('This PDF is larger than 25 MB.'); return; }
    setIsReading(true);
    setFileName(file.name);
    setFindings([]);
    try {
      const extracted = await extractPdfText(file);
      const parsed = parsePdfFindings(extracted.text);
      setPages(extracted.pages);
      setFindings(parsed);
      if (!extracted.text.trim()) setError('This PDF contains no selectable text. Scanned PDFs need OCR before values can be compared.');
      else if (!parsed.length) setError('The PDF text was read, but no supported finding fields were recognized.');
    } catch (cause) {
      setError(cause instanceof Error ? `Could not read this PDF: ${cause.message}` : 'Could not read this PDF.');
    } finally { setIsReading(false); }
  };

  return (
    <section className="space-y-5">
      <div className="border-b border-zinc-800 pb-5">
        <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-400">Finding review</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">Compare a PDF report</h2>
        <p className="mt-1 max-w-2xl font-sans text-sm text-zinc-400">Compare values from a report with this capture’s SIGMA measurements. The PDF stays in your browser.</p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.75fr)]">
        <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
          <input ref={input} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(event) => void readFile(event.target.files?.[0])} />
          <button type="button" onClick={() => input.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); void readFile(event.dataTransfer.files?.[0]); }} className="flex min-h-36 w-full flex-col items-center justify-center border border-dashed border-zinc-700 bg-zinc-950/50 px-4 text-center hover:border-cyan-800">
            {isReading ? <LoaderCircle className="h-5 w-5 animate-spin text-cyan-400" /> : <Upload className="h-5 w-5 text-cyan-400" />}
            <span className="mt-3 text-sm font-medium text-zinc-200">{isReading ? 'Reading report locally…' : fileName || 'Choose a PDF findings report'}</span>
            <span className="mt-1 text-xs text-zinc-500">Select or drop one text-based PDF · up to 25 MB</span>
          </button>
          {error && <p role="alert" className="mt-3 flex items-start gap-2 text-xs text-amber-300"><AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{error}</p>}
          {pages > 0 && <p className="mt-3 flex items-center gap-2 text-xs text-zinc-500"><FileText className="h-3.5 w-3.5" />{pages} page{pages === 1 ? '' : 's'} · {findings.length} recognized value{findings.length === 1 ? '' : 's'}</p>}
          {!findings.length && !isReading && <p className="mt-6 text-center text-xs text-zinc-600">Recognized fields include modulation, frequency, bandwidth, SNR, symbol rate, FEC, and BER.</p>}
        </section>

        <aside className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
          <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Comparison basis</p>
          <h3 className="mt-1 text-sm font-semibold text-white">Current capture</h3>
          <p className="mt-2 truncate font-mono text-xs text-cyan-300">{metadata?.name ?? 'No capture selected'}</p>
          <p className="mt-3 text-xs leading-relaxed text-zinc-500">{result ? `SIGMA returned ${result.overall_status ?? 'an analysis result'}. Only fields in that result are compared; unavailable values remain unmeasured.` : 'Run the analysis pipeline on an IQ or WAV capture to compare report values against returned results.'}</p>
          {result?.classification?.confidence_evidence && <p className="mt-3 border-t border-zinc-800 pt-3 text-[11px] text-zinc-500">Classifier evidence: <span className="text-zinc-300">{result.classification.confidence_evidence}</span></p>}
        </aside>
      </div>

      {findings.length > 0 && <section className="overflow-hidden border border-zinc-800 bg-[#0c0c0e]">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3"><div><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Field comparison</p><h3 className="mt-1 text-sm font-semibold text-white">{findings.length} report value{findings.length === 1 ? '' : 's'} checked</h3></div><span className="text-[10px] text-zinc-500">3% numeric tolerance · 0.5 dB for SNR</span></div>
        <div className="divide-y divide-zinc-800">
          {comparisons.map((row) => <div key={row.label} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(100px,0.7fr)_1fr_1fr_112px] sm:items-center">
            <span className="text-xs text-zinc-400">{row.label}</span><span className="text-xs text-zinc-200"><span className="mr-1 text-[9px] uppercase text-zinc-600 sm:hidden">PDF</span>{row.pdfValue}</span><span className="text-xs text-zinc-200"><span className="mr-1 text-[9px] uppercase text-zinc-600 sm:hidden">SIGMA</span>{row.sigmaValue}</span>
            <span className={`inline-flex w-fit items-center gap-1 border px-2 py-1 text-[10px] uppercase ${row.status === 'match' ? 'border-emerald-900 bg-emerald-950/30 text-emerald-300' : row.status === 'mismatch' ? 'border-rose-900 bg-rose-950/30 text-rose-300' : 'border-zinc-700 text-zinc-400'}`}>{row.status === 'match' && <Check className="h-3 w-3" />}{row.status === 'match' ? 'Match' : row.status === 'mismatch' ? 'Mismatch' : row.status === 'pdf-only' ? 'Not measured' : row.status === 'sigma-only' ? 'PDF not listed' : 'Run analysis'}</span>
          </div>)}
        </div>
        <p className="border-t border-zinc-800 px-4 py-3 text-[10px] text-zinc-600">Values are extracted from selectable PDF text. This view does not judge whether either measurement is correct.</p>
      </section>}
    </section>
  );
}
