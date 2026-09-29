'use client';

import React, { useEffect, useRef } from 'react';

export function InstrumentWaterfall() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let frameIndex = 0;

    // Colormap cache for 256 intensity values (deep navy -> steel cyan -> crisp amber)
    const colorMap: string[] = [];
    for (let i = 0; i < 256; i++) {
      const t = i / 255;
      let r = 0, g = 0, b = 0;
      if (t < 0.35) {
        // Noise floor: dark slate
        r = Math.floor(10 + t * 40);
        g = Math.floor(14 + t * 60);
        b = Math.floor(24 + t * 120);
      } else if (t < 0.75) {
        // In-band signal: phosphor cyan
        const subT = (t - 0.35) / 0.4;
        r = Math.floor(20 + subT * 30);
        g = Math.floor(120 + subT * 120);
        b = Math.floor(180 + subT * 70);
      } else {
        // Peak energy: amber / white
        const subT = (t - 0.75) / 0.25;
        r = Math.floor(210 + subT * 45);
        g = Math.floor(210 + subT * 45);
        b = Math.floor(120 + subT * 135);
      }
      colorMap.push(`rgb(${r},${g},${b})`);
    }

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;

      // Base background
      ctx.fillStyle = '#09090b';
      ctx.fillRect(0, 0, w, h);

      const cols = 56;
      const rows = 24;
      const cellW = w / cols;
      const cellH = h / rows;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const distFromCenter = Math.abs(c - (cols / 2));
          // Time modulation wave
          const timeSignal = Math.sin((r + frameIndex * 0.3) * 0.5);

          let intensity = Math.random() * 45 + 15; // baseline noise

          if (distFromCenter < 8) {
            // Signal band
            if (timeSignal > -0.3) {
              const envelope = Math.cos((distFromCenter / 8) * (Math.PI / 2));
              intensity += envelope * 170 + Math.random() * 25;
            }
          }

          const clamped = Math.min(255, Math.max(0, Math.floor(intensity)));
          ctx.fillStyle = colorMap[clamped];
          ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
        }
      }

      frameIndex++;
      setTimeout(() => {
        animationId = requestAnimationFrame(render);
      }, 50);
    };

    render();

    return () => cancelAnimationFrame(animationId);
  }, []);

  return (
    <div className="relative w-full h-full flex flex-col font-mono text-[10px]">
      <div className="flex items-center justify-between pb-1.5 text-zinc-400 border-b border-zinc-800/80 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-zinc-200 font-medium tracking-wide uppercase">
            TIME-FREQUENCY WATERFALL
          </span>
          <span className="text-zinc-500">[STFT / 256-PT]</span>
        </div>
        <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          ACTIVE SWEEP
        </span>
      </div>

      <div className="relative flex-1 bg-[#09090b] border border-zinc-800 rounded-sm overflow-hidden">
        {/* Y Axis (Time index) */}
        <div className="absolute left-1.5 top-1 bottom-1 flex flex-col justify-between text-[8px] font-mono text-zinc-400 pointer-events-none select-none z-10 bg-black/60 px-1 py-0.5 border border-zinc-800/60">
          <span>T - 0.0s</span>
          <span>T - 1.2s</span>
          <span>T - 2.4s</span>
          <span>T - 3.6s</span>
        </div>

        <canvas
          ref={canvasRef}
          width={460}
          height={140}
          className="w-full h-full block"
        />

        {/* X Axis (Frequency) */}
        <div className="absolute bottom-1 right-2 flex gap-4 text-[8px] font-mono text-zinc-400 pointer-events-none select-none bg-black/60 px-1 py-0.5 border border-zinc-800/60">
          <span>CENTER: 433.92 MHz</span>
          <span>SPAN: 5.0 MHz</span>
        </div>
      </div>
    </div>
  );
}

