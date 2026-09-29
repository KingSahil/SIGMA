'use client';

import React, { useState } from 'react';
import { Activity, Blocks, Check, Copy, Fingerprint, LockKeyhole, Radio, ShieldCheck, Wallet } from 'lucide-react';
import { SignalMetadata, SpectralAnalysisResult } from '../../lib/dsp-types';
import { SigmaRecoveryResult } from '../../lib/sigma-api';

interface BlockchainFingerprintWorkspaceProps {
  capture: File | null;
  metadata: SignalMetadata | null;
  spectralData: SpectralAnalysisResult | null;
  apiResult: SigmaRecoveryResult | null;
}

export function BlockchainFingerprintWorkspace({ capture, metadata, spectralData, apiResult }: BlockchainFingerprintWorkspaceProps) {
  const [fingerprint, setFingerprint] = useState('');
  const [fingerprintError, setFingerprintError] = useState('');
  const [isHashing, setIsHashing] = useState(false);
  const [copied, setCopied] = useState(false);

  const createFingerprint = async () => {
    if (!capture || !globalThis.crypto?.subtle) return;
    setIsHashing(true);
    setFingerprintError('');
    try {
      const digest = await crypto.subtle.digest('SHA-256', await capture.arrayBuffer());
      setFingerprint(Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join(''));
    } catch {
      setFingerprintError('The browser could not read this capture. Try selecting the file again.');
    } finally {
      setIsHashing(false);
    }
  };

  const copyFingerprint = async () => {
    if (!fingerprint) return;
    try {
      await navigator.clipboard.writeText(`0x${fingerprint}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setFingerprintError('Clipboard access is unavailable in this browser.');
    }
  };

  const shortHash = fingerprint ? `0x${fingerprint.slice(0, 16)}…${fingerprint.slice(-12)}` : 'Generate a capture fingerprint';

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-4 border-b border-zinc-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-400">Integrity registry · UI preview</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">Signal fingerprinting</h2>
          <p className="mt-1 max-w-2xl font-sans text-sm text-zinc-400">Review a signal feature fingerprint, compare similar observations, and preview its blockchain integrity record.</p>
        </div>
        <div className="flex items-center gap-2 border border-amber-900/60 bg-amber-950/20 px-3 py-2 text-[10px] uppercase tracking-wider text-amber-300">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" /> Wallet not connected · no chain writes
        </div>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.75fr)]">
        <div className="space-y-5">
          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3"><div className="border border-cyan-900/70 bg-cyan-950/30 p-2 text-cyan-300"><Fingerprint className="h-4 w-4" /></div><div><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Capture integrity digest</p><h3 className="mt-1 text-sm font-semibold text-white">Generate a verifiable file identity</h3></div></div>
              <span className="border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400">SHA-256</span>
            </div>
            <div className="mt-5 border border-zinc-800 bg-zinc-950 p-3 sm:p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0"><p className="text-[10px] uppercase tracking-wider text-zinc-500">Selected capture</p><p className="mt-1 truncate text-xs text-zinc-200">{metadata?.name ?? capture?.name ?? 'No capture loaded'}</p></div>
                <span className={`border px-2 py-1 text-[10px] ${capture ? 'border-emerald-900/70 text-emerald-300' : 'border-zinc-800 text-zinc-500'}`}>{capture ? 'READY' : 'WAITING FOR CAPTURE'}</span>
              </div>
              <div className="mt-4 grid gap-3 border-t border-zinc-800 pt-3 sm:grid-cols-3">
                <div><p className="text-[9px] uppercase tracking-wider text-zinc-600">Sample rate</p><p className="mt-1 text-xs text-zinc-300">{metadata?.sampleRateHz ? `${(metadata.sampleRateHz / 1e6).toFixed(3)} MS/s` : '—'}</p></div>
                <div><p className="text-[9px] uppercase tracking-wider text-zinc-600">Center frequency</p><p className="mt-1 text-xs text-zinc-300">{metadata?.centerFreqHz ? `${(metadata.centerFreqHz / 1e6).toFixed(3)} MHz` : '—'}</p></div>
                <div><p className="text-[9px] uppercase tracking-wider text-zinc-600">Capture size</p><p className="mt-1 text-xs text-zinc-300">{capture ? `${(capture.size / 1024 / 1024).toFixed(2)} MB` : '—'}</p></div>
              </div>
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <button type="button" onClick={createFingerprint} disabled={!capture || isHashing} className="inline-flex items-center justify-center gap-2 bg-cyan-400 px-4 py-2.5 text-xs font-semibold text-black transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"><Activity className={`h-3.5 w-3.5 ${isHashing ? 'animate-pulse' : ''}`} />{isHashing ? 'HASHING CAPTURE…' : fingerprint ? 'REGENERATE FINGERPRINT' : 'GENERATE FINGERPRINT'}</button>
              <button type="button" onClick={copyFingerprint} disabled={!fingerprint} className="inline-flex items-center justify-center gap-2 border border-zinc-700 px-4 py-2.5 text-xs text-zinc-300 hover:border-zinc-500 disabled:cursor-not-allowed disabled:text-zinc-600">{copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}{copied ? 'COPIED' : 'COPY HASH'}</button>
            </div>
            {fingerprintError && <p role="alert" className="mt-3 text-xs text-rose-300">{fingerprintError}</p>}
            {fingerprint && <div className="mt-4 border border-cyan-950 bg-cyan-950/20 p-3"><p className="text-[9px] uppercase tracking-[0.14em] text-cyan-500">Capture SHA-256 · computed in this browser</p><p className="mt-2 break-all font-mono text-xs leading-relaxed text-cyan-100">0x{fingerprint}</p></div>}
            <p className="mt-3 font-sans text-[11px] leading-relaxed text-zinc-500">This file hash confirms byte-for-byte capture integrity. A signal fingerprint is the measured feature profile below; the two serve different purposes.</p>
          </section>

          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Signal object · feature fingerprint</p><h3 className="mt-1 text-sm font-semibold text-white">Measured characteristics</h3></div><span className="border border-zinc-700 px-2 py-1 text-[9px] text-zinc-500">ANALYZER OUTPUT ONLY</span></div>
            <p className="mt-2 font-sans text-[11px] text-zinc-500">Comparable signal features are shown separately from file identity. Missing measurements stay unknown.</p>
            <dl className="mt-4 grid grid-cols-2 gap-px border border-zinc-800 bg-zinc-800 sm:grid-cols-3">
              {[
                ['Center frequency', metadata?.centerFreqHz ? `${(metadata.centerFreqHz / 1e6).toFixed(3)} MHz` : 'Unknown'],
                ['Bandwidth', spectralData && !metadata?.isPreset ? `${(spectralData.bandwidthMhz * 1000).toFixed(1)} kHz` : 'Unknown'],
                ['SNR', spectralData && !metadata?.isPreset ? `${spectralData.snrDb.toFixed(1)} dB` : apiResult?.signal_metrics?.snr_str ?? 'Unknown'],
                ['Modulation', apiResult?.classification?.modulation ?? (spectralData && !metadata?.isPreset ? spectralData.estimatedModulation : 'Unknown')],
                ['Symbol rate', apiResult?.signal_metrics?.symbol_rate_str ?? 'Unknown'],
                ['Spectral shape', 'Not computed'],
                ['Timing / pulse features', 'Not computed'],
                ['Cyclostationary features', 'Not computed'],
                ['Signal embedding', 'Not computed'],
              ].map(([label, value]) => <div key={label} className="bg-zinc-950 p-3"><dt className="text-[9px] uppercase tracking-wider text-zinc-600">{label}</dt><dd className={`mt-1 text-xs ${value === 'Unknown' || value === 'Not computed' ? 'text-zinc-600' : 'text-zinc-200'}`}>{value}</dd></div>)}
            </dl>
            <div className="mt-4 flex items-start gap-2 border border-amber-950/70 bg-amber-950/10 p-3 font-sans text-[11px] leading-relaxed text-amber-200/80"><Activity className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />Signal embeddings, a historical vector index, and similarity scores are not connected, so no match or fingerprint vector is fabricated here.</div>
          </section>

          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3"><div><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Anchor record</p><h3 className="mt-1 text-sm font-semibold text-white">Blockchain transaction preview</h3></div><span className="border border-amber-900/60 bg-amber-950/20 px-2 py-1 text-[9px] uppercase tracking-wider text-amber-300">Not submitted</span></div>
            <div className="mt-4 divide-y divide-zinc-800 border-y border-zinc-800">
              {[["Network", 'No network selected'], ["Record", fingerprint ? shortHash : 'Fingerprint required'], ["Storage", 'Hash and capture metadata only'], ["Transaction", 'Waiting for wallet connection']].map(([label, value]) => <div key={label} className="grid grid-cols-[100px_1fr] gap-3 py-3 text-xs sm:grid-cols-[130px_1fr]"><span className="text-zinc-500">{label}</span><span className="break-all text-zinc-300">{value}</span></div>)}
            </div>
            <button type="button" disabled className="mt-4 inline-flex cursor-not-allowed items-center gap-2 border border-zinc-800 px-4 py-2.5 text-xs text-zinc-600"><Wallet className="h-3.5 w-3.5" /> CONNECT WALLET TO ANCHOR</button>
            <p className="mt-3 font-sans text-[11px] text-zinc-600">This screen is a frontend preview. Wallet connection, network selection, and transaction submission are not implemented.</p>
          </section>
        </div>

        <aside className="space-y-5">
          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
            <div className="flex items-center justify-between gap-2"><div><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Signal similarity</p><h3 className="mt-1 text-sm font-semibold text-white">Historical matches</h3></div><span className="text-[9px] text-zinc-600">VECTOR SEARCH OFFLINE</span></div>
            <div className="mt-4 border border-dashed border-zinc-800 bg-zinc-950 px-3 py-5 text-center"><Fingerprint className="mx-auto h-4 w-4 text-zinc-600" /><p className="mt-2 text-xs text-zinc-400">No similarity results</p><p className="mt-1 font-sans text-[11px] text-zinc-600">A signal embedding model and historical index are needed to find related observations.</p></div>
            <p className="mt-3 font-sans text-[10px] leading-relaxed text-zinc-600">Similar signal features do not prove the same transmitter or source.</p>
          </section>
          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
            <div className="flex items-center gap-2"><Blocks className="h-4 w-4 text-cyan-400" /><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Registry status</p></div>
            <div className="mt-4 border border-dashed border-zinc-800 bg-zinc-950 px-4 py-8 text-center"><LockKeyhole className="mx-auto h-5 w-5 text-zinc-600" /><p className="mt-3 text-xs font-medium text-zinc-300">No wallet session</p><p className="mt-1 font-sans text-[11px] text-zinc-600">Connect a wallet in a future integration to view on-chain records.</p></div>
            <div className="mt-4 grid grid-cols-2 gap-2"><div className="border border-zinc-800 bg-zinc-950 p-3"><p className="text-[9px] uppercase text-zinc-600">Anchored captures</p><p className="mt-1 text-lg font-semibold text-zinc-300">—</p></div><div className="border border-zinc-800 bg-zinc-950 p-3"><p className="text-[9px] uppercase text-zinc-600">Network</p><p className="mt-1 text-xs font-semibold text-zinc-300">Unselected</p></div></div>
          </section>
          <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
            <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" /><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Integrity workflow</p></div>
            <ol className="mt-4 space-y-4">
              {[["01", "Select capture", "Use the IQ or WAV loaded in the workbench."], ["02", "Fingerprint locally", "Calculate a SHA-256 digest in the browser."], ["03", "Anchor when connected", "A future wallet integration can submit the hash."], ["04", "Verify later", "Compare a fresh digest with the registry record."]].map(([number, title, description], index) => <li key={number} className="flex gap-3"><span className={`flex h-6 w-6 shrink-0 items-center justify-center border text-[9px] ${index === 0 ? 'border-cyan-900 text-cyan-300' : 'border-zinc-800 text-zinc-600'}`}>{number}</span><div><p className="text-xs text-zinc-300">{title}</p><p className="mt-1 font-sans text-[11px] leading-relaxed text-zinc-600">{description}</p></div></li>)}
            </ol>
          </section>
          <p className="flex items-start gap-2 border border-zinc-800 bg-zinc-950 p-3 font-sans text-[11px] leading-relaxed text-zinc-500"><Radio className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-600" />Only the digest should be written to a public chain. Keep capture files and sensitive metadata off-chain.</p>
        </aside>
      </div>
    </section>
  );
}
