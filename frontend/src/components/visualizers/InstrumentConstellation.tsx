'use client';

import React, { useEffect, useRef } from 'react';

interface InstrumentConstellationProps {
  modulation?: string;
  snrDb?: number;
}

export function InstrumentConstellation({
  modulation = 'QPSK',
  snrDb = 18.4,
}: InstrumentConstellationProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;

      // Dark instrument background
      ctx.fillStyle = '#09090b';
      ctx.fillRect(0, 0, w, h);

      // Grid crosshairs
      ctx.strokeStyle = '#18181b';
      ctx.lineWidth = 1;

      // Unit circle reference
      ctx.beginPath();
      ctx.arc(cx, cy, 46, 0, Math.PI * 2);
      ctx.stroke();

      // Axes: I and Q
      ctx.beginPath();
      ctx.moveTo(cx, 10);
      ctx.lineTo(cx, h - 10);
      ctx.moveTo(10, cy);
      ctx.lineTo(w - 10, cy);
      ctx.stroke();

      // QPSK 4 Symbol Target Centers: (+1, +1), (-1, +1), (-1, -1), (+1, -1) normalized
      const offset = 33;
      const centers = [
        { x: cx + offset, y: cy - offset },
        { x: cx - offset, y: cy - offset },
        { x: cx - offset, y: cy + offset },
        { x: cx + offset, y: cy + offset },
      ];

      // Draw crosshair markers on ideal constellation targets
      ctx.strokeStyle = '#27272a';
      centers.forEach((c) => {
        ctx.beginPath();
        ctx.moveTo(c.x - 4, c.y);
        ctx.lineTo(c.x + 4, c.y);
        ctx.moveTo(c.x, c.y - 4);
        ctx.lineTo(c.x, c.y + 4);
        ctx.stroke();
      });

      // Scatter points (simulating 18.4 dB SNR)
      ctx.fillStyle = '#06b6d4';
      for (let i = 0; i < 90; i++) {
        const c = centers[i % 4];
        // Standard normal approximation
        const u = 1 - Math.random();
        const v = Math.random();
        const r = Math.sqrt(-2.0 * Math.log(u)) * 4.2;
        const theta = 2.0 * Math.PI * v;
        const px = c.x + r * Math.cos(theta);
        const py = c.y + r * Math.sin(theta);

        ctx.fillRect(px, py, 1.5, 1.5);
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationId);
  }, [modulation, snrDb]);

  return (
    <div className="relative w-full h-full flex flex-col font-mono text-[10px]">
      <div className="flex items-center justify-between pb-1.5 text-zinc-400 border-b border-zinc-800/80 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-zinc-200 font-medium tracking-wide uppercase">
            I/Q CONSTELLATION
          </span>
        </div>
        <span className="text-cyan-400 font-semibold">{modulation} (M=4)</span>
      </div>

      <div className="relative flex-1 bg-[#09090b] border border-zinc-800 rounded-sm overflow-hidden flex items-center justify-center">
        {/* Quadrant labels */}
        <span className="absolute top-2 left-2 text-[8px] text-zinc-600">Q2 (-I,+Q)</span>
        <span className="absolute top-2 right-2 text-[8px] text-zinc-600">Q1 (+I,+Q)</span>
        <span className="absolute bottom-2 left-2 text-[8px] text-zinc-600">Q3 (-I,-Q)</span>
        <span className="absolute bottom-2 right-2 text-[8px] text-zinc-600">Q4 (+I,-Q)</span>

        <canvas
          ref={canvasRef}
          width={180}
          height={140}
          className="w-full h-full block"
        />
      </div>
    </div>
  );
}

