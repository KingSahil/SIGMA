'use client';

import React from 'react';

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-800 bg-[#09090b] text-zinc-500 font-mono text-[11px] py-12">
      <div className="max-w-7xl mx-auto px-6 space-y-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-8 border-b border-zinc-800/60">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-zinc-300 font-display font-bold text-sm tracking-tight">
              <span className="w-2 h-2 bg-cyan-400 rotate-45 inline-block" />
              <span>SIGNALFORGE // RF SIGNAL INTELLIGENCE</span>
            </div>
            <p className="text-zinc-500 text-xs font-sans">
              Autonomous RF demodulation, parameter extraction, and bitstream forensics platform.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs text-zinc-400">
            <span className="text-zinc-600">// STACK:</span>
            <span>NEXT.JS 16</span>
            <span>FASTAPI</span>
            <span>NUMPY / SCIPY</span>
            <span>GNU RADIO</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[10px] text-zinc-600">
          <div>
            SYSTEM IDENTIFIER: <span className="text-zinc-400">SF-PS-26147-DSP</span> | CLOCK: <span className="text-zinc-400">2.40 MSPS</span>
          </div>
          <div>
            COORDINATES: UTC 2026-09-16 | COMMIT: <span className="text-zinc-400">6f8a2b1</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

