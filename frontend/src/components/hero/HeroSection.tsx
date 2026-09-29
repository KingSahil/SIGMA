'use client';

import React from 'react';
import {
  Upload,
  ArrowRight,
  Play,
  Activity,
  Grid3X3,
  Cpu,
  Layers,
  FileCode2,
  Radio,
} from 'lucide-react';
import { HeroNavbar } from './HeroNavbar';
import { HeroProductPreview } from './HeroProductPreview';

interface HeroSectionProps {
  onOpenLab?: () => void;
  onUploadSignal?: () => void;
  onWatchDemo?: () => void;
}

export function HeroSection({
  onOpenLab,
  onUploadSignal,
  onWatchDemo,
}: HeroSectionProps) {
  const featureBadges = [
    {
      title: 'Spectrum Analysis',
      icon: Activity,
    },
    {
      title: 'Modulation Identification',
      icon: Grid3X3,
    },
    {
      title: 'Demodulation & Decoding',
      icon: Cpu,
    },
    {
      title: 'FEC & De-interleaving',
      icon: Layers,
    },
    {
      title: 'Bitstream Correlation',
      icon: FileCode2,
    },
  ];

  return (
    <section className="relative min-h-screen w-full bg-[#040814] text-white flex flex-col justify-between overflow-hidden">
      {/* Background Gradients & Atmospheric Glow */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[500px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Navigation */}
      <HeroNavbar onOpenLab={onOpenLab} />

      {/* Hero Center Grid */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 lg:px-12 pt-4 pb-16 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        {/* Left Column: Headline & Value Prop */}
        <div className="lg:col-span-6 flex flex-col gap-6">
          {/* Overline category */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono tracking-[0.25em] text-slate-400 uppercase font-semibold">
              From Signals To Insights
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.12]">
            Decode the{' '}
            <span className="bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 bg-clip-text text-transparent">
              Invisible
            </span>{' '}
            World
          </h1>

          {/* Subtitle Description */}
          <p className="text-base sm:text-lg text-slate-300 max-w-xl leading-relaxed font-normal">
            An advanced RF signal analysis platform to identify, demodulate, and
            extract critical signal parameters from IQ and WAV files using AI
            and signal processing.
          </p>

          {/* Call-to-action buttons */}
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <button
              onClick={onUploadSignal || onOpenLab}
              className="flex items-center gap-3 px-6 py-3.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:from-blue-700 active:to-indigo-700 text-white font-semibold text-base shadow-xl shadow-blue-600/30 transition-all cursor-pointer group"
            >
              <Upload className="w-5 h-5 text-cyan-200 group-hover:-translate-y-0.5 transition-transform" />
              <span>Upload a Signal</span>
              <ArrowRight className="w-4 h-4 text-cyan-200 group-hover:translate-x-0.5 transition-transform" />
            </button>

            <button
              onClick={onWatchDemo || onOpenLab}
              className="flex items-center gap-2.5 px-6 py-3.5 rounded-xl bg-[#0b1429] hover:bg-[#101d3b] active:bg-[#080f1f] text-slate-200 border border-[#1e3059] font-medium text-base transition-all cursor-pointer"
            >
              <div className="w-6 h-6 rounded-full border border-slate-400 flex items-center justify-center">
                <Play className="w-3 h-3 fill-slate-200 text-slate-200 ml-0.5" />
              </div>
              <span>Watch Demo</span>
            </button>
          </div>

          {/* 5-Stage Feature Icons Row */}
          <div className="grid grid-cols-5 gap-3 pt-6 border-t border-slate-800/80 max-w-xl">
            {featureBadges.map((badge, idx) => {
              const Icon = badge.icon;
              return (
                <div
                  key={idx}
                  className="flex flex-col items-center text-center gap-2 group cursor-pointer"
                  onClick={onOpenLab}
                >
                  <div className="w-10 h-10 rounded-xl bg-[#0b142b] border border-cyan-500/20 group-hover:border-cyan-400/50 flex items-center justify-center text-cyan-400 group-hover:text-cyan-300 transition-all shadow-md group-hover:shadow-cyan-500/20">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] leading-tight text-slate-400 group-hover:text-slate-200 font-medium">
                    {badge.title}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Hero Product Preview / Lab Scope */}
        <div className="lg:col-span-6 flex justify-center">
          <HeroProductPreview onOpenFullLab={onOpenLab} />
        </div>
      </div>

      {/* Atmospheric Bottom Section with Glowing Sine Wave Ribbons & Radio Tower */}
      <div className="relative w-full overflow-hidden mt-auto pt-8">
        {/* Wave ribbons SVG */}
        <div className="absolute inset-x-0 bottom-0 pointer-events-none opacity-80">
          <svg
            viewBox="0 0 1440 220"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-full h-auto"
          >
            {/* Wave 1: Blue */}
            <path
              d="M-40,160 C240,80 420,240 720,150 C1020,60 1200,180 1480,120"
              stroke="url(#blue-grad)"
              strokeWidth="2.5"
              fill="none"
              opacity="0.85"
            />
            {/* Wave 2: Cyan */}
            <path
              d="M-40,190 C220,130 480,190 740,110 C1000,30 1260,170 1480,140"
              stroke="url(#cyan-grad)"
              strokeWidth="2.0"
              fill="none"
              opacity="0.9"
            />
            {/* Wave 3: Purple / Violet */}
            <path
              d="M-40,130 C260,200 460,90 760,180 C1060,270 1240,110 1480,170"
              stroke="url(#purple-grad)"
              strokeWidth="1.8"
              fill="none"
              opacity="0.6"
            />
            {/* Mesh gradient fills */}
            <defs>
              <linearGradient id="cyan-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.1" />
                <stop offset="30%" stopColor="#00f0ff" stopOpacity="0.9" />
                <stop offset="70%" stopColor="#3b82f6" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.2" />
              </linearGradient>
              <linearGradient id="blue-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.1" />
                <stop offset="40%" stopColor="#2563eb" stopOpacity="0.8" />
                <stop offset="80%" stopColor="#06b6d4" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#2563eb" stopOpacity="0.1" />
              </linearGradient>
              <linearGradient id="purple-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.1" />
                <stop offset="50%" stopColor="#a855f7" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#6366f1" stopOpacity="0.1" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Radio Tower Silhouettes and Frequency Badges on Bottom Right */}
        <div className="absolute right-8 sm:right-16 bottom-12 flex items-end gap-3 pointer-events-none opacity-60">
          <div className="flex flex-col items-center">
            <Radio className="w-10 h-10 text-slate-500 stroke-[1.5]" />
            <div className="w-1 h-12 bg-gradient-to-t from-slate-700 to-transparent" />
          </div>
          <div className="flex flex-col text-[10px] font-mono font-semibold tracking-wider text-slate-400 pb-1">
            <span>HF</span>
            <span>VHF</span>
            <span className="text-cyan-400">UHF</span>
          </div>
        </div>

        {/* Bottom Centered Ticker Banner */}
        <div className="relative z-10 w-full py-4 text-center border-t border-slate-800/60 bg-[#040814]/70 backdrop-blur-sm">
          <p className="text-[11px] font-mono tracking-[0.35em] uppercase text-slate-400">
            ANALYZE &nbsp;&nbsp;·&nbsp;&nbsp; DEMODULATE &nbsp;&nbsp;·&nbsp;&nbsp; DECODE &nbsp;&nbsp;·&nbsp;&nbsp; DISCOVER
          </p>
        </div>
      </div>
    </section>
  );
}

