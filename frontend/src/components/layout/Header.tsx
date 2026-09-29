'use client';

import React from 'react';
import { Terminal, Radio, ArrowUpRight } from 'lucide-react';

interface HeaderProps {
  onOpenLab: () => void;
  onOpenIngest: () => void;
}

export function Header({ onOpenLab, onOpenIngest }: HeaderProps) {
  return (
    <header className="w-full border-b border-zinc-800/80 bg-[#09090b]/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Brand & Technical Metadata */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={onOpenLab}>
            <div className="w-2.5 h-2.5 bg-cyan-400 rounded-none rotate-45" />
            <span className="font-display font-bold text-base tracking-tight text-white uppercase">
              SignalForge
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 border border-zinc-800 bg-zinc-900/60 text-zinc-400">
              SYS-26147
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-4 text-[11px] font-mono text-zinc-500 border-l border-zinc-800/80 pl-6">
            <span className="flex items-center gap-1.5 text-zinc-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              DSP CORE: ACTIVE
            </span>
            <span>{'//'}</span>
            <span>DUAL ADC: 14-BIT</span>
            <span>{'//'}</span>
            <span>SAMPLE CLK: 2.40 MSPS</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenIngest}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-zinc-300 hover:text-white border border-zinc-800 hover:border-zinc-700 bg-zinc-900/40 transition-all cursor-pointer"
          >
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span>INGEST IQ/WAV</span>
          </button>

          <button
            onClick={onOpenLab}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-mono font-semibold text-black bg-[#EDEDED] hover:bg-white transition-all cursor-pointer"
          >
            <span>OPEN WORKBENCH</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
