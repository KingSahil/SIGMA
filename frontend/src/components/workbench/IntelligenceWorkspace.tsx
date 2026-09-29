'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowRight, Check, Download, FileText, MessageSquareText, Radio, Search, Sparkles } from 'lucide-react';
import { SignalMetadata, SpectralAnalysisResult } from '../../lib/dsp-types';
import { downloadDossierPdf, DossierSignal } from '../../lib/dossier-pdf';

type WorkspaceView = 'signals' | 'model' | 'analyst' | 'reports';

const sampleSignals: DossierSignal[] = [
  { id: 'SIG-01', modulation: 'QPSK', frequency: '433.92 MHz', bandwidth: '120 kHz', snr: '17.3 dB', state: 'Known class' },
  { id: 'SIG-02', modulation: 'FSK', frequency: '434.15 MHz', bandwidth: '250 kHz', snr: '—', state: 'Needs review' },
  { id: 'SIG-03', modulation: 'Unknown', frequency: '434.62 MHz', bandwidth: '—', snr: '—', state: 'Analyst review' },
];

const cardClass = 'border border-zinc-800 bg-[#0c0c0e]';
const mutedLabel = 'text-[10px] uppercase tracking-[0.14em] text-zinc-500';
const feedbackStorageKey = 'sigma-analyst-reviews-v1';

interface AnalystReview {
  id: string;
  signalId: string;
  label: string;
  notes: string;
  createdAt: string;
}

interface IntelligenceWorkspaceProps {
  metadata: SignalMetadata | null;
  spectralData: SpectralAnalysisResult | null;
}

export function IntelligenceWorkspace({ metadata, spectralData }: IntelligenceWorkspaceProps) {
  const [view, setView] = useState<WorkspaceView>('signals');
  const [selectedSignal, setSelectedSignal] = useState(sampleSignals[0].id);
  const [query, setQuery] = useState('Why is this signal classified as QPSK?');
  const [showAnswer, setShowAnswer] = useState(false);
  const [feedbackLabel, setFeedbackLabel] = useState('QPSK');
  const [feedbackNote, setFeedbackNote] = useState('');
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [reviews, setReviews] = useState<AnalystReview[]>([]);
  const [reportSaved, setReportSaved] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = window.localStorage.getItem(feedbackStorageKey);
        if (saved) setReviews(JSON.parse(saved) as AnalystReview[]);
      } catch {
        setReviews([]);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const activeSignal = useMemo(
    () => sampleSignals.find((signal) => signal.id === selectedSignal) ?? sampleSignals[0],
    [selectedSignal],
  );

  const reportDetails = {
    fileName: metadata?.name ?? 'sample-capture.iq',
    format: metadata?.format ?? '.iq',
    sampleRate: metadata ? `${(metadata.sampleRateHz / 1e6).toFixed(2)} MS/s` : 'Not provided',
    centerFrequency: metadata ? `${(metadata.centerFreqHz / 1e6).toFixed(3)} MHz` : 'Not provided',
    duration: metadata ? `${metadata.durationSeconds.toFixed(2)} s` : 'Not provided',
    modulation: spectralData?.estimatedModulation ?? 'Unclassified',
    bandwidth: spectralData ? `${spectralData.bandwidthMhz.toFixed(3)} MHz` : 'Not available',
    snr: spectralData ? `${spectralData.snrDb.toFixed(1)} dB` : 'Not available',
    signals: sampleSignals,
  };

  const saveFeedback = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const review: AnalystReview = { id: crypto.randomUUID(), signalId: activeSignal.id, label: feedbackLabel, notes: feedbackNote.trim(), createdAt: new Date().toISOString() };
    const updated = [review, ...reviews];
    setReviews(updated);
    try { window.localStorage.setItem(feedbackStorageKey, JSON.stringify(updated)); } catch { /* Browser storage may be disabled. */ }
    setFeedbackSaved(true);
  };

  const downloadReviews = () => {
    const quote = (value: string) => `"${value.replace(/"/g, '""')}"`;
    const csv = ['Review ID,Signal,Analyst label,Notes,Created at', ...reviews.map((review) => [review.id, review.signalId, review.label, review.notes, review.createdAt].map(quote).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'sigma-analyst-reviews.csv'; anchor.click(); URL.revokeObjectURL(url);
  };

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 border-b border-zinc-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-400">Investigation workspace</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">Signal intelligence</h2>
          <p className="mt-1 max-w-2xl font-sans text-sm text-zinc-400">Review detected events, inspect evidence, capture analyst feedback, and export a dossier.</p>
        </div>
        <div className="flex flex-wrap gap-1 border border-zinc-800 bg-zinc-950 p-1" role="tablist" aria-label="Investigation views">
          {([
            ['signals', 'Signals'],
            ['model', 'Model lab'],
            ['analyst', 'AI analyst'],
            ['reports', 'Reports'],
          ] as const).map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={view === id} onClick={() => setView(id)} className={`px-3 py-2 text-xs transition-colors ${view === id ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-start gap-2 border border-amber-900/60 bg-amber-950/20 px-3 py-2.5 text-xs text-amber-200" role="note">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <p><strong>Illustrative preview.</strong> Sample signal events and analyst responses below are not measurements from the current recording. Connect the analysis and intelligence services to populate verified results.</p>
      </div>

      {view === 'signals' && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
          <div className={`${cardClass} p-4 sm:p-5`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className={mutedLabel}>Recording event map</p>
                <h3 className="mt-1 text-sm font-semibold text-white">Multiple signal regions</h3>
              </div>
              <span className="border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400">SAMPLE VIEW · 3 EVENTS</span>
            </div>
            <div className="mt-5 overflow-x-auto">
              <div className="min-w-[560px]">
                <div className="mb-2 flex justify-between font-mono text-[10px] text-zinc-500"><span>0.0 s</span><span>1.5 s</span><span>3.0 s</span><span>4.5 s</span></div>
                <div className="space-y-2 border-y border-zinc-800 py-3">
                  {sampleSignals.map((signal, index) => (
                    <button key={signal.id} type="button" onClick={() => setSelectedSignal(signal.id)} className={`grid w-full grid-cols-[72px_1fr] items-center gap-3 rounded-sm px-2 py-2 text-left transition-colors ${selectedSignal === signal.id ? 'bg-cyan-950/30 ring-1 ring-cyan-800/70' : 'hover:bg-zinc-900'}`}>
                      <span className="font-mono text-[11px] text-zinc-300">{signal.id}</span>
                      <span className="relative h-6 border-l border-zinc-800 bg-zinc-950">
                        <span className={`absolute top-1 h-4 ${index === 0 ? 'left-[7%] w-[34%]' : index === 1 ? 'left-[38%] w-[44%]' : 'left-[66%] w-[21%]'} ${selectedSignal === signal.id ? 'bg-cyan-400/80' : index === 2 ? 'bg-amber-500/60' : 'bg-sky-700/80'}`} />
                      </span>
                    </button>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-[10px] text-zinc-500"><span className="flex items-center gap-1.5"><i className="h-2 w-2 bg-sky-700" />Classified</span><span className="flex items-center gap-1.5"><i className="h-2 w-2 bg-amber-500/70" />Review needed</span><span>Event times are illustrative</span></div>
              </div>
            </div>
            <div className="mt-5 divide-y divide-zinc-800 border-t border-zinc-800">
              {sampleSignals.map((signal) => (
                <button key={signal.id} type="button" onClick={() => setSelectedSignal(signal.id)} className={`flex w-full items-center justify-between gap-4 py-3 text-left ${selectedSignal === signal.id ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'}`}>
                  <span className="flex items-center gap-3"><Radio className={`h-4 w-4 ${signal.state === 'Known class' ? 'text-cyan-400' : 'text-amber-400'}`} /><span><span className="block text-xs font-medium">{signal.id} <span className="text-zinc-500">· {signal.modulation}</span></span><span className="mt-1 block text-[10px] text-zinc-500">{signal.frequency} · {signal.bandwidth}</span></span></span>
                  <span className="text-[10px] text-zinc-500">{signal.state}</span>
                </button>
              ))}
            </div>
          </div>

          <aside className={`${cardClass} p-4 sm:p-5`}>
            <p className={mutedLabel}>Signal object</p>
            <div className="mt-2 flex items-center justify-between"><h3 className="text-base font-semibold text-white">{activeSignal.id}</h3><span className="border border-amber-900/60 bg-amber-950/30 px-2 py-1 text-[10px] text-amber-300">{activeSignal.state}</span></div>
            <p className="mt-1 font-mono text-xs text-cyan-300">{activeSignal.modulation}</p>
            <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-4 border-y border-zinc-800 py-4">
              {[["Frequency", activeSignal.frequency], ["Bandwidth", activeSignal.bandwidth], ["SNR", activeSignal.snr], ["Symbol rate", 'Unknown']].map(([label, value]) => <div key={label}><dt className={mutedLabel}>{label}</dt><dd className="mt-1 text-sm text-zinc-200">{value}</dd></div>)}
            </dl>
            <div className="mt-4">
              <p className={mutedLabel}>Fingerprint & similarity</p>
              <p className="mt-2 font-sans text-xs leading-relaxed text-zinc-400">A signal fingerprint combines spectral shape, timing, modulation and capture metadata. Similarity search will appear here when a signal embedding index is connected.</p>
              <div className="mt-3 flex items-center gap-2 border border-dashed border-zinc-700 px-3 py-2 text-xs text-zinc-500"><Search className="h-3.5 w-3.5" />No historical matches loaded</div>
            </div>
            <div className="mt-5 border-t border-zinc-800 pt-4">
              <div className="flex items-center justify-between gap-2"><p className={mutedLabel}>Classifier & novelty</p><span className="text-[10px] text-zinc-600">MODEL NOT CONNECTED</span></div>
              <div className="mt-3 space-y-2 text-xs">
                <div className="flex justify-between gap-3"><span className="text-zinc-500">Modulation classifier</span><span className="text-zinc-400">No output</span></div>
                <div className="flex justify-between gap-3"><span className="text-zinc-500">Novelty decision</span><span className="text-zinc-400">Not evaluated</span></div>
                <div className="flex justify-between gap-3"><span className="text-zinc-500">Confidence breakdown</span><span className="text-zinc-400">Not available</span></div>
              </div>
              <p className="mt-3 font-sans text-[11px] leading-relaxed text-zinc-600">Class probabilities and unknown-signal decisions will render here when the model service returns scored candidates.</p>
            </div>
          </aside>
        </div>
      )}

      {view === 'model' && (
        <div className="space-y-5">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)]">
            <section className={`${cardClass} p-4 sm:p-5`}>
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className={mutedLabel}>Multimodal classifier</p><h3 className="mt-1 text-sm font-semibold text-white">Feature fusion pipeline</h3></div><span className="border border-amber-900/60 bg-amber-950/20 px-2 py-1 text-[10px] text-amber-300">MODEL SERVICE NOT CONNECTED</span></div>
              <div className="mt-5 grid gap-2 md:grid-cols-3">
                {[["01", "IQ samples", "Complex baseband windows"], ["02", "Spectrogram", "Time-frequency features"], ["03", "Constellation", "Symbol geometry features"]].map(([step, title, body]) => <div key={step} className="border border-zinc-800 bg-zinc-950 p-3"><span className="font-mono text-[10px] text-cyan-400">{step}</span><h4 className="mt-2 text-xs font-medium text-white">{title}</h4><p className="mt-1 text-[11px] text-zinc-500">{body}</p><p className="mt-3 border-t border-zinc-800 pt-2 text-[10px] text-zinc-600">Input status · awaiting service</p></div>)}
              </div>
              <div className="my-3 flex items-center justify-center text-[10px] uppercase tracking-wider text-zinc-600">Feature fusion ↓</div>
              <div className="border border-cyan-950 bg-cyan-950/10 p-4 text-center"><p className="text-xs font-medium text-cyan-100">CNN / CRNN / transformer candidate</p><p className="mt-1 text-[11px] text-zinc-500">Training and inference are not available in the web client.</p></div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="border border-zinc-800 p-3"><p className={mutedLabel}>Modulation outputs</p><p className="mt-2 text-xs text-zinc-400">BPSK · QPSK · 8PSK · FSK · QAM · Unknown</p><p className="mt-2 text-[10px] text-zinc-600">No probabilities returned</p></div><div className="border border-zinc-800 p-3"><p className={mutedLabel}>Novelty / confidence</p><p className="mt-2 text-xs text-zinc-400">Requires a calibrated model and reference embeddings.</p><p className="mt-2 text-[10px] text-zinc-600">No scores returned</p></div></div>
            </section>
            <aside className={`${cardClass} p-4 sm:p-5`}><p className={mutedLabel}>Dataset & training readiness</p><h3 className="mt-1 text-sm font-semibold text-white">Model registry</h3><dl className="mt-4 divide-y divide-zinc-800 border-y border-zinc-800">{[["Training datasets", "Not connected"], ["Active model version", "Not available"], ["Evaluation metrics", "Not available"], ["Label queue", `${reviews.length} local reviews`]].map(([label, value]) => <div key={label} className="flex justify-between gap-3 py-3 text-xs"><dt className="text-zinc-500">{label}</dt><dd className="text-zinc-300">{value}</dd></div>)}</dl><p className="mt-4 font-sans text-[11px] leading-relaxed text-zinc-500">Analyst labels saved in this browser can be exported from the AI analyst view. Model training requires a dataset registry and training service.</p></aside>
          </div>
        </div>
      )}

      {view === 'analyst' && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.78fr)]">
          <section className={`${cardClass} p-4 sm:p-5`}>
            <div className="flex items-center gap-2"><MessageSquareText className="h-4 w-4 text-cyan-400" /><h3 className="text-sm font-semibold text-white">Ask about this recording</h3><span className="ml-auto border border-zinc-700 px-2 py-1 text-[10px] text-zinc-500">RAG SERVICE NOT CONNECTED</span></div>
            <p className="mt-2 font-sans text-xs text-zinc-500">The analyst should explain DSP/ML output using retrieved references and clearly name unknowns.</p>
            <div className="mt-5 flex flex-wrap gap-2">{['Why this modulation?', 'What is uncertain?', 'Find similar captures'].map((suggestion) => <button key={suggestion} type="button" onClick={() => { setQuery(suggestion); setShowAnswer(false); }} className="border border-zinc-800 px-2.5 py-1.5 text-[10px] text-zinc-400 hover:border-zinc-600 hover:text-white">{suggestion}</button>)}</div>
            <form className="mt-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); setShowAnswer(true); }}>
              <input aria-label="Question for signal analyst" value={query} onChange={(event) => { setQuery(event.target.value); setShowAnswer(false); }} className="min-w-0 flex-1 border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-700" />
              <button className="flex items-center gap-2 bg-zinc-100 px-3 py-2 text-xs font-semibold text-black hover:bg-white" type="submit">Ask <ArrowRight className="h-3.5 w-3.5" /></button>
            </form>
            {showAnswer && <div className="mt-5 border-l-2 border-cyan-700 bg-zinc-950/80 p-4"><div className="flex items-center gap-2 text-xs font-medium text-cyan-200"><Sparkles className="h-3.5 w-3.5" />Preview response</div><p className="mt-2 font-sans text-sm leading-relaxed text-zinc-300">This sample view cannot verify a classification. A connected analyst service should cite the measured constellation and classifier output here. FEC and interleaving remain unknown unless a decoder establishes them.</p><div className="mt-4 border-t border-zinc-800 pt-3"><p className={mutedLabel}>Evidence to retrieve</p><div className="mt-2 flex flex-wrap gap-2 text-[10px] text-zinc-400"><span className="border border-zinc-800 px-2 py-1">DSP measurement</span><span className="border border-zinc-800 px-2 py-1">Model record</span><span className="border border-zinc-800 px-2 py-1">Technical reference</span></div></div></div>}
          </section>

          <section className={`${cardClass} p-4 sm:p-5`}>
            <p className={mutedLabel}>Analyst feedback</p>
            <h3 className="mt-1 text-sm font-semibold text-white">Review {activeSignal.id}</h3>
            <p className="mt-2 font-sans text-xs text-zinc-500">Reviews persist in this browser and can be exported for dataset curation. They are not sent to a training service.</p>
            <form className="mt-4 space-y-3" onSubmit={saveFeedback}>
              <label className="block text-xs text-zinc-400">Analyst label<select value={feedbackLabel} onChange={(event) => { setFeedbackLabel(event.target.value); setFeedbackSaved(false); }} className="mt-1.5 w-full border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-white"><option>QPSK</option><option>BPSK</option><option>8PSK</option><option>16QAM</option><option>FSK</option><option>Unknown</option></select></label>
              <label className="block text-xs text-zinc-400">Notes<textarea value={feedbackNote} onChange={(event) => { setFeedbackNote(event.target.value); setFeedbackSaved(false); }} rows={3} placeholder="Add a short evidence note" className="mt-1.5 w-full resize-y border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-white placeholder:text-zinc-600" /></label>
              <button type="submit" className="flex w-full items-center justify-center gap-2 bg-zinc-100 px-3 py-2.5 text-xs font-semibold text-black hover:bg-white"><Check className="h-3.5 w-3.5" />Save review</button>
              {feedbackSaved && <p role="status" className="text-xs text-emerald-300">Review saved in this browser. No dataset was updated.</p>}
            </form>
            <div className="mt-5 border-t border-zinc-800 pt-4">
              <div className="flex items-center justify-between gap-3"><p className={mutedLabel}>Local review queue · {reviews.length}</p><button type="button" disabled={!reviews.length} onClick={downloadReviews} className="flex items-center gap-1.5 border border-zinc-700 px-2.5 py-1.5 text-[10px] text-zinc-300 disabled:opacity-40"><Download className="h-3 w-3" />Export CSV</button></div>
              {reviews.length ? <ul className="mt-2 max-h-40 divide-y divide-zinc-800 overflow-y-auto">{reviews.slice(0, 8).map((review) => <li key={review.id} className="py-2 text-[11px]"><div className="flex justify-between gap-2"><span className="text-zinc-200">{review.signalId} · {review.label}</span><time className="text-zinc-600">{new Date(review.createdAt).toLocaleDateString()}</time></div>{review.notes && <p className="mt-1 line-clamp-2 text-zinc-500">{review.notes}</p>}</li>)}</ul> : <p className="mt-2 text-[11px] text-zinc-600">No analyst reviews saved in this browser yet.</p>}
            </div>
          </section>
        </div>
      )}

      {view === 'reports' && (
        <section className={`${cardClass} p-4 sm:p-6`}>
          <div className="flex flex-col gap-4 border-b border-zinc-800 pb-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3"><div className="rounded-sm border border-zinc-700 bg-zinc-950 p-2"><FileText className="h-4 w-4 text-cyan-400" /></div><div><p className={mutedLabel}>Investigation dossier</p><h3 className="mt-1 text-sm font-semibold text-white">{reportDetails.fileName}</h3><p className="mt-1 text-xs text-zinc-500">Recording metadata, signal summary, detected event list, and method notes.</p></div></div>
            <button type="button" onClick={() => { downloadDossierPdf(reportDetails); setReportSaved(true); }} className="shrink-0 bg-zinc-100 px-4 py-2.5 text-xs font-semibold text-black hover:bg-white">Download PDF dossier</button>
          </div>
          {reportSaved && <p role="status" className="mt-3 text-xs text-emerald-300">PDF dossier downloaded.</p>}
          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <div><p className={mutedLabel}>Recording information</p><dl className="mt-3 space-y-2 text-xs">{[["Format", reportDetails.format], ["Sample rate", reportDetails.sampleRate], ["Center frequency", reportDetails.centerFrequency], ["Duration", reportDetails.duration]].map(([label, value]) => <div key={label} className="flex justify-between gap-3 border-b border-zinc-900 pb-2"><dt className="text-zinc-500">{label}</dt><dd className="text-zinc-200">{value}</dd></div>)}</dl></div>
            <div><p className={mutedLabel}>Signal characteristics</p><dl className="mt-3 space-y-2 text-xs">{[["Modulation", reportDetails.modulation], ["Bandwidth", reportDetails.bandwidth], ["SNR", reportDetails.snr], ["FEC / interleaving", "Unknown"]].map(([label, value]) => <div key={label} className="flex justify-between gap-3 border-b border-zinc-900 pb-2"><dt className="text-zinc-500">{label}</dt><dd className="text-zinc-200">{value}</dd></div>)}</dl></div>
          </div>
          <div className="mt-5 border-t border-zinc-800 pt-4"><p className={mutedLabel}>Included sections</p><div className="mt-3 flex flex-wrap gap-2">{['Recording details', 'Signal events', 'Classification & uncertainty', 'Demodulation & FEC status', 'Analyst notes', 'Visual diagnostics', 'Method limitations'].map((item) => <span key={item} className="border border-zinc-800 bg-zinc-950 px-2.5 py-1.5 text-[10px] text-zinc-400">{item}</span>)}</div><p className="mt-4 font-sans text-[11px] leading-relaxed text-zinc-500">The PDF includes spectrum, waterfall, waveform and constellation illustrations. Preview plots and sample rows are clearly marked; measurements that are unavailable remain labeled as such.</p></div>
        </section>
      )}
    </section>
  );
}
