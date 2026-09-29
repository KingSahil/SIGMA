'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Waterfall3D } from './Waterfall3D';

export function InstrumentWaterfall({ frames = [], centerFrequencyMhz, spanMhz }: { frames?: number[][]; centerFrequencyMhz?: number; spanMhz?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [view, setView] = useState<'2d' | '3d'>('2d');
  const displayFrames = useMemo(() => {
    if (!frames.length || !frames[0]?.length || frames.length >= frames[0].length) return frames;
    return frames[0].map((_, column) => frames.map((row) => row[column] ?? -120));
  }, [frames]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const width = canvas.width;
    const height = canvas.height;
    let frame = 0;
    let animation = 0;
    let lastStep = 0;

    const draw = (now: number) => {
      ctx.fillStyle = '#09090b';
      ctx.fillRect(0, 0, width, height);
      if (!displayFrames.length) {
        ctx.fillStyle = '#71717a';
        ctx.font = '12px ui-monospace, monospace';
        ctx.fillText('Run analysis to render a measured waterfall', 14, 24);
        return;
      }
      const rows = displayFrames.length;
      const cols = Math.min(...displayFrames.map((row) => row.length).filter((length) => length > 0));
      if (!Number.isFinite(cols) || cols <= 0) return;
      let min = Number.POSITIVE_INFINITY;
      let max = Number.NEGATIVE_INFINITY;
      for (const rowValues of displayFrames) {
        for (let col = 0; col < cols; col += 1) {
          const value = Number(rowValues[col]);
          if (!Number.isFinite(value)) continue;
          min = Math.min(min, value);
          max = Math.max(max, value);
        }
      }
      const valueSpan = Math.max(1, max - min);
      const cellW = width / cols;
      const cellH = height / rows;
      for (let row = 0; row < rows; row += 1) {
        const rowValues = displayFrames[(row + frame) % rows] ?? [];
        for (let col = 0; col < cols; col += 1) {
          const value = Number(rowValues[col] ?? min);
          const intensity = Number.isFinite(value) ? Math.max(0, Math.min(1, (value - min) / valueSpan)) : 0;
          ctx.fillStyle = `hsl(${225 - intensity * 190} 82% ${10 + intensity * 55}%)`;
          ctx.fillRect(col * cellW, row * cellH, Math.ceil(cellW), Math.ceil(cellH));
        }
      }
      if (now - lastStep > 80) {
        frame = (frame + 1) % rows;
        lastStep = now;
      }
      animation = requestAnimationFrame(draw);
    };

    animation = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animation);
  }, [displayFrames]);
  return (
    <div className="relative flex h-full w-full flex-col font-mono text-[10px]">
      <div className="mb-2 flex items-center justify-between border-b border-zinc-800/80 pb-1.5 text-zinc-400">
        <div className="flex items-center gap-2"><span className="font-medium uppercase tracking-wide text-zinc-200">Time-frequency waterfall</span><span className="text-zinc-500">{displayFrames.length ? '[MEASURED FFT FRAMES]' : '[AWAITING ANALYSIS]'}</span></div>
        <div className="flex items-center gap-1" aria-label="Waterfall view mode">
          {(['2d', '3d'] as const).map((mode) => <button key={mode} type="button" onClick={() => setView(mode)} aria-pressed={view === mode} className={`px-2 py-1 uppercase ${view === mode ? 'bg-zinc-800 text-cyan-300' : 'text-zinc-500 hover:text-zinc-200'}`}>{mode}</button>)}
        </div>
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden border border-zinc-800 bg-[#09090b]">
        {view === '2d' ? <canvas ref={canvasRef} width={768} height={260} className="block h-full w-full" /> : displayFrames.length ? <Waterfall3D frames={displayFrames} /> : <div className="flex h-full items-center justify-center text-xs text-zinc-500">Measured waterfall frames appear after analysis.</div>}
        <span className="pointer-events-none absolute bottom-1 right-2 bg-black/75 px-1.5 py-1 text-[8px] text-zinc-400">{view === '3d' ? 'X FREQUENCY · Y POWER · Z TIME' : `TIME ↓ · ${centerFrequencyMhz !== undefined ? `CENTER ${centerFrequencyMhz.toFixed(3)} MHz · SPAN ${spanMhz?.toFixed(3) ?? '—'} MHz` : 'FREQUENCY →'}`}</span>
      </div>
    </div>
  );
}