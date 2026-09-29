'use client';

import React, { useEffect, useRef } from 'react';

export function MiniConstellationPlot() {
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
      const centerX = w / 2;
      const centerY = h / 2;

      // Dark background
      ctx.fillStyle = '#060c1c';
      ctx.fillRect(0, 0, w, h);

      // Draw subtle crosshair axes
      ctx.strokeStyle = '#15243f';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(centerX, 0);
      ctx.lineTo(centerX, h);
      ctx.moveTo(0, centerY);
      ctx.lineTo(w, centerY);
      ctx.stroke();

      // QPSK constellation 4 clusters: (+1, +1), (-1, +1), (-1, -1), (+1, -1)
      const offset = 40;
      const clusters = [
        { x: centerX - offset, y: centerY - offset },
        { x: centerX + offset, y: centerY - offset },
        { x: centerX - offset, y: centerY + offset },
        { x: centerX + offset, y: centerY + offset },
      ];

      // Draw each cluster with glow + scattered points
      clusters.forEach((cluster) => {
        // Outer radial halo
        const grad = ctx.createRadialGradient(
          cluster.x,
          cluster.y,
          0,
          cluster.x,
          cluster.y,
          24
        );
        grad.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
        grad.addColorStop(0.4, 'rgba(0, 180, 255, 0.18)');
        grad.addColorStop(1, 'rgba(0, 180, 255, 0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cluster.x, cluster.y, 24, 0, Math.PI * 2);
        ctx.fill();

        // High intensity core
        ctx.fillStyle = '#ffffff';
        ctx.shadowColor = '#00f0ff';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(cluster.x, cluster.y, 3.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0; // reset

        // Draw small scattered noisy points around the core
        ctx.fillStyle = 'rgba(0, 235, 255, 0.8)';
        for (let i = 0; i < 18; i++) {
          const angle = Math.random() * Math.PI * 2;
          const r = Math.pow(Math.random(), 1.8) * 14;
          const px = cluster.x + Math.cos(angle) * r;
          const py = cluster.y + Math.sin(angle) * r;
          ctx.beginPath();
          ctx.arc(px, py, 1, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      tick++;
      // Subtle redraw rate for smooth twinkle
      setTimeout(() => {
        animationId = requestAnimationFrame(render);
      }, 70);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <div className="relative w-full h-full flex flex-col">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-300">Constellation</span>
        <span className="text-[10px] text-slate-400 font-mono">I / Q</span>
      </div>
      <div className="relative flex-1 rounded-lg overflow-hidden border border-[#1b2b4d] bg-[#060c1c] flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={180}
          height={130}
          className="w-full h-full block"
        />
      </div>
    </div>
  );
}

