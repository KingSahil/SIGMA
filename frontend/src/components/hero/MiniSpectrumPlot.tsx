'use client';

import React, { useEffect, useRef } from 'react';

export function MiniSpectrumPlot() {
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

      // Dark background
      ctx.fillStyle = '#060c1c';
      ctx.fillRect(0, 0, w, h);

      // Grid lines
      ctx.strokeStyle = '#142038';
      ctx.lineWidth = 1;
      // Horizontal grid
      for (let y = 15; y < h; y += 22) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      // Vertical grid
      for (let x = 20; x < w; x += 35) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      // Draw RF Spectrum curve
      ctx.beginPath();
      const points: [number, number][] = [];
      const numPoints = 100;
      const centerIndex = 52;

      for (let i = 0; i <= numPoints; i++) {
        const x = (i / numPoints) * w;
        const distFromCenter = Math.abs(i - centerIndex);
        
        // Base noise floor
        const noise = (Math.sin(i * 12.3 + tick * 0.05) * 4 + Math.cos(i * 5.7) * 5) * 0.8;
        let signalPeak = 0;

        // Carrier peak around center
        if (distFromCenter < 14) {
          const envelope = Math.cos((distFromCenter / 14) * (Math.PI / 2));
          signalPeak = envelope * 58 + Math.sin(tick * 0.1 + i) * 3;
        }

        const baselineY = h - 20;
        const y = Math.max(12, baselineY - signalPeak - noise);
        points.push([x, y]);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }

      // Stroke with glowing cyan
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 1.8;
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 8;
      ctx.stroke();

      // Area fill under curve with gradient
      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(0, 229, 255, 0.25)');
      grad.addColorStop(1, 'rgba(0, 229, 255, 0.0)');
      ctx.fillStyle = grad;
      ctx.shadowBlur = 0; // reset shadow
      ctx.fill();

      tick++;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <div className="relative w-full h-full flex flex-col">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-300">Spectrum</span>
        <span className="text-[10px] text-slate-400 font-mono">dBFS</span>
      </div>
      <div className="relative flex-1 rounded-lg overflow-hidden border border-[#1b2b4d] bg-[#060c1c]">
        {/* Y Axis ticks */}
        <div className="absolute left-1.5 top-1 bottom-1 flex flex-col justify-between text-[8px] font-mono text-slate-400 pointer-events-none select-none z-10">
          <span>-60</span>
          <span>-40</span>
          <span>-20</span>
          <span>0</span>
        </div>
        {/* Canvas */}
        <canvas
          ref={canvasRef}
          width={280}
          height={120}
          className="w-full h-full block"
        />
        {/* X Axis ticks */}
        <div className="absolute bottom-1 left-8 right-2 flex justify-between text-[8px] font-mono text-slate-400 pointer-events-none select-none">
          <span>100</span>
          <span>200</span>
          <span>300</span>
          <span>400</span>
        </div>
      </div>
      <div className="text-[9px] text-center text-slate-400 mt-1 font-mono">
        Frequency (MHz)
      </div>
    </div>
  );
}

