'use client';

import React from 'react';
import { ArrowDown, Check, Binary, Cpu, Layers, ShieldCheck, Search } from 'lucide-react';

interface PipelineFlowProps {
  onSelectStage: (stage: string) => void;
}

export function PipelineFlow({ onSelectStage }: PipelineFlowProps) {
  const stages = [
    {
      num: '01',
      id: 'ingest',
      title: 'QUADRATURE INGESTION',
      subtitle: 'IEEE-754 32-bit Complex Float & Baseband Audio',
      formula: 's(t) = I(t)·cos(2πf_c t) - Q(t)·sin(2πf_c t)',
      description:
        'Raw binary streaming of interleaved In-Phase (I) and Quadrature (Q) samples. Preserves instantaneous phase, amplitude, and frequency dynamics without analog distortion.',
      badge: 'INPUT FORMAT: .IQ / .WAV',
      icon: Binary,
    },
    {
      num: '02',
      id: 'spectral',
      title: 'SPECTRAL CHARACTERIZATION',
      subtitle: 'Welch PSD, Carrier Frequency & SNR Bounds',
      formula: 'SNR = 10·log₁₀(P_signal / P_noise) dB',
      description:
        'Fast Fourier Transform (FFT) analysis detects occupied bandwidth, carrier offset, and noise floor. Spectral shape estimation infers candidate modulation schemes.',
      badge: 'ESTIMATOR: BLIND FFT',
      icon: Search,
    },
    {
      num: '03',
      id: 'demod',
      title: 'SYMBOL SLICING & DEMODULATION',
      subtitle: 'Phase & Amplitude Constellation Mapping',
      formula: 'd_k = argmin |r_k - s_m|',
      description:
        'Carrier phase synchronization (Costas Loop) and Root-Raised Cosine matched filtering recover baseband symbols. Slicers project coordinates to discrete bit sequences.',
      badge: 'MOD FAMILIES: FSK / PSK / QAM',
      icon: Cpu,
    },
    {
      num: '04',
      id: 'deinterleave',
      title: 'BURST DE-INTERLEAVING',
      subtitle: 'Matrix Transposition & Convolutional Diffusion',
      formula: 'Matrix Transposition: M[r, c] ➔ M[c, r]',
      description:
        'RF multi-path and atmospheric fading cause localized error bursts. De-interleaving scatters adjacent corrupted bits across time, converting dense bursts into isolated single-bit errors.',
      badge: 'ALGORITHMS: BLOCK / CONV / DIAGONAL',
      icon: Layers,
    },
    {
      num: '05',
      id: 'fec',
      title: 'FORWARD ERROR CORRECTION',
      subtitle: 'Viterbi Trellis Search & Reed-Solomon Decoding',
      formula: 'Reed-Solomon RS(255, 223): t = 16 bytes corrected',
      description:
        'Syndrome calculation and maximum likelihood sequence estimation correct bit errors introduced over the wireless channel without requiring packet retransmission.',
      badge: 'FEC CODES: VITERBI (K=7) / RS',
      icon: ShieldCheck,
    },
    {
      num: '06',
      id: 'correlate',
      title: 'FRAME SYNC & CORRELATION',
      subtitle: 'Preamble Cross-Correlation & Payload Extraction',
      formula: 'R_xy[n] = Σ x[m] · y[m - n]',
      description:
        'Sliding correlation against known sync words (Barker codes, CCSDS sync vectors) locks packet boundaries, discards flush bits, and extracts valid protocol headers.',
      badge: 'SYNC TARGET: BARKER / 0xACD2',
      icon: Binary,
    },
  ];

  return (
    <section className="w-full border-b border-zinc-800/80 bg-[#09090b] py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header: Editorial & Asymmetric */}
        <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-zinc-800 pb-8 mb-12 gap-6">
          <div className="space-y-3 max-w-xl">
            <div className="text-[11px] font-mono tracking-widest text-zinc-500 uppercase">
              MATHEMATICAL SIGNAL CHAIN
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-white">
              The Architecture of Demodulation
            </h2>
            <p className="text-sm text-zinc-400 font-sans leading-relaxed">
              Digital signal receivers reconstruct transmitted data through cascaded deterministic
              mathematical operations. Each stage resolves one fundamental channel degradation.
            </p>
          </div>

          <div className="font-mono text-xs text-zinc-500 flex items-center gap-2">
            <span>6 SEQUENTIAL STAGES</span>
            <span>·</span>
            <span className="text-cyan-400">DETERMINISTIC DSP</span>
          </div>
        </div>

        {/* Asymmetric Technical Grid (Alternating structures, NOT generic cards) */}
        <div className="space-y-0 border-t border-zinc-800 divide-y divide-zinc-800">
          {stages.map((st, idx) => {
            const Icon = st.icon;
            return (
              <div
                key={st.id}
                onClick={() => onSelectStage(st.id)}
                className="group py-8 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start hover:bg-zinc-900/30 transition-colors px-4 cursor-pointer"
              >
                {/* Stage Indicator (2 cols) */}
                <div className="lg:col-span-2 font-mono flex lg:flex-col justify-between items-start gap-2">
                  <div className="flex items-center gap-2">
                    <Icon className="w-5 h-5 text-zinc-500 group-hover:text-cyan-400 transition-colors" />
                  </div>
                  <span className="text-[10px] px-2 py-0.5 border border-zinc-800 bg-zinc-950 text-zinc-400 font-mono">
                    {st.badge}
                  </span>
                </div>

                {/* Core Title & Description (6 cols) */}
                <div className="lg:col-span-6 space-y-2">
                  <h3 className="font-display text-lg sm:text-xl font-bold text-white tracking-tight group-hover:text-cyan-300 transition-colors flex items-center gap-2">
                    <span>{st.title}</span>
                  </h3>
                  <div className="text-xs font-mono text-zinc-400 font-medium">
                    {st.subtitle}
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed font-sans pt-1 max-w-xl">
                    {st.description}
                  </p>
                </div>

                {/* Mathematical Formula / Data Transformation (4 cols) */}
                <div className="lg:col-span-4 border border-zinc-800/80 bg-zinc-950 p-3 font-mono text-[11px] flex flex-col justify-between">
                  <div className="text-[9px] uppercase tracking-wider text-zinc-600 border-b border-zinc-900 pb-1 flex justify-between">
                    <span>MATHEMATICAL OPERATOR</span>
                    <span className="text-cyan-500/80">EQ_{st.num}</span>
                  </div>
                  <div className="py-2 text-cyan-300 text-xs font-semibold overflow-x-auto">
                    {st.formula}
                  </div>
                  <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-900 flex justify-between items-center">
                    <span>STATUS: IMPLEMENTED</span>
                    <span className="text-zinc-400 group-hover:text-white transition-colors">
                      INSPECT ➔
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

