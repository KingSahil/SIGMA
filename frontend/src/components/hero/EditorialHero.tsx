'use client';

import React from 'react';
import { ArrowRight, Terminal, Radio, Play, ChevronRight } from 'lucide-react';
import { InstrumentSpectrum } from '../visualizers/InstrumentSpectrum';
import { InstrumentWaterfall } from '../visualizers/InstrumentWaterfall';
import { InstrumentConstellation } from '../visualizers/InstrumentConstellation';
import { useSignal } from '../../context/SignalContext';

interface EditorialHeroProps {
  onOpenWorkbench: () => void;
  onOpenIngest: () => void;
}

export function EditorialHero({
  onOpenWorkbench,
  onOpenIngest,
}: EditorialHeroProps) {
  const { metadata, spectralData, loadPreset } = useSignal();

  return (
    <section className="relative w-full border-b border-zinc-800/80 bg-[#09090b]">
      {/* Top Section Metadata Bar */}
      <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center justify-between text-[11px] font-mono text-zinc-500 border-b border-zinc-800/50">
        <div className="flex items-center gap-3">
          <span className="text-zinc-300">00 // SIGNAL ANALYSIS PLATFORM</span>
          <span>·</span>
          <span>COMPLEX QUADRATURE PROCESSING</span>
        </div>
        <div className="hidden sm:flex items-center gap-4">
          <span>LATENCY: 1.4ms</span>
          <span>·</span>
          <span>PRECISION: IEEE-754 FP32</span>
          <span>·</span>
          <span className="text-cyan-400">FRAME SYNC: LOCKED</span>
        </div>
      </div>

      {/* Main Asymmetric Grid */}
      <div className="max-w-7xl mx-auto px-6 py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-start">
        {/* Left Column: Editorial Typography (5 cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between space-y-8">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 border border-zinc-800 bg-zinc-900/60 text-[10px] font-mono tracking-widest text-zinc-400 uppercase">
              <span className="w-1.5 h-1.5 bg-cyan-400" />
              <span>RF DIGITAL COMMUNICATIONS FORENSICS</span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl font-bold tracking-tight text-white leading-[1.08]">
              From raw quadrature to recovered bitstream.
            </h1>

            <p className="text-sm sm:text-base text-zinc-400 leading-relaxed max-w-md font-sans font-normal">
              An open-architecture signal processing workbench engineered for RF surveillance,
              satellite telemetry analysis, and blind digital demodulation. Ingests raw <code className="text-zinc-200 bg-zinc-900 px-1 py-0.5 text-xs font-mono">.IQ</code> and{' '}
              <code className="text-zinc-200 bg-zinc-900 px-1 py-0.5 text-xs font-mono">.WAV</code> captures to extract spectral parameters, de-interleave framing matrices, and decode error-corrected payloads.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={onOpenWorkbench}
              className="flex items-center gap-2.5 px-5 py-3 bg-zinc-100 hover:bg-white text-black text-xs font-mono font-semibold tracking-wide transition-all cursor-pointer"
            >
              <span>LAUNCH LAB WORKBENCH</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onOpenIngest}
              className="flex items-center gap-2 px-4 py-3 border border-zinc-700 hover:border-zinc-500 bg-zinc-900/40 text-zinc-300 hover:text-white text-xs font-mono transition-all cursor-pointer"
            >
              <Radio className="w-3.5 h-3.5 text-cyan-400" />
              <span>LOAD CAPTURE</span>
            </button>
          </div>

          {/* Quick Technical Matrix Breakdown */}
          <div className="grid grid-cols-3 gap-0 border border-zinc-800 divide-x divide-zinc-800 text-[11px] font-mono pt-1 bg-zinc-950/40">
            <div className="p-3">
              <div className="text-zinc-500 text-[9px] uppercase">MODULATION</div>
              <div className="font-semibold text-zinc-200 mt-0.5">FSK / PSK / QAM</div>
            </div>
            <div className="p-3">
              <div className="text-zinc-500 text-[9px] uppercase">DE-INTERLEAVE</div>
              <div className="font-semibold text-zinc-200 mt-0.5">4 ALGORITHMS</div>
            </div>
            <div className="p-3">
              <div className="text-zinc-500 text-[9px] uppercase">FEC DECODER</div>
              <div className="font-semibold text-cyan-400 mt-0.5">VITERBI + RS</div>
            </div>
          </div>
        </div>

        {/* Right Column: Instrument Rack (7 cols) */}
        <div className="lg:col-span-7 border border-zinc-800 bg-[#0c0c0e] shadow-2xl">
          {/* Instrument Rack Header */}
          <div className="h-10 px-4 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between font-mono text-[11px]">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 bg-emerald-500 inline-block" />
              <span className="text-zinc-300 font-semibold uppercase">
                {metadata?.name || 'CubeSat Telemetry (433.92 MHz)'}
              </span>
              <span className="text-zinc-500">[{metadata?.format || '.IQ'}]</span>
            </div>

            <div className="flex items-center gap-3 text-zinc-400 text-[10px]">
              <span>FS: 2.4 MSPS</span>
              <span>·</span>
              <span className="text-cyan-400">SNR: 18.4 dB</span>
            </div>
          </div>

          {/* Instrument Screen Content */}
          <div className="p-4 space-y-4">
            {/* Top: Spectrum Analyzer */}
            <div className="h-48">
              <InstrumentSpectrum
                carrierMhz={metadata?.centerFreqHz ? metadata.centerFreqHz / 1e6 : 433.92}
                bandwidthMhz={spectralData?.bandwidthMhz || 1.8}
                snrDb={spectralData?.snrDb || 18.4}
              />
            </div>

            {/* Middle: Real-time Waterfall Spectrogram */}
            <div className="h-36">
              <InstrumentWaterfall />
            </div>

            {/* Bottom Row: Constellation Scope + Telemetry Register */}
            <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 pt-1">
              <div className="sm:col-span-5 h-38">
                <InstrumentConstellation modulation={spectralData?.estimatedModulation || 'QPSK'} />
              </div>

              {/* Right Side: Telemetry Register */}
              <div className="sm:col-span-7 border border-zinc-800 bg-[#09090b] p-3 font-mono text-[11px] flex flex-col justify-between">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-1.5 text-zinc-400">
                  <span className="uppercase text-[9px] tracking-wider text-zinc-500">{'// 04 PARAMETER TELEMETRY'}</span>
                  <span className="text-emerald-400 text-[10px]">AUTO-ESTIMATED</span>
                </div>

                <div className="grid grid-cols-2 gap-y-2 text-[10px] py-2 text-zinc-300">
                  <div>
                    <span className="text-zinc-500 block">EST. MODULATION:</span>
                    <span className="font-semibold text-white">QPSK (M=4)</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">CARRIER OFFSET:</span>
                    <span className="font-semibold text-cyan-400">+1.24 kHz</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">SYMBOL RATE:</span>
                    <span className="font-semibold text-white">1.20 MBaud</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">ROLL-OFF FACTOR:</span>
                    <span className="font-semibold text-white">0.35 RRC</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-zinc-400">STATUS: READY TO DEMODULATE</span>
                  <button
                    onClick={onOpenWorkbench}
                    className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold cursor-pointer"
                  >
                    <span>STEP INTO PIPELINE</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
