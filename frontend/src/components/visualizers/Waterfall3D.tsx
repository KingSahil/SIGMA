'use client';

import { useEffect, useRef, useState } from 'react';

export function Waterfall3D({ frames }: { frames: number[][] }) {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let disposed = false;
    let renderer: import('three').WebGLRenderer | undefined;
    let controls: { dispose: () => void } | undefined;
    let geometry: import('three').BufferGeometry | undefined;
    let animation = 0;
    const mount = host.current;
    if (!mount || !frames.length) return;
    setError(false);

    void (async () => {
      try {
        const THREE = await import('three');
        const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
        if (disposed || !mount) return;
        const width = Math.max(320, mount.clientWidth);
        const height = Math.max(180, mount.clientHeight);
        const scene = new THREE.Scene();
        scene.background = new THREE.Color('#09090b');
        const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 100);
        camera.position.set(0, 1.25, 2.35);
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(width, height);
        mount.appendChild(renderer.domElement);
        const controlsInstance = new OrbitControls(camera, renderer.domElement);
        controlsInstance.enableDamping = true;
        controlsInstance.target.set(0, 0.1, 0);
        controls = controlsInstance;

        const validFrames = frames.filter((row) => row.length > 0);
        if (!validFrames.length) throw new Error('Waterfall has no populated rows');
        const rows = Math.min(32, validFrames.length);
        const columns = Math.min(96, Math.min(...validFrames.map((row) => row.length)));
        if (columns < 2) throw new Error('Waterfall has too few frequency bins');
        const positions = new Float32Array(rows * columns * 3);
        const colors = new Float32Array(rows * columns * 3);
        let low = Number.POSITIVE_INFINITY;
        let high = Number.NEGATIVE_INFINITY;
        for (const row of validFrames) {
          for (let col = 0; col < columns; col += 1) {
            const value = Number(row[col]);
            if (!Number.isFinite(value)) continue;
            low = Math.min(low, value);
            high = Math.max(high, value);
          }
        }
        const span = Math.max(1, high - low);
        for (let row = 0; row < rows; row += 1) {
          const sourceRow = validFrames[Math.floor((row / Math.max(1, rows - 1)) * (validFrames.length - 1))];
          for (let col = 0; col < columns; col += 1) {
            const sourceCol = Math.floor((col / Math.max(1, columns - 1)) * (sourceRow.length - 1));
            const index = row * columns + col;
            const value = Number(sourceRow[sourceCol]);
            const intensity = Number.isFinite(value) ? Math.max(0, Math.min(1, (value - low) / span)) : 0;
            positions[index * 3] = col / (columns - 1) - 0.5;
            positions[index * 3 + 1] = intensity * 0.55;
            positions[index * 3 + 2] = row / Math.max(1, rows - 1) - 0.5;
            const color = new THREE.Color().setHSL(0.56 - intensity * 0.45, 0.86, 0.18 + intensity * 0.52);
            colors[index * 3] = color.r;
            colors[index * 3 + 1] = color.g;
            colors[index * 3 + 2] = color.b;
          }
        }
        const indices: number[] = [];
        for (let row = 0; row < rows - 1; row += 1) for (let col = 0; col < columns - 1; col += 1) {
          const a = row * columns + col;
          const b = a + columns;
          indices.push(a, b, a + 1, b, b + 1, a + 1);
        }
        geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setIndex(indices);
        const surface = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, wireframe: true }));
        scene.add(surface);
        const grid = new THREE.GridHelper(1.2, 12, '#155e75', '#27272a');
        grid.position.y = -0.015;
        scene.add(grid);
        const draw = () => {
          if (disposed || !renderer) return;
          controlsInstance.update();`r`n          surface.rotation.y += 0.0015;
          renderer.render(scene, camera);
          animation = requestAnimationFrame(draw);
        };
        draw();
      } catch {
        if (!disposed) setError(true);
      }
    })();

    return () => {
      disposed = true;
      cancelAnimationFrame(animation);
      controls?.dispose();
      geometry?.dispose();
      renderer?.dispose();
      if (renderer?.domElement.parentElement === mount) mount.removeChild(renderer.domElement);
    };
  }, [frames]);

  if (error) return <div className="flex h-full items-center justify-center text-xs text-zinc-500">3D rendering is not available in this browser.</div>;
  return <div ref={host} className="h-full w-full" aria-label="Interactive 3D waterfall. Drag to rotate." />;
}