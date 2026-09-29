'use client';

import { useState } from 'react';
import { Download, LoaderCircle, Radio, Sparkles } from 'lucide-react';
import { generateSignal } from '../../lib/sigma-api';

export function SignalGeneratorPanel() {
  const [modulation, setModulation] = useState('QPSK');
  const [sampleRate, setSampleRate] = useState(1000000);
  const [snr, setSnr] = useState(18);
  const [cfo, setCfo] = useState(0);
  const [phase, setPhase] = useState(0);
  const [samplesPerSymbol, setSamplesPerSymbol] = useState(4);
  const [state, setState] = useState<'idle' | 'running' | 'ready' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [payload, setPayload] = useState<{ samples_i: number[]; samples_q: number[]; total_bits: number; total_samples: number } | null>(null);

  const run = async () => {
    setState('running'); setMessage(''); setPayload(null);
    try {
      const result = await generateSignal({ modulation, sps: samplesPerSymbol, snr_db: snr, cfo_hz: cfo, phase_offset_deg: phase, samp_rate: sampleRate });
      setPayload(result); setState('ready');
      setMessage(result.total_samples > result.samples_i.length ? `API returned ${result.samples_i.length} of ${result.total_samples} IQ samples. Download is limited to this returned preview.` : `${result.total_bits} bits · ${result.total_samples} generated samples`);
    } catch (error) {
      setState('error'); setMessage(error instanceof Error ? error.message : 'Signal generation failed. Check the SIGMA API connection.');
    }
  };

  const download = () => {
    if (!payload) return;
    const buffer = new ArrayBuffer(payload.samples_i.length * 8);
    const view = new DataView(buffer);
    for (let index = 0; index < payload.samples_i.length; index++) {
      view.setFloat32(index * 8, payload.samples_i[index], true);
      view.setFloat32(index * 8 + 4, payload.samples_q[index], true);
    }
    const url = URL.createObjectURL(new Blob([buffer], { type: 'application/octet-stream' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `synthetic-${modulation.toLowerCase()}.iq`; anchor.click(); URL.revokeObjectURL(url);
  };

  return (
    <details className="mt-5 border border-zinc-800 bg-zinc-950">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-xs font-medium text-zinc-200"><Sparkles className="h-3.5 w-3.5 text-cyan-400" />Generate a synthetic IQ sample<span className="ml-auto text-[10px] text-zinc-600">SIGMA API</span></summary>
      <div className="border-t border-zinc-800 p-4">
        <p className="mb-4 text-[11px] text-zinc-500">Configure modulation and channel impairments. This creates test data, not a trained model prediction.</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-[11px] text-zinc-500">Modulation<select value={modulation} onChange={(e) => setModulation(e.target.value)} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white">{['BPSK', 'QPSK', '8PSK', '16QAM', 'BFSK', '4FSK'].map((name) => <option key={name}>{name}</option>)}</select></label>
          <label className="text-[11px] text-zinc-500">Sample rate (S/s)<input type="number" min="1000" value={sampleRate} onChange={(e) => setSampleRate(Number(e.target.value) || 1000)} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white" /></label>
          <label className="text-[11px] text-zinc-500">Samples per symbol<input type="number" min="1" max="32" value={samplesPerSymbol} onChange={(e) => setSamplesPerSymbol(Math.min(32, Math.max(1, Number(e.target.value) || 1)))} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white" /></label>
          <label className="text-[11px] text-zinc-500">SNR (dB)<input type="number" min="-20" max="60" value={snr} onChange={(e) => setSnr(Number(e.target.value))} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white" /></label>
          <label className="text-[11px] text-zinc-500">Carrier offset (Hz)<input type="number" value={cfo} onChange={(e) => setCfo(Number(e.target.value))} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white" /></label>
          <label className="text-[11px] text-zinc-500">Phase offset (°)<input type="number" value={phase} onChange={(e) => setPhase(Number(e.target.value))} className="mt-1 w-full border border-zinc-700 bg-zinc-900 px-2.5 py-2 text-xs text-white" /></label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2"><button type="button" onClick={() => void run()} disabled={state === 'running'} className="flex items-center gap-2 bg-zinc-100 px-3 py-2 text-xs font-semibold text-black hover:bg-white disabled:opacity-50">{state === 'running' ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Radio className="h-3.5 w-3.5" />}Generate IQ</button>{payload && <button type="button" onClick={download} className="flex items-center gap-2 border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:border-zinc-500"><Download className="h-3.5 w-3.5" />Download .iq</button>}</div>
        {message && <p role={state === 'error' ? 'alert' : 'status'} className={`mt-3 text-xs ${state === 'error' ? 'text-rose-300' : 'text-zinc-400'}`}>{message}</p>}
      </div>
    </details>
  );
}
