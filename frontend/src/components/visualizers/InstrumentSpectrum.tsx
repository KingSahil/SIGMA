'use client';

import React, { useEffect, useRef } from 'react';

interface InstrumentSpectrumProps {
  carrierMhz?: number;
  bandwidthMhz?: number;
  snrDb?: number;
}

export function InstrumentSpectrum({
  carrierMhz = 433.92,
  bandwidthMhz = 1.8,
  snrDb = 18.4,
}: InstrumentSpectrumProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let tick = 0;

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;

      // Deep instrument black background
      ctx.fillStyle = '#09090b';
      ctx.fillRect(0, 0, w, h);

      // Oscilloscope grid lines (subtle zinc)
      ctx.strokeStyle = '#18181b';
      ctx.lineWidth = 1;

      // Horizontal grid lines (dBFS steps)
      const hSteps = 5;
      for (let i = 0; i <= hSteps; i++) {
        const y = Math.floor((h / hSteps) * i) + 0.5;
        ctx.beginPath();
        ctx.moveTo(35, y);
        ctx.lineTo(w - 10, y);
        ctx.stroke();
      }

      // Vertical grid lines (Frequency steps)
      const vSteps = 8;
      for (let i = 0; i <= vSteps; i++) {
        const x = Math.floor(35 + ((w - 45) / vSteps) * i) + 0.5;
        ctx.beginPath();
        ctx.moveTo(x, 5);
        ctx.lineTo(x, h - 20);
        ctx.stroke();
      }

      // Center frequency dashed line
      const centerX = Math.floor(35 + (w - 45) * 0.5) + 0.5;
      ctx.save();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = '#27272a';
      ctx.beginPath();
      ctx.moveTo(centerX, 5);
      ctx.lineTo(centerX, h - 20);
      ctx.stroke();
      ctx.restore();

      // Bandwidth shading region (3dB bandwidth)
      const bwPx = (w - 45) * 0.22;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
      ctx.fillRect(centerX - bwPx / 2, 5, bwPx, h - 25);

      // Draw spectral trace (clean phosphor cyan-white line, zero fuzzy blur)
      ctx.beginPath();
      const numPoints = 128;
      const plotWidth = w - 45;
      const baselineY = h - 24;

      for (let i = 0; i < numPoints; i++) {
        const x = 35 + (i / (numPoints - 1)) * plotWidth;
        const distFromCenter = Math.abs(i - (numPoints / 2));

        // Realistic noise floor with fine micro-noise
        const noise = (Math.sin(i * 9.2 + tick * 0.04) * 3 + Math.cos(i * 14.1) * 3.5) * 0.7;
        let signalHump = 0;

        // Raised-cosine envelope
        const halfBwBins = 14;
        if (distFromCenter < halfBwBins) {
          const normDist = distFromCenter / halfBwBins;
          signalHump = Math.cos(normDist * (Math.PI / 2)) * 62 + (Math.random() * 2 - 1);
        } else if (distFromCenter < halfBwBins * 1.5) {
          const skirtDist = (distFromCenter - halfBwBins) / (halfBwBins * 0.5);
          signalHump = Math.max(0, (1 - skirtDist) * 12 + (Math.random() * 2 - 1));
        }

        const y = Math.max(10, baselineY - signalHump - noise);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }

      // Crisp 1.5px trace
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Subtle trace fill
      ctx.lineTo(35 + plotWidth, baselineY);
      ctx.lineTo(35, baselineY);
      ctx.closePath();
      const fillGrad = ctx.createLinearGradient(0, 10, 0, baselineY);
      fillGrad.addColorStop(0, 'rgba(6, 182, 212, 0.12)');
      fillGrad.addColorStop(1, 'rgba(6, 182, 212, 0.0)');
      ctx.fillStyle = fillGrad;
      ctx.fill();

      // Peak marker indicator
      ctx.fillStyle = '#06b6d4';
      ctx.beginPath();
      ctx.arc(centerX, baselineY - 62, 2.5, 0, Math.PI * 2);
      ctx.fill();

      tick++;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationId);
  }, [carrierMhz, bandwidthMhz, snrDb]);

  return (
    <div className="relative w-full h-full flex flex-col font-mono text-[10px]">
      <div className="flex items-center justify-between pb-1.5 text-zinc-400 border-b border-zinc-800/80 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-zinc-200 font-medium tracking-wide uppercase">
            POWER SPECTRUM DENSITY
          </span>
          <span className="text-zinc-500">[RBW: 10 kHz]</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-zinc-500">SPAN: 5.0 MHz</span>
          <span className="text-cyan-400 font-semibold">PEAK: -18.2 dBFS</span>
        </div>
      </div>

      <div className="relative flex-1 bg-[#09090b] border border-zinc-800 rounded-sm overflow-hidden">
        {/* Y Axis Labels */}
        <div className="absolute left-1.5 top-1 bottom-6 flex flex-col justify-between text-[9px] font-mono text-zinc-500 pointer-events-none select-none">
          <span>0 dB</span>
          <span>-20</span>
          <span>-40</span>
          <span>-60</span>
          <span>-80</span>
        </div>

        <canvas
          ref={canvasRef}
          width={460}
          height={180}
          className="w-full h-full block"
        />

        {/* X Axis Labels */}
        <div className="absolute bottom-1 left-9 right-3 flex justify-between text-[9px] font-mono text-zinc-500 pointer-events-none select-none">
          <span>{(carrierMhz - 2.5).toFixed(1)}</span>
          <span>{(carrierMhz - 1.25).toFixed(1)}</span>
          <span className="text-cyan-400 font-semibold">{carrierMhz.toFixed(2)} MHz (Fc)</span>
          <span>{(carrierMhz + 1.25).toFixed(1)}</span>
          <span>{(carrierMhz + 2.5).toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}

