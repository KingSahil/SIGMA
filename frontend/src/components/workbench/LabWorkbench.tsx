'use client';

import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Activity,
  Radio,
  Cpu,
  Layers,
  FileCheck2,
  FileCode2,
  Play,
  Download,
  Copy,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';
import { useSignal } from '../../context/SignalContext';
import { InstrumentSpectrum } from '../visualizers/InstrumentSpectrum';
import { InstrumentWaterfall } from '../visualizers/InstrumentWaterfall';
import { InstrumentConstellation } from '../visualizers/InstrumentConstellation';
import { IngestionModal } from '../modules/IngestionModal';
import { IntelligenceWorkspace } from './IntelligenceWorkspace';
import { HammingDemo } from './HammingDemo';
import { ErrorControlLab } from './ErrorControlLab';
import { ModulationType, DeinterleaveMethod, FecCodeType, PipelineStage } from '../../lib/dsp-types';
import { downloadDossierPdf } from '../../lib/dossier-pdf';
import { checkSigmaHealth } from '../../lib/sigma-api';
import { PdfComparison } from './PdfComparison';

interface LabWorkbenchProps {
  onBackToOverview: () => void;
}

export function LabWorkbench({ onBackToOverview }: LabWorkbenchProps) {
  const {
    apiStatus,
    stage,
    setStage,
    metadata,
    uploadedFile,
    apiResult,
    apiPlots,
    apiBusy,
    apiError,
    spectralData,
    waterfallFrames,
    demodData,
    selectedModulation,
    setSelectedModulation,
    runDemodulation,
    deinterleaveData,
    selectedDeintMethod,
    setSelectedDeintMethod,
    deintRows,
    setDeintRows,
    deintCols,
    setDeintCols,
    runDeinterleave,
    fecData,
    selectedFecCode,
    setSelectedFecCode,
    runFec,
    correlationData,
    runCorrelation,
    runFullPipeline,
  } = useSignal();

  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<'analysis' | 'intelligence' | 'error-control' | 'comparison'>('analysis');

  const pipelineStages = [
    { id: 'spectral', label: 'SPECTRAL ANALYSIS', icon: Activity },
    { id: 'demod', label: 'DEMODULATION', icon: Cpu },
    { id: 'deinterleave', label: 'DE-INTERLEAVING', icon: Layers },
    { id: 'fec', label: 'FEC DECODING', icon: FileCheck2 },
    { id: 'correlate', label: 'FRAME CORRELATION', icon: FileCode2 },
  ] as const;

  const activeStage = ['spectral', 'demod', 'deinterleave', 'fec', 'correlate'].includes(stage)
    ? stage
    : 'spectral';

  useEffect(() => {
    if (!['spectral', 'demod', 'deinterleave', 'fec', 'correlate'].includes(stage)) {
      setStage('spectral');
    }
  }, [stage, setStage]);

  const handleRunAll = async () => {
    setIsPipelineRunning(true);
    setPipelineError(null);
    try {
      await runFullPipeline();
    } catch (error) {
      setPipelineError(error instanceof Error ? error.message : 'Pipeline execution failed');
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#EDEDED] flex flex-col font-mono text-xs selection:bg-zinc-800 selection:text-white">
      {/* Top Engineering Telemetry Bar */}
      <header className="sticky top-0 z-40 flex min-h-14 flex-wrap items-center justify-between gap-2 border-b border-zinc-800 bg-[#0c0c0e] px-3 py-2 sm:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onBackToOverview}
            className="flex items-center gap-2 px-3 py-1.5 border border-zinc-800 hover:border-zinc-700 bg-zinc-900/60 text-xs text-zinc-300 hover:text-white transition-all cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>OVERVIEW</span>
          </button>

          <div className="h-4 w-[1px] bg-zinc-800" />

          <div className="flex items-center gap-3">
            <span className="w-2 h-2 bg-emerald-400 rotate-45" />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-white text-sm tracking-tight">
                  SIGNALFORGE LAB
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center/Right Controls */}
        <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
          {/* Target Capture Indicator */}
          <div className="hidden xl:flex min-w-0 max-w-64 items-center gap-2 px-3 py-1 border border-zinc-800 bg-zinc-950 text-[11px] text-zinc-400">
            <span className="text-zinc-500">CAPTURE:</span>
            <span className="truncate text-zinc-200 font-semibold">{metadata?.name}</span>
            <span className="text-cyan-400">
              ({metadata?.centerFreqHz ? (metadata.centerFreqHz / 1e6).toFixed(2) : '433.92'} MHz)
            </span>
          </div>

          <div className="flex items-center gap-2 border border-zinc-800 bg-zinc-950 px-2.5 py-1 text-[10px] text-zinc-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            {apiStatus === 'checking' ? 'API CHECKING' : apiStatus === 'connected' ? 'FASTAPI · CONNECTED' : 'FASTAPI · OFFLINE'}
            <span className={`h-1.5 w-1.5 rounded-full ${apiOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            {apiOnline ? 'SIGMA API CONNECTED' : uploadedFile ? 'API OFFLINE' : 'SAMPLE PREVIEW'}
          </div>

          <button
            onClick={() => setIsIngestModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-zinc-800 hover:border-zinc-700 bg-zinc-900/60 text-zinc-300 hover:text-white transition-all cursor-pointer"
          >
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span>SWITCH FILE</span>
          </button>

          <button
            onClick={handleRunAll}
            disabled={isPipelineRunning}
            className="flex items-center gap-2 px-4 py-1.5 bg-zinc-100 hover:bg-white text-black font-semibold tracking-wider transition-all cursor-pointer disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-black ${isPipelineRunning ? 'animate-spin' : ''}`} />
            <span>{isPipelineRunning ? 'PROCESSING...' : 'RUN PIPELINE'}</span>
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 bg-zinc-950/80 px-3 py-2.5 sm:px-6">
        <div className="flex items-center gap-2 text-[11px] text-amber-300">
          <span className={`h-1.5 w-1.5 rounded-full ${apiOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          {apiOnline ? 'Analysis API connected · upload a capture to run it' : 'Sample preview · connect the SIGMA API to analyze uploaded captures'}
        </div>
        {pipelineError && <div className="border border-red-900/60 bg-red-950/30 px-3 py-1.5 text-[11px] text-red-300">{pipelineError}</div>}
        <nav className="flex flex-wrap gap-1" aria-label="Workbench areas">
          <button type="button" onClick={() => setWorkspace('analysis')} aria-current={workspace === 'analysis' ? 'page' : undefined} className={`px-3 py-1.5 text-xs ${workspace === 'analysis' ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>Signal analysis</button>
          <button type="button" onClick={() => setWorkspace('intelligence')} aria-current={workspace === 'intelligence' ? 'page' : undefined} className={`px-3 py-1.5 text-xs ${workspace === 'intelligence' ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>Signal intelligence</button>
          <button type="button" onClick={() => setWorkspace('error-control')} aria-current={workspace === 'error-control' ? 'page' : undefined} className={`px-3 py-1.5 text-xs ${workspace === 'error-control' ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>Error control lab</button>
          <button type="button" onClick={() => setWorkspace('comparison')} aria-current={workspace === 'comparison' ? 'page' : undefined} className={`px-3 py-1.5 text-xs ${workspace === 'comparison' ? 'bg-zinc-800 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>Compare PDF</button>
        </nav>
      </div>

      {/* Pipeline Navigation Bar */}
      {workspace === 'analysis' && <nav className="flex items-center gap-0 overflow-x-auto border-b border-zinc-800 bg-[#09090b] px-2 sm:px-6">
        {pipelineStages.map((st) => {
          const Icon = st.icon;
          const isActive = activeStage === st.id;
          return (
            <button
              key={st.id}
              onClick={() => setStage(st.id as PipelineStage)}
              className={`flex items-center gap-2 py-3 px-5 border-b-2 transition-all cursor-pointer whitespace-nowrap text-xs ${
                isActive
                  ? 'border-cyan-400 text-white bg-zinc-900/40 font-bold'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/20'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-zinc-500'}`} />
              <span>{st.label}</span>
            </button>
          );
        })}
      </nav>}

      {/* Main Lab Screen Area */}
      <main className="mx-auto w-full min-w-0 max-w-7xl flex-1 space-y-6 p-3 sm:p-6">
        {workspace === 'intelligence' ? (
          <IntelligenceWorkspace metadata={metadata} spectralData={spectralData} apiResult={apiResult} apiPlots={apiPlots} />
        ) : workspace === 'error-control' ? (
          <ErrorControlLab />
        ) : workspace === 'comparison' ? (
          <PdfComparison result={apiResult} metadata={metadata} />
        ) : <>
        {uploadedFile ? (
          <div className="space-y-5">
            <section className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-800 pb-4">
                <div><p className="text-[10px] uppercase tracking-[0.14em] text-cyan-400">Uploaded capture · SIGMA recovery API</p><h2 className="mt-1 text-base font-semibold text-white">{metadata?.name}</h2><p className="mt-1 text-xs text-zinc-500">{metadata?.format} · {((metadata?.sizeBytes ?? 0) / (1024 * 1024)).toFixed(1)} MB · {metadata?.sampleRateHz.toLocaleString()} samples/s</p></div>
                <button type="button" onClick={handleRunAll} disabled={apiBusy} className="flex items-center gap-2 bg-zinc-100 px-4 py-2 text-xs font-semibold text-black hover:bg-white disabled:opacity-50"><Play className={`h-3.5 w-3.5 ${apiBusy ? 'animate-pulse' : 'fill-black'}`} />{apiBusy ? 'ANALYZING…' : apiResult ? 'RUN AGAIN' : 'RUN ANALYSIS'}</button>
              </div>
              {apiBusy && <div className="mt-4 flex items-center gap-2 text-xs text-cyan-300"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />Uploading capture and running DSP recovery…</div>}
              {apiError && <p role="alert" className="mt-4 border border-rose-900/70 bg-rose-950/20 p-3 text-xs text-rose-300">{apiError}</p>}
              {!apiResult && !apiBusy && !apiError && <p className="mt-4 text-xs text-zinc-500">Run analysis to send this capture to the connected SIGMA API. Measurements appear here when processing completes.</p>}
              {apiResult && <>
                <div className="mt-5 grid gap-px border border-zinc-800 bg-zinc-800 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    ['Modulation', apiResult.classification?.modulation ?? 'Not classified'],
                    ['SNR', apiResult.signal_metrics?.snr_str ?? 'Not available'],
                    ['Symbol rate', apiResult.signal_metrics?.symbol_rate_str ?? 'Not available'],
                    ['Status', apiResult.overall_status ?? 'Completed'],
                  ].map(([label, value]) => <div key={label} className="bg-zinc-950 p-3"><span className="block text-[10px] uppercase text-zinc-500">{label}</span><span className="mt-1 block text-sm font-semibold text-zinc-100">{value}</span></div>)}
                </div>
                <div className="mt-5 grid gap-5 lg:grid-cols-2">
                  <div className="border border-zinc-800 bg-zinc-950 p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500">Recovery stages</p><dl className="mt-3 space-y-2 text-xs">{[
                    ['Demodulation', apiResult.recovery?.demodulation_status ?? 'Not returned'],
                    ['De-interleaving', apiResult.deinterleaving?.status ?? 'Not returned'],
                    ['FEC', apiResult.fec?.status ?? 'Not returned'],
                    ['Correlation', apiResult.correlation?.status ?? 'Not returned'],
                  ].map(([label, value]) => <div key={label} className="flex justify-between gap-3 border-b border-zinc-900 pb-2"><dt className="text-zinc-500">{label}</dt><dd className="text-zinc-200">{value}</dd></div>)}</dl><p className="mt-3 text-[10px] text-zinc-600">Modulation output is the analyzer’s classification evidence; no CNN probability scores are returned.</p></div>
                  <div className="border border-zinc-800 bg-zinc-950 p-4"><p className="text-[10px] uppercase tracking-wider text-zinc-500">Recovered bit preview</p><pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-emerald-300">{apiResult.fec?.output_bits?.length ? apiResult.fec.output_bits.slice(0, 512).join('') : apiResult.recovery?.bits?.length ? apiResult.recovery.bits.slice(0, 512).join('') : 'No recovered bits returned by the pipeline.'}</pre><p className="mt-3 text-[10px] text-zinc-600">{apiResult.fec?.output_bits?.length ? `Showing ${Math.min(512, apiResult.fec.output_bits.length)} of ${apiResult.fec.output_bits.length} FEC output bits.` : apiResult.recovery?.bits?.length ? `Showing ${Math.min(512, apiResult.recovery.bits.length)} of ${apiResult.recovery.bits.length} demodulated bits.` : 'Bit recovery was not established for this capture.'}</p></div>
                </div>
              </>}
            </section>
            {apiPlots ? <div className="grid gap-5 xl:grid-cols-2">
              <div className="h-64 border border-zinc-800 bg-[#0c0c0e] p-4"><InstrumentSpectrum carrierMhz={(metadata?.centerFreqHz ?? 0) / 1e6} spanMhz={(metadata?.sampleRateHz ?? 0) / 1e6} spectrumDb={apiPlots.spectrum_db} frequenciesNorm={apiPlots.frequencies_norm} snrDb={apiPlots.snr_db} /></div>
              <div className="h-64 border border-zinc-800 bg-[#0c0c0e] p-4"><InstrumentWaterfall frames={apiPlots.waterfall_db} centerFrequencyMhz={(metadata?.centerFreqHz ?? 0) / 1e6} spanMhz={(metadata?.sampleRateHz ?? 0) / 1e6} /></div>
              <div className="h-64 border border-zinc-800 bg-[#0c0c0e] p-4"><InstrumentConstellation modulation={apiResult?.classification?.modulation ?? 'Unclassified'} points={(apiPlots.constellation_i ?? []).map((i, index) => ({ i, q: apiPlots.constellation_q?.[index] ?? 0 }))} /></div>
            </div> : uploadedFile && apiResult && metadata?.format !== '.iq' ? <p className="border border-zinc-800 bg-zinc-950 px-4 py-3 text-xs text-zinc-500">The current visualization endpoint accepts raw float32 IQ, so plots are not returned for this file type. Recovery results above are from the WAV analysis endpoint.</p> : null}
          </div>
        ) : <>
        {/* STAGE 1: SPECTRAL */}
        {activeStage === 'spectral' && (
          <div className="space-y-6">
            {/* Telemetry Metric Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-5 border border-zinc-800 bg-zinc-950/40 divide-y sm:divide-y-0 sm:divide-x divide-zinc-800 text-[11px]">
              <div className="p-3.5">
                <span className="text-zinc-500 block uppercase">EST. MODULATION</span>
                <span className="text-base font-bold text-cyan-400 mt-0.5 block">
                  {spectralData?.estimatedModulation || 'QPSK'}
                </span>
                <span className="text-[10px] text-zinc-500 mt-0.5 block">Illustrative preview · no CNN result</span>
              </div>
              <div className="p-3.5">
                <span className="text-zinc-500 block uppercase">CARRIER FREQUENCY</span>
                <span className="text-base font-bold text-white mt-0.5 block">
                  {(metadata?.centerFreqHz ? metadata.centerFreqHz / 1e6 : 433.92).toFixed(2)} MHz
                </span>
                <span className="text-[10px] text-zinc-500 mt-0.5 block">Offset: +1.2 kHz</span>
              </div>
              <div className="p-3.5">
                <span className="text-zinc-500 block uppercase">BANDWIDTH (-3dB)</span>
                <span className="text-base font-bold text-white mt-0.5 block">
                  {(spectralData?.bandwidthMhz || 1.8).toFixed(2)} MHz
                </span>
                <span className="text-[10px] text-zinc-500 mt-0.5 block">Nyquist Bound</span>
              </div>
              <div className="p-3.5">
                <span className="text-zinc-500 block uppercase">SIGNAL-TO-NOISE</span>
                <span className="text-base font-bold text-cyan-400 mt-0.5 block">
                  {(spectralData?.snrDb || 18.4).toFixed(1)} dB
                </span>
                <span className="text-[10px] text-zinc-500 mt-0.5 block">Floor: -85 dBFS</span>
              </div>
              <div className="p-3.5">
                <span className="text-zinc-500 block uppercase">SAMPLE RATE</span>
                <span className="text-base font-bold text-white mt-0.5 block">
                  {(metadata?.sampleRateHz ? metadata.sampleRateHz / 1e6 : 2.4).toFixed(1)} MSps
                </span>
                <span className="text-[10px] text-cyan-400 mt-0.5 block">FP32 Complex</span>
              </div>
            </div>

            {/* Split Visualizer: Spectrum + Waterfall + Constellation */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-8 space-y-6">
                <div className="border border-zinc-800 bg-[#0c0c0e] p-4 shadow-sm">
                  <div className="h-56">
                    <InstrumentSpectrum
                      carrierMhz={metadata?.centerFreqHz ? metadata.centerFreqHz / 1e6 : 433.92}
                      bandwidthMhz={spectralData?.bandwidthMhz || 1.8}
                      snrDb={spectralData?.snrDb || 18.4}
                      spanMhz={5}
                    />
                  </div>
                </div>

                <div className="border border-zinc-800 bg-[#0c0c0e] p-4 shadow-sm">
                  <div className="h-44">
                    <InstrumentWaterfall frames={waterfallFrames.map((frame) => frame.bins)} centerFrequencyMhz={(metadata?.centerFreqHz ?? 0) / 1e6} spanMhz={(metadata?.sampleRateHz ?? 0) / 1e6} />
                  </div>
                </div>
              </div>

              <div className="lg:col-span-4 border border-zinc-800 bg-[#0c0c0e] p-4 flex flex-col justify-between space-y-4">
                <div>
                  <div className="h-60 mb-4">
                    <InstrumentConstellation modulation={spectralData?.estimatedModulation || 'QPSK'} />
                  </div>

                  <div className="border border-zinc-800 bg-zinc-950 p-3 space-y-2 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Error Vector Magnitude</span>
                      <span className="text-cyan-400 font-bold">4.82% rms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Phase Jitter</span>
                      <span className="text-white">1.4°</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Pulse Shaping</span>
                      <span className="text-white">RRC (β=0.35)</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => {
                    runDemodulation();
                    setStage('demod');
                  }}
                  className="w-full py-2.5 bg-zinc-100 hover:bg-white text-black font-semibold text-xs transition-all cursor-pointer text-center"
                >
                  PROCEED TO DEMODULATION ➔
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STAGE 2: DEMOD */}
        {activeStage === 'demod' && (
          <div className="border border-zinc-800 bg-[#0c0c0e] p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide uppercase">
                  Symbol Slicing & Carrier Demodulation
                </h3>
                <p className="text-xs text-zinc-500 mt-1 font-sans">
                  Select modulation scheme to slice continuous complex I/Q baseband samples into discrete digital symbols.
                </p>
              </div>

              {/* Modulation Family Selector */}
              <div className="flex items-center gap-1 border border-zinc-800 bg-zinc-950 p-1">
                {(['BPSK', 'QPSK', '8PSK', '16QAM', '2FSK'] as ModulationType[]).map((mod) => (
                  <button
                    key={mod}
                    onClick={() => {
                      setSelectedModulation(mod);
                      runDemodulation(mod);
                    }}
                    className={`px-3 py-1 text-xs font-semibold transition-all cursor-pointer ${
                      selectedModulation === mod
                        ? 'bg-zinc-800 text-white font-bold'
                        : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {mod}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-8 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-400 uppercase font-bold">
                    RECOVERED BITSTREAM ({demodData?.rawBits?.length || 1040} BITS)
                  </span>
                  <button
                    onClick={() => copyToClipboard(demodData?.rawBits || '')}
                    className="flex items-center gap-1.5 px-3 py-1 border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-[11px] text-zinc-300 cursor-pointer"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{copied ? 'COPIED' : 'COPY'}</span>
                  </button>
                </div>

                <div className="p-4 border border-zinc-800 bg-zinc-950 text-xs text-emerald-400 break-all leading-relaxed max-h-60 overflow-y-auto">
                  {demodData?.rawBits ||
                    '101011001101001011001010101011010010101111001010101100101011001011010010101101010100101011110010101011001010110010110100101011010101001010111100101010110010101100101101001010110101'}
                </div>

                <div className="flex items-center justify-between pt-2">
                  <span className="text-zinc-500 text-xs">
                    SYMBOL RATE: <strong className="text-white">1.20 MBaud</strong> | SLICER THRESHOLD: <strong className="text-white">0.00 V</strong>
                  </span>
                  <button
                    onClick={() => {
                      runDeinterleave();
                      setStage('deinterleave');
                    }}
                    className="px-5 py-2 bg-zinc-100 hover:bg-white text-black font-semibold text-xs cursor-pointer"
                  >
                    PROCEED TO DE-INTERLEAVING ➔
                  </button>
                </div>
              </div>

              <div className="lg:col-span-4 border border-zinc-800 bg-zinc-950 p-4">
                <span className="text-xs text-zinc-400 block mb-3 uppercase font-bold">
                  SLICER CONSTELLATION MAP
                </span>
                <div className="h-52">
                  <InstrumentConstellation modulation={selectedModulation} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STAGE 3: DE-INTERLEAVING */}
        {activeStage === 'deinterleave' && (
          <div className="border border-zinc-800 bg-[#0c0c0e] p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide uppercase">
                  Matrix De-interleaving Transformation
                </h3>
                <p className="text-xs text-zinc-500 mt-1 font-sans">
                  Reconstruct burst-dispersed channel permutations by transposing the memory array.
                </p>
              </div>

              {/* Algorithm selector */}
              <div className="flex items-center gap-1 border border-zinc-800 bg-zinc-950 p-1 text-xs">
                {(['block', 'convolution', 'diagonal', 'pseudorandom'] as DeinterleaveMethod[]).map(
                  (m) => (
                    <button
                      key={m}
                      onClick={() => {
                        setSelectedDeintMethod(m);
                        runDeinterleave(m, deintRows, deintCols);
                      }}
                      className={`px-3 py-1 font-semibold uppercase transition-all cursor-pointer ${
                        selectedDeintMethod === m
                          ? 'bg-zinc-800 text-white font-bold'
                          : 'text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      {m}
                    </button>
                  )
                )}
              </div>
            </div>

            {/* Matrix Parameters */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 border border-zinc-800 bg-zinc-950">
              <div>
                <div className="flex justify-between text-xs text-zinc-400 mb-2">
                  <span>MATRIX DEPTH (ROWS): {deintRows}</span>
                  <span className="text-zinc-500">M = {deintRows}</span>
                </div>
                <input
                  type="range"
                  min="4"
                  max="32"
                  step="4"
                  value={deintRows}
                  onChange={(e) => {
                    const r = Number(e.target.value);
                    setDeintRows(r);
                    runDeinterleave(selectedDeintMethod, r, deintCols);
                  }}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-zinc-400 mb-2">
                  <span>MATRIX WIDTH (COLUMNS): {deintCols}</span>
                  <span className="text-zinc-500">N = {deintCols}</span>
                </div>
                <input
                  type="range"
                  min="8"
                  max="64"
                  step="8"
                  value={deintCols}
                  onChange={(e) => {
                    const c = Number(e.target.value);
                    setDeintCols(c);
                    runDeinterleave(selectedDeintMethod, deintRows, c);
                  }}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>
            </div>

            {/* Before vs After Diff View */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>INPUT INTERLEAVED (ROW-WISE)</span>
                  <span>BURST-CORRUPTED</span>
                </div>
                <div className="p-3.5 border border-zinc-800 bg-zinc-950 text-zinc-400 break-all h-36 overflow-y-auto">
                  {deinterleaveData?.beforeBits || demodData?.rawBits?.slice(0, 512)}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs text-cyan-400 font-bold">
                  <span>DE-INTERLEAVED OUTPUT (COLUMN-WISE)</span>
                  <span className="text-emerald-400">DISPERSED</span>
                </div>
                <div className="p-3.5 border border-zinc-700 bg-zinc-950 text-cyan-300 break-all h-36 overflow-y-auto">
                  {deinterleaveData?.afterBits || demodData?.rawBits?.slice(0, 512)}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-zinc-800 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-zinc-500">
                BIT PERMUTATIONS REORDERED:{' '}
                <strong className="text-emerald-400">{deinterleaveData?.bitChangesCount || 248}</strong>
              </span>

              <button
                onClick={() => {
                  runFec();
                  setStage('fec');
                }}
                className="px-5 py-2 bg-zinc-100 hover:bg-white text-black font-semibold text-xs cursor-pointer"
              >
                PROCEED TO FEC DECODING ➔
              </button>
            </div>
          </div>
        )}

        {/* STAGE 4: FEC */}
        {activeStage === 'fec' && (
          <div className="border border-zinc-800 bg-[#0c0c0e] p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide uppercase">
                  Forward Error Correction (FEC) Engine
                </h3>
                <p className="text-xs text-zinc-500 mt-1 font-sans">
                  Syndrome calculation and maximum-likelihood Viterbi / Reed-Solomon polynomial decoding.
                </p>
              </div>

              <div className="flex items-center gap-1 border border-zinc-800 bg-zinc-950 p-1 text-xs">
                {(['viterbi', 'reed-solomon', 'ldpc'] as FecCodeType[]).map((c) => (
                  <button
                    key={c}
                    onClick={() => {
                      setSelectedFecCode(c);
                      runFec(c);
                    }}
                    className={`px-3 py-1 font-semibold uppercase transition-all cursor-pointer ${
                      selectedFecCode === c
                        ? 'bg-zinc-800 text-white font-bold'
                        : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            {/* Diagnostic Scorecard */}
            <div className="grid grid-cols-2 sm:grid-cols-4 border border-zinc-800 bg-zinc-950 divide-y sm:divide-y-0 sm:divide-x divide-zinc-800">
              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">INPUT BITS</span>
                <span className="text-xl font-bold text-white mt-1 block">
                  {fecData?.inputBitsCount || 1024}
                </span>
              </div>
              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">CORRECTED BIT ERRORS</span>
                <span className="text-xl font-bold text-emerald-400 mt-1 block">
                  {fecData?.correctedErrors || 17} bits
                </span>
              </div>
              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">RESIDUAL POST-FEC BER</span>
                <span className="text-xl font-bold text-cyan-400 mt-1 block">
                  {(fecData?.estimatedBer || 0.0134).toFixed(4)}%
                </span>
              </div>
              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">FRAME SYNDROME STATUS</span>
                <span className="text-sm font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>PARITY VALID</span>
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-zinc-800 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-zinc-500">
                DECODER: <strong className="text-white">{fecData?.decoder || 'Soft Viterbi (K=7, R=1/2)'}</strong>
              </span>

              <button
                onClick={() => {
                  runCorrelation();
                  setStage('correlate');
                }}
                className="px-5 py-2 bg-zinc-100 hover:bg-white text-black font-semibold text-xs cursor-pointer"
              >
                PROCEED TO FRAME CORRELATION ➔
              </button>
            </div>
            <HammingDemo />
          </div>
        )}

        {/* STAGE 5: CORRELATION */}
        {activeStage === 'correlate' && (
          <div className="border border-zinc-800 bg-[#0c0c0e] p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide uppercase">
                  Frame Synchronization & Bit Stream Correlation
                </h3>
                <p className="text-xs text-zinc-500 mt-1 font-sans">
                  Detect aerospace/RF sync preambles and extract recovered telemetry payload.
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-zinc-500">PREAMBLE TARGET:</span>
                <span className="font-bold text-cyan-400 px-2.5 py-1 border border-zinc-800 bg-zinc-950">
                  {correlationData?.syncWordHex || '0xACD2'}
                </span>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 border border-zinc-800 bg-zinc-950 divide-y md:divide-y-0 md:divide-x divide-zinc-800">
              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">PEAK MATCH COEFFICIENT</span>
                <span className="text-2xl font-bold text-cyan-400 mt-1 block">
                  {((correlationData?.peakCorrelation || 0.967) * 100).toFixed(1)}%
                </span>
                <span className="text-zinc-500 text-[10px] mt-0.5 block">Offset: Bit index 48</span>
              </div>

              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">DETECTED SYNC HEADER</span>
                <span className="text-lg font-bold text-white mt-1 block font-mono">
                  {correlationData?.detectedHeaderHex || 'AC D2 88 01'}
                </span>
                <span className="text-emerald-400 text-[10px] mt-0.5 block">Barker Alignment Locked</span>
              </div>

              <div className="p-4">
                <span className="text-zinc-500 text-[10px] block uppercase">EXTRACTED PAYLOAD ASCII</span>
                <span className="text-sm font-bold text-emerald-400 mt-1 block font-mono">
                  &quot;{correlationData?.extractedPayloadAscii || 'Hello Satellite Telemetry'}&quot;
                </span>
                <span className="text-zinc-500 text-[10px] mt-0.5 block">25 Bytes Decoded</span>
              </div>
            </div>

            {/* Extracted Payload Hex Stream */}
            <div className="space-y-2">
              <span className="text-zinc-500 uppercase text-xs">
                EXTRACTED PAYLOAD HEX DUMP
              </span>
              <div className="p-4 border border-zinc-800 bg-zinc-950 text-cyan-300 text-xs">
                {correlationData?.extractedPayloadHex ||
                  '48 65 6C 6C 6F 20 53 61 74 65 6C 6C 69 74 65 20 54 65 6C 65 6D 65 74 72 79'}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-zinc-800 pt-4">
              <button
                onClick={() => downloadDossierPdf({
                  fileName: metadata?.name ?? 'signal-analysis.iq',
                  format: metadata?.format ?? '.iq',
                  sampleRate: metadata ? `${(metadata.sampleRateHz / 1e6).toFixed(2)} MS/s` : 'Not provided',
                  centerFrequency: metadata ? `${(metadata.centerFreqHz / 1e6).toFixed(3)} MHz` : 'Not provided',
                  duration: metadata ? `${metadata.durationSeconds.toFixed(2)} s` : 'Not provided',
                  modulation: spectralData?.estimatedModulation ?? 'Unclassified',
                  bandwidth: spectralData ? `${spectralData.bandwidthMhz.toFixed(3)} MHz` : 'Not available',
                  snr: spectralData ? `${spectralData.snrDb.toFixed(1)} dB` : 'Not available',
                  signals: [],
                  isPreview: !uploadedFile,
                  plotData: apiPlots,
                  classificationEvidence: apiResult?.classification?.confidence_evidence,
                  demodulationStatus: apiResult?.recovery?.demodulation_status,
                  deinterleavingStatus: apiResult?.deinterleaving?.status,
                  fecStatus: apiResult?.fec?.status,
                  correlationStatus: apiResult?.correlation?.status,
                  bitCount: apiResult?.fec?.output_bits?.length ?? apiResult?.recovery?.bits?.length,
                })}
                className="flex items-center gap-2 px-5 py-2.5 bg-zinc-100 hover:bg-white text-black font-semibold text-xs transition-all cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>EXPORT MISSION INTELLIGENCE REPORT</span>
              </button>
            </div>
          </div>
        )}
        </>}
        </>}
      </main>

      {/* Ingestion Console Modal */}
      <IngestionModal
        isOpen={isIngestModalOpen}
        onClose={() => setIsIngestModalOpen(false)}
        onLaunchWorkbench={() => {
          setIsIngestModalOpen(false);
          setStage('spectral');
        }}
      />
    </div>
  );
}
