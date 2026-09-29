'use client';

import React from 'react';
import { Activity } from 'lucide-react';

interface HeroNavbarProps {
  onOpenLab?: () => void;
  active?: 'home' | 'features' | 'how-it-works' | 'use-cases' | 'about';
}

const activeClass = "text-white relative after:content-[''] after:absolute after:-bottom-1 after:left-0 after:w-full after:h-0.5 after:bg-blue-500 rounded";
const inactiveClass = 'text-slate-300 hover:text-white transition-colors';

export function HeroNavbar({ onOpenLab, active = 'home' }: HeroNavbarProps) {
  return (
    <header className="relative z-30 mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-5 sm:px-6 xl:px-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <a href="/#home" className="flex items-center gap-3 cursor-pointer group">
          <div className="relative flex items-center justify-center">
            <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-md group-hover:bg-cyan-500/40 transition-all" />
            <div className="relative p-2 rounded-lg bg-[#0a1226] border border-cyan-500/30 text-cyan-400">
              <Activity className="w-6 h-6 stroke-[2.5]" />
            </div>
          </div>
          <div>
            <div className="flex items-center">
              <span className="text-xl font-bold tracking-tight text-white">Signal</span>
              <span className="text-xl font-bold tracking-tight text-cyan-400">Forge</span>
            </div>
            <div className="text-[9px] tracking-[0.25em] font-medium text-slate-400 uppercase">See Beyond The Spectrum</div>
          </div>
        </a>

        <nav className="hidden items-center gap-8 text-sm font-medium xl:flex">
          <a href="/#home" className={active === 'home' ? activeClass : inactiveClass}>Home</a>
          <a href="/features" className={active === 'features' ? activeClass : inactiveClass}>Features</a>
          <a href="/how-it-works" className={active === 'how-it-works' ? activeClass : inactiveClass}>How It Works</a>
          <a href="/use-cases" className={active === 'use-cases' ? activeClass : inactiveClass}>Use Cases</a>
          <a href="/about" className={active === 'about' ? activeClass : inactiveClass}>About</a>
        </nav>

        <div className="flex items-center gap-2 sm:gap-4">
          <button onClick={onOpenLab} className="text-sm font-medium text-slate-300 hover:text-white px-3 py-1.5 transition-colors">Sign In</button>
          <button onClick={onOpenLab} className="text-sm font-semibold px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white shadow-lg shadow-blue-600/30 transition-all duration-200 cursor-pointer">Get Started</button>
        </div>
      </div>

      <div className="hidden items-center justify-end gap-3 pt-1 xl:flex">
        <span className="text-[10px] tracking-[0.25em] font-mono uppercase text-slate-400">RADIO &nbsp; SIGNAL &nbsp; INTELLIGENCE</span>
        <div className="w-20 h-[1px] bg-slate-700/60" />
      </div>
    </header>
  );
}