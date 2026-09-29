'use client';

import React, { useMemo, useState } from 'react';

function encodeHamming74(data: string) {
  const bits = Array<number>(8).fill(0);
  [3, 5, 6, 7].forEach((position, index) => { bits[position] = Number(data[index] ?? 0); });
  for (const parityPosition of [1, 2, 4]) {
    let parity = 0;
    for (let position = 1; position <= 7; position++) {
      if ((position & parityPosition) !== 0 && position !== parityPosition) parity ^= bits[position];
    }
    bits[parityPosition] = parity;
  }
  return bits.slice(1).join('');
}

export function HammingDemo() {
  const [data, setData] = useState('1011');
  const [errorPosition, setErrorPosition] = useState('5');
  const result = useMemo(() => {
    const encoded = encodeHamming74(data);
    const receivedBits = encoded.split('').map(Number);
    const position = Number(errorPosition);
    if (position >= 1 && position <= 7) receivedBits[position - 1] ^= 1;
    let syndrome = 0;
    for (const parityPosition of [1, 2, 4]) {
      let parity = 0;
      for (let index = 1; index <= 7; index++) if ((index & parityPosition) !== 0) parity ^= receivedBits[index - 1];
      if (parity) syndrome += parityPosition;
    }
    const corrected = [...receivedBits];
    if (syndrome >= 1 && syndrome <= 7) corrected[syndrome - 1] ^= 1;
    const recovered = [3, 5, 6, 7].map((index) => corrected[index - 1]).join('');
    return { encoded, received: receivedBits.join(''), syndrome, corrected: corrected.join(''), recovered };
  }, [data, errorPosition]);

  return (
    <details className="border border-zinc-800 bg-zinc-950/50">
      <summary className="cursor-pointer list-none px-4 py-3 text-xs font-medium text-zinc-300 marker:hidden">
        <span className="mr-2 text-cyan-400">+</span>Try the Hamming(7,4) correction demo
        <span className="ml-2 text-[10px] text-zinc-600">Browser-only example</span>
      </summary>
      <div className="grid gap-5 border-t border-zinc-800 p-4 lg:grid-cols-[240px_1fr]">
        <div className="space-y-3">
          <label className="block text-xs text-zinc-400">4-bit input<input value={data} maxLength={4} inputMode="numeric" onChange={(event) => setData(event.target.value.replace(/[^01]/g, '').slice(0, 4))} className="mt-1.5 w-full border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-cyan-700" /></label>
          <label className="block text-xs text-zinc-400">Flip bit on transmission<select value={errorPosition} onChange={(event) => setErrorPosition(event.target.value)} className="mt-1.5 w-full border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-white"><option value="0">No error</option>{[1, 2, 3, 4, 5, 6, 7].map((position) => <option key={position} value={position}>Position {position}</option>)}</select></label>
          <p className="font-sans text-[11px] leading-relaxed text-zinc-500">Hamming(7,4) uses even parity and corrects a single flipped bit. This teaching example is separate from the recording’s recovery output.</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {[["Encoded", result.encoded], ["Received", result.received], ["Syndrome", result.syndrome.toString(2).padStart(3, '0')], ["Corrected", result.corrected], ["Recovered", result.recovered]].map(([label, value]) => <div key={label} className="border border-zinc-800 bg-[#0c0c0e] p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-500">{label}</span><strong className="mt-2 block break-all font-mono text-sm text-cyan-200">{value}</strong>{label === 'Syndrome' && <span className="mt-1 block text-[10px] text-zinc-600">error at bit {result.syndrome || 'none'}</span>}</div>)}
        </div>
      </div>
    </details>
  );
}
