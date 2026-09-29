'use client';

import React, { useState } from 'react';
import {
  Activity,
  LayoutDashboard,
  Radio,
  Cpu,
  Binary,
  History,
  Settings,
  CheckCircle2,
  Download,
} from 'lucide-react';
import { MiniSpectrumPlot } from './MiniSpectrumPlot';
import { MiniWaterfallPlot } from './MiniWaterfallPlot';
import { MiniConstellationPlot } from './MiniConstellationPlot';
import { useSignal } from '../../context/SignalContext';

interface HeroProductPreviewProps {
  onOpenFullLab?: () => void;
}

export function HeroProductPreview({ onOpenFullLab }: HeroProductPreviewProps) {
  const { metadata, spectralData } = useSignal();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'analyze' | 'demod' | 'decode' | 'history' | 'settings'>('dashboard');

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'analyze', label: 'Analyze', icon: Radio },
    { id: 'demod', label: 'Demodulate', icon: Cpu },
    { id: 'decode', label: 'Decode', icon: Binary },
    { id: 'history', label: 'History', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <div className="relative group w-full max-w-2xl mx-auto">
      {/* Outer ambient glow */}
      <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 via-blue-600/20 to-purple-600/20 rounded-2xl blur-xl opacity-75 group-hover:opacity-100 transition duration-500" />

      {/* Main card container */}
      <div className="relative rounded-2xl border border-cyan-500/30 bg-[#070e20]/95 backdrop-blur-xl shadow-2xl shadow-black/80 overflow-hidden flex flex-col md:flex-row">
        {/* Mini Sidebar */}
        <div className="w-full md:w-36 border-b md:border-b-0 md:border-r border-[#152342] p-3 flex md:flex-col justify-between bg-[#050b1a]/80">
          <div>
            {/* Mini Brand */}
            <div className="flex items-center gap-1.5 px-2 py-1 mb-3">
              <Activity className="w-4 h-4 text-cyan-400 stroke-[2.5]" />
              <span className="text-xs font-bold text-white tracking-tight">Signal</span>
              <span className="text-xs font-bold text-cyan-400 tracking-tight">Forge</span>
            </div>

            {/* Nav list */}
            <div className="flex md:flex-col gap-1 overflow-x-auto md:overflow-visible">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id);
                      if (item.id !== 'dashboard' && onOpenFullLab) {
                        onOpenFullLab();
                      }
                    }}
                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                      isActive
                        ? 'bg-blue-600/30 text-cyan-300 border border-blue-500/40 shadow-sm shadow-blue-500/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-[#0c1730]'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 p-3.5 flex flex-col gap-3">
          {/* 4 Quadrants Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Top-Left: Spectrum */}
            <div className="h-44 p-2 rounded-xl bg-[#081229]/80 border border-[#182a4d]/70 shadow-inner">
              <MiniSpectrumPlot />
            </div>

            {/* Top-Right: Spectrogram */}
            <div className="h-44 p-2 rounded-xl bg-[#081229]/80 border border-[#182a4d]/70 shadow-inner">
              <MiniWaterfallPlot />
            </div>

            {/* Bottom-Left: Constellation */}
            <div className="h-40 p-2 rounded-xl bg-[#081229]/80 border border-[#182a4d]/70 shadow-inner">
              <MiniConstellationPlot />
            </div>

            {/* Bottom-Right: Detected Parameters */}
            <div className="h-40 p-2.5 rounded-xl bg-[#081229]/80 border border-[#182a4d]/70 flex flex-col justify-between">
              <div className="flex items-center justify-between border-b border-[#182a4d] pb-1.5">
                <span className="text-xs font-semibold text-slate-300">Detected Parameters</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  AUTO-DSP
                </span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Modulation</span>
                  <span className="font-semibold text-white font-mono">
                    {spectralData?.estimatedModulation || 'QPSK'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Sampling Rate</span>
                  <span className="font-semibold text-white font-mono">
                    {(metadata?.sampleRateHz ? (metadata.sampleRateHz / 1e6).toFixed(1) : '2.4')} Msps
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Carrier Frequency</span>
                  <span className="font-semibold text-white font-mono">
                    {(metadata?.centerFreqHz ? (metadata.centerFreqHz / 1e6).toFixed(1) : '144.2')} MHz
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Bandwidth</span>
                  <span className="font-semibold text-white font-mono">
                    {(spectralData?.bandwidthMhz || 1.8).toFixed(1)} MHz
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">SNR</span>
                  <span className="font-semibold text-cyan-400 font-mono">
                    {(spectralData?.snrDb || 18.4).toFixed(1)} dB
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Status & Action Bar */}
          <div className="flex items-center justify-between pt-1 border-t border-[#152342] text-xs">
            <div className="flex items-center gap-2 text-slate-300">
              <div className="p-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <span className="text-[11px] font-medium text-slate-200">
                Signal Analyzed Successfully
              </span>
            </div>

            <button
              onClick={onOpenFullLab}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-xs font-semibold shadow-md shadow-blue-600/30 transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Report</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

