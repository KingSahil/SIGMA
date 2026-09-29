'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Waterfall3D } from './Waterfall3D';

export function InstrumentWaterfall({ frames = [], centerFrequencyMhz, spanMhz }: { frames?: number[][]; centerFrequencyMhz?: number; spanMhz?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [view, setView] = useState<'2d' | '3d'>('2d');

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const width = canvas.width;
    const height = canvas.height;
    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, width, height);
    if (!frames.length) {
      ctx.fillStyle = '#71717a';
      ctx.font = '12px ui-monospace, monospace';
      ctx.fillText('Run analysis to render a measured waterfall', 14, 24);
      return;
    }
    const rows = frames.length;
    let cols = Number.POSITIVE_INFINITY;
    for (const row of frames) {
      if (row.length > 0 && row.length < cols) {
        cols = row.length;
      }
    }
    if (!Number.isFinite(cols) || cols <= 0) {
      ctx.fillStyle = '#71717a';
      ctx.font = '12px ui-monospace, monospace';
      ctx.fillText('Run analysis to render a measured waterfall', 14, 24);
      return;
    }

    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (let row = 0; row < rows; row++) {
      const rowValues = frames[row] ?? [];
      for (let col = 0; col < cols; col++) {
        const value = rowValues[col] ?? 0;
        if (value < min) min = value;
        if (value > max) max = value;
      }
    }
    const span = Math.max(1, max - min);
    const cellW = width / cols;
    const cellH = height / rows;
    for (let row = 0; row < rows; row++) {
      const rowValues = frames[row] ?? [];
      for (let col = 0; col < cols; col++) {
        const value = rowValues[col] ?? 0;
        const intensity = Math.max(0, Math.min(1, (value - min) / span));
        const hue = 225 - intensity * 190;
        const light = 10 + intensity * 55;
        ctx.fillStyle = `hsl(${hue} 82% ${light}%)`;
        ctx.fillRect(col * cellW, row * cellH, Math.ceil(cellW), Math.ceil(cellH));
      }
    }
  }, [frames]);

  return (
    <div className="relative flex h-full w-full flex-col font-mono text-[10px]">
      <div className="mb-2 flex items-center justify-between border-b border-zinc-800/80 pb-1.5 text-zinc-400">
        <div className="flex items-center gap-2"><span className="font-medium uppercase tracking-wide text-zinc-200">Time-frequency waterfall</span><span className="text-zinc-500">{frames.length ? '[MEASURED FFT FRAMES]' : '[AWAITING ANALYSIS]'}</span></div>
        <div className="flex items-center gap-1" aria-label="Waterfall view mode">
          {(['2d', '3d'] as const).map((mode) => <button key={mode} type="button" onClick={() => setView(mode)} aria-pressed={view === mode} className={`px-2 py-1 uppercase ${view === mode ? 'bg-zinc-800 text-cyan-300' : 'text-zinc-500 hover:text-zinc-200'}`}>{mode}</button>)}
        </div>
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden border border-zinc-800 bg-[#09090b]">
        {view === '2d' ? <canvas ref={canvasRef} width={768} height={260} className="block h-full w-full" /> : frames.length ? <Waterfall3D frames={frames} /> : <div className="flex h-full items-center justify-center text-xs text-zinc-500">Measured waterfall frames appear after analysis.</div>}
        <span className="pointer-events-none absolute bottom-1 right-2 bg-black/75 px-1.5 py-1 text-[8px] text-zinc-400">{view === '3d' ? 'X FREQUENCY · Y POWER · Z TIME' : `TIME ↓ · ${centerFrequencyMhz !== undefined ? `CENTER ${centerFrequencyMhz.toFixed(3)} MHz · SPAN ${spanMhz?.toFixed(3) ?? '—'} MHz` : 'FREQUENCY →'}`}</span>
      </div>
    </div>
  );
}
