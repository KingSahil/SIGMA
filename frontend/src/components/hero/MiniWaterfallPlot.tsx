'use client';

import React, { useEffect, useRef } from 'react';

export function MiniWaterfallPlot() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let offset = 0;

    const render = () => {
      const w = canvas.width;
      const h = canvas.height;

      // Base background
      ctx.fillStyle = '#050a18';
      ctx.fillRect(0, 0, w, h);

      // Render spectrogram heatmap blocks
      const cols = 28;
      const rows = 16;
      const cellW = w / cols;
      const cellH = h / rows;

      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          // Calculate energy value
          const distFromCarrier = Math.abs(r - 7); // Center carrier at row 7
          const timePulse = Math.sin((c + offset * 0.2) * 0.4);

          let intensity = 0.15 + Math.random() * 0.1; // background noise

          if (distFromCarrier <= 2) {
            // Signal energy with modulation bursts
            if (timePulse > -0.2) {
              intensity = 0.75 + Math.random() * 0.25;
            } else {
              intensity = 0.35 + Math.random() * 0.15;
            }
          }

          // Color mapping: deep blue -> cyan -> yellow -> white
          let rVal = 0;
          let gVal = 0;
          let bVal = 0;

          if (intensity < 0.3) {
            // Dark blue noise
            rVal = 10;
            gVal = Math.floor(intensity * 120);
            bVal = Math.floor(100 + intensity * 350);
          } else if (intensity < 0.7) {
            // Vibrant cyan
            rVal = 0;
            gVal = Math.floor(180 + (intensity - 0.3) * 180);
            bVal = 255;
          } else {
            // High energy yellow / white
            rVal = Math.floor(200 + (intensity - 0.7) * 180);
            gVal = 255;
            bVal = Math.floor(100 + (1 - intensity) * 300);
          }

          ctx.fillStyle = `rgb(${rVal}, ${gVal}, ${bVal})`;
          ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
        }
      }

      // Subtle horizontal scanline overlay
      ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
      for (let y = 0; y < h; y += 4) {
        ctx.fillRect(0, y, w, 1);
      }

      offset++;
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
        <span className="text-xs font-semibold text-slate-300">Spectrogram</span>
        <span className="text-[10px] text-cyan-400 font-mono">LIVE</span>
      </div>
      <div className="relative flex-1 rounded-lg overflow-hidden border border-[#1b2b4d] bg-[#050a18]">
        {/* Y Axis ticks */}
        <div className="absolute left-1 top-1 bottom-1 flex flex-col justify-between text-[8px] font-mono text-slate-400 pointer-events-none select-none z-10">
          <span>300</span>
          <span>200</span>
          <span>100</span>
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
          <span>0</span>
          <span>2</span>
          <span>4</span>
          <span>6</span>
          <span>8</span>
        </div>
      </div>
      <div className="text-[9px] text-center text-slate-400 mt-1 font-mono">
        Time (s)
      </div>
    </div>
  );
}

