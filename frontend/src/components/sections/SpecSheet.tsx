'use client';

import React from 'react';

export function SpecSheet() {
  const specs = [
    {
      category: 'QUADRATURE INGESTION',
      entries: [
        { label: 'IQ Representation', value: 'Interleaved 32-bit Float (FP32), 16-bit Signed Int (CS16)' },
        { label: 'Audio Baseband', value: 'RIFF WAVE (.wav) up to 192 kHz 24-bit PCM' },
        { label: 'Max Ingestion Rate', value: 'Tested up to 40.0 MSps continuous streaming buffer' },
        { label: 'Buffer Storage', value: 'Circular ring buffer with IEEE-754 memory mapping' },
      ],
    },
    {
      category: 'MODULATION RECOVERY',
      entries: [
        { label: 'Phase Shift Keying (PSK)', value: 'BPSK (M=2), QPSK (M=4), 8-PSK (M=8) with Costas loop phase lock' },
        { label: 'Frequency Shift Keying (FSK)', value: '2-FSK, 4-FSK with mark/space frequency discriminator' },
        { label: 'Quadrature Amplitude (QAM)', value: '16-QAM, 64-QAM with adaptive decision feedback equalization' },
        { label: 'Pulse Shaping Filter', value: 'Root-Raised Cosine (RRC) matched filter with roll-off α: 0.20 – 0.50' },
      ],
    },
    {
      category: 'DE-INTERLEAVING ENGINE',
      entries: [
        { label: 'Block Interleaver', value: 'Row-in / Column-out matrix transposition up to 256 × 256 depth' },
        { label: 'Convolutional Interleaver', value: 'Ramsey / Forney shift-register array (B branches, M delays)' },
        { label: 'Diagonal Interleaver', value: 'Skewed triangular memory address generator' },
        { label: 'Pseudo-Random', value: 'LFSR polynomial permutation vector alignment' },
      ],
    },
    {
      category: 'ERROR CORRECTION (FEC)',
      entries: [
        { label: 'Convolutional / Viterbi', value: 'Soft-decision trellis decoder (K=7, polynomials 171₈ / 133₈)' },
        { label: 'Reed-Solomon Codes', value: 'RS(255, 223) & RS(204, 188) over Galois Field GF(2⁸) with t=16 errors' },
        { label: 'Concatenated Coding', value: 'Inner Viterbi convolutional + Outer Reed-Solomon block code' },
        { label: 'LDPC Codes', value: 'Sparse parity-check matrix with belief propagation syndrome decoding' },
      ],
    },
    {
      category: 'FRAME SYNCHRONIZATION',
      entries: [
        { label: 'Preamble Detectors', value: 'Barker sequences (7, 11, 13 bits), CCSDS sync marker (0x1ACFFC1D)' },
        { label: 'Correlation Metric', value: 'Sliding normalized cross-correlation R_xy with configurable threshold' },
        { label: 'Tolerance Window', value: 'Hamming distance allowance: 0 to 3 bit flips in preamble window' },
      ],
    },
  ];

  return (
    <section className="w-full border-b border-zinc-800/80 bg-[#09090b] py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between border-b border-zinc-800 pb-8 mb-12 gap-6">
          <div className="space-y-3 max-w-xl">
            <div className="text-[11px] font-mono tracking-widest text-zinc-500 uppercase">
              CAPABILITY MATRIX
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Signal Processing Specifications
            </h2>
            <p className="text-sm text-zinc-400 font-sans leading-relaxed">
              Standardized mathematical parameters supported across the SignalForge engine.
              Compliant with aerospace, satellite, and tactical SDR transmission profiles.
            </p>
          </div>

          <div className="font-mono text-xs text-zinc-500">
            <span>DOC-ID: SF-SPEC-2026</span>
          </div>
        </div>

        {/* Technical Data Sheet Grid */}
        <div className="border border-zinc-800 bg-zinc-950/40 divide-y divide-zinc-800 font-mono text-xs">
          {specs.map((group, idx) => (
            <div key={idx} className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-zinc-800">
              {/* Category Label (4 cols) */}
              <div className="lg:col-span-4 p-5 bg-zinc-950/60 flex items-start justify-between">
                <span className="font-bold text-zinc-300 tracking-wider text-[11px]">
                  {group.category}
                </span>
              </div>

              {/* Entries (8 cols) */}
              <div className="lg:col-span-8 divide-y divide-zinc-800/70">
                {group.entries.map((e, eIdx) => (
                  <div key={eIdx} className="p-3.5 sm:px-5 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 hover:bg-zinc-900/30 transition-colors">
                    <span className="text-zinc-400 text-[11px] sm:w-1/3">
                      {e.label}
                    </span>
                    <span className="text-zinc-200 text-xs sm:w-2/3 font-sans sm:font-mono">
                      {e.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

