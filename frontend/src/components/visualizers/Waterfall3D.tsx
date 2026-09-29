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

        const rows = Math.min(32, frames.length);
        const columns = Math.min(96, Math.min(...frames.map((row) => row.length)));
        const positions = new Float32Array(rows * columns * 3);
        const colors = new Float32Array(rows * columns * 3);
        const low = Math.min(...frames.flatMap((row) => row.slice(0, columns)));
        const high = Math.max(...frames.flatMap((row) => row.slice(0, columns)));
        const span = Math.max(1, high - low);
        for (let row = 0; row < rows; row++) {
          const sourceRow = frames[Math.floor((row / Math.max(1, rows - 1)) * (frames.length - 1))];
          for (let col = 0; col < columns; col++) {
            const sourceCol = Math.floor((col / Math.max(1, columns - 1)) * (sourceRow.length - 1));
            const index = row * columns + col;
            const intensity = (sourceRow[sourceCol] - low) / span;
            positions[index * 3] = col / Math.max(1, columns - 1) - 0.5;
            positions[index * 3 + 1] = intensity * 0.55;
            positions[index * 3 + 2] = row / Math.max(1, rows - 1) - 0.5;
            const color = new THREE.Color().setHSL(0.56 - intensity * 0.45, 0.86, 0.18 + intensity * 0.52);
            colors[index * 3] = color.r;
            colors[index * 3 + 1] = color.g;
            colors[index * 3 + 2] = color.b;
          }
        }
        const indices: number[] = [];
        for (let row = 0; row < rows - 1; row++) for (let col = 0; col < columns - 1; col++) {
          const a = row * columns + col;
          const b = a + columns;
          indices.push(a, b, a + 1, b, b + 1, a + 1);
        }
        geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setIndex(indices);
        geometry.computeVertexNormals();
        const surface = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, wireframe: true }));
        scene.add(surface);
        const grid = new THREE.GridHelper(1.2, 12, '#155e75', '#27272a');
        grid.position.y = -0.015;
        scene.add(grid);
        const draw = () => {
          if (disposed || !renderer) return;
          controlsInstance.update();
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
