'use client';

import { useMemo, useState } from 'react';

const stages = [
  ['Phase 1', 'Parity, Hamming distance & Hamming(7,4)'],
  ['Phase 2', 'CRC-8 & checksum'],
  ['Phase 3', 'Bit stuffing & frame formation'],
  ['Phase 4', 'ARQ reliability'],
  ['Phase 5', 'Complete error-control simulator'],
] as const;

function divideCrc(data: string, polynomial: string) {
  const bits = [...`${data}${'0'.repeat(polynomial.length - 1)}`].map(Number);
  const poly = [...polynomial].map(Number);
  for (let i = 0; i <= bits.length - poly.length; i++) {
    if (bits[i]) for (let j = 0; j < poly.length; j++) bits[i + j] ^= poly[j];
  }
  return bits.slice(-(poly.length - 1)).join('');
}

function checksum8(data: string) {
  let sum = 0;
  for (let offset = 0; offset < data.length; offset += 8) {
    sum += Number.parseInt(data.slice(offset, offset + 8).padEnd(8, '0'), 2);
  }
  while (sum > 0xff) sum = (sum & 0xff) + (sum >>> 8);
  return ((~sum) & 0xff).toString(2).padStart(8, '0');
}

function hammingEncode74(data: string) {
  const code = Array<number>(8).fill(0);
  [3, 5, 6, 7].forEach((position, index) => { code[position] = Number(data[index] ?? 0); });
  for (const parityPosition of [1, 2, 4]) {
    for (let position = 1; position <= 7; position++) if (position !== parityPosition && (position & parityPosition)) code[parityPosition] ^= code[position];
  }
  return code.slice(1);
}

function hammingDecode74(received: number[]) {
  const corrected = [...received];
  let syndrome = 0;
  for (const parityPosition of [1, 2, 4]) {
    let parity = 0;
    for (let position = 1; position <= 7; position++) if (position & parityPosition) parity ^= corrected[position - 1];
    if (parity) syndrome += parityPosition;
  }
  if (syndrome >= 1 && syndrome <= 7) corrected[syndrome - 1] ^= 1;
  return { syndrome, corrected, data: [3, 5, 6, 7].map((position) => corrected[position - 1]).join('') };
}

export function ErrorControlLab() {
  const [phase, setPhase] = useState(0);
  const [bits, setBits] = useState('10110010');
  const [compareBits, setCompareBits] = useState('10110110');
  const [arq, setArq] = useState<'stop' | 'gbn' | 'sr'>('stop');
  const [loss, setLoss] = useState(2);
  const [errorPosition, setErrorPosition] = useState(0);
  const [secondError, setSecondError] = useState(false);
  const cleanBits = bits.replace(/[^01]/g, '').slice(0, 64);
  const cleanCompare = compareBits.replace(/[^01]/g, '').slice(0, 64);
  const parity = cleanBits.split('').reduce((sum, bit) => sum ^ Number(bit), 0);
  const distance = Math.max(cleanBits.length, cleanCompare.length);
  const hammingDistance = Array.from({ length: distance }, (_, i) => cleanBits[i] !== cleanCompare[i] ? 1 : 0).reduce<number>((a, b) => a + b, 0);
  const stuffed = useMemo(() => cleanBits.replace(/11111/g, '111110'), [cleanBits]);
  const crc = divideCrc(cleanBits || '0', '100000111');
  const payload = cleanBits.slice(0, 4).padEnd(4, '0');
  const simulator = useMemo(() => {
    const transmitted = hammingEncode74(payload);
    if (errorPosition) transmitted[errorPosition - 1] ^= 1;
    const secondPosition = errorPosition === 1 ? 7 : 1;
    if (secondError) transmitted[secondPosition - 1] ^= 1;
    const decoded = hammingDecode74(transmitted);
    const crcValid = divideCrc(`${decoded.data}00000000`, '100000111') === divideCrc(`${payload}00000000`, '100000111') && decoded.data === payload;
    return { encoded: hammingEncode74(payload).join(''), received: transmitted.join(''), ...decoded, crcValid, retry: !crcValid };
  }, [payload, errorPosition, secondError]);
  const retryText = arq === 'stop'
    ? `Frame ${loss} is retransmitted, then the sender waits for its acknowledgement before continuing.`
    : arq === 'gbn'
      ? `A loss at frame ${loss} causes that frame and every later unacknowledged frame in the window to be resent.`
      : `Only missing frame ${loss} is retransmitted; correctly received frames are retained in the receive window.`;

  return (
    <section className="space-y-5">
      <header className="border-b border-zinc-800 pb-5">
        <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-400">Interactive learning tools</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">Error control lab</h2>
        <p className="mt-1 max-w-2xl font-sans text-sm text-zinc-400">Explore the stages from bit-error checks to reliable frame delivery. Examples run locally in your browser and are separate from recording analysis.</p>
      </header>
      <div className="grid gap-2 sm:grid-cols-4" role="tablist" aria-label="Error control phases">
        {stages.map(([label, title], i) => <button key={label} role="tab" aria-selected={phase === i} onClick={() => setPhase(i)} className={`border px-3 py-3 text-left ${phase === i ? 'border-cyan-800 bg-cyan-950/20' : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'}`}><span className="block text-[10px] uppercase tracking-wider text-zinc-500">{label}</span><span className="mt-1 block text-xs text-zinc-200">{title}</span></button>)}
      </div>
      <div className="border border-zinc-800 bg-[#0c0c0e] p-4 sm:p-5">
        <label className="block max-w-xl text-xs text-zinc-400">Input bit stream<input aria-label="Input bit stream" value={bits} onChange={(e) => setBits(e.target.value.replace(/[^01]/g, '').slice(0, 64))} className="mt-1.5 w-full border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-sm text-cyan-200" /></label>
        {phase === 0 && <div className="mt-5 grid gap-4 md:grid-cols-3">
          <Result label="Even parity bit" value={String(parity)} detail={`Append ${parity} to make the total number of 1 bits even.`} />
          <Result label="Odd parity bit" value={String(parity ^ 1)} detail={`Append ${parity ^ 1} to make the total number of 1 bits odd.`} />
          <div className="border border-zinc-800 bg-zinc-950 p-3"><label className="text-[10px] uppercase tracking-wider text-zinc-500">Compare for Hamming distance<input aria-label="Second bit stream" value={compareBits} onChange={(e) => setCompareBits(e.target.value.replace(/[^01]/g, '').slice(0, 64))} className="mt-2 w-full border border-zinc-700 bg-[#0c0c0e] px-2 py-1.5 font-mono text-xs text-white" /></label><strong className="mt-3 block text-xl text-cyan-200">{hammingDistance} bit{hammingDistance === 1 ? '' : 's'}</strong><p className="mt-1 text-[11px] text-zinc-500">{cleanBits.length === cleanCompare.length ? 'Different positions' : 'Unequal lengths are padded as mismatches'}</p></div>
        </div>}
        {phase === 1 && <div className="mt-5 grid gap-4 md:grid-cols-2"><Result label="CRC-8 remainder" value={crc} detail="Generator polynomial 0x07 (x⁸ + x² + x + 1). Append the remainder to form a codeword." /><Result label="8-bit one's-complement checksum" value={checksum8(cleanBits)} detail="Sum the payload's 8-bit words with end-around carry, then complement the result." /></div>}
        {phase === 2 && <div className="mt-5 grid gap-4 md:grid-cols-2"><Result label="Stuffed payload" value={stuffed} detail="A zero is inserted after each run of five 1 bits so payload data cannot imitate the frame flag." /><Result label="HDLC-style frame" value={`01111110 ${stuffed || '—'} 01111110`} detail="Opening and closing 01111110 flags bracket the stuffed payload." /></div>}
        {phase === 3 && <div className="mt-5 space-y-4"><div className="flex flex-wrap gap-2">{([['stop', 'Stop-and-Wait'], ['gbn', 'Go-Back-N'], ['sr', 'Selective Repeat']] as const).map(([id, label]) => <button key={id} onClick={() => setArq(id)} className={`border px-3 py-2 text-xs ${arq === id ? 'border-cyan-800 bg-cyan-950/30 text-white' : 'border-zinc-800 text-zinc-400'}`}>{label}</button>)}</div><label className="block max-w-sm text-xs text-zinc-400">Simulated lost frame: {loss}<input type="range" min="1" max="8" value={loss} onChange={(e) => setLoss(Number(e.target.value))} className="mt-2 block w-full accent-cyan-400" /></label><div className="border-l-2 border-cyan-700 bg-zinc-950 p-4"><p className="text-sm text-zinc-200">{retryText}</p><p className="mt-2 text-[10px] uppercase tracking-wider text-amber-400">Protocol illustration · no network transmission</p></div></div>}
        {phase === 4 && <div className="mt-5 space-y-4">
          <p className="font-sans text-xs text-zinc-400">Follow one 4-bit payload through Hamming encoding, a simulated transmission error, syndrome correction, CRC verification and the retry decision.</p>
          <div className="flex flex-wrap items-end gap-4"><label className="block text-xs text-zinc-400">Flip codeword bit<select value={errorPosition} onChange={(e) => setErrorPosition(Number(e.target.value))} className="mt-1.5 block border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-white"><option value={0}>No error</option>{[1, 2, 3, 4, 5, 6, 7].map((position) => <option key={position} value={position}>Position {position}</option>)}</select></label><label className="flex items-center gap-2 pb-2 text-xs text-zinc-400"><input type="checkbox" checked={secondError} onChange={(e) => setSecondError(e.target.checked)} className="accent-cyan-400" />Inject a second bit error</label></div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{[["Payload", payload], ["Hamming codeword", simulator.encoded], ["Received", simulator.received], ["Syndrome", simulator.syndrome.toString(2).padStart(3, '0')], ["Recovered payload", simulator.data], ["CRC check", simulator.crcValid ? 'PASS' : 'FAIL'], ["ARQ action", simulator.retry ? 'REQUEST RETRANSMISSION' : 'ACKNOWLEDGE FRAME'], ["Receiver status", simulator.retry ? 'Retry succeeds on clean channel' : 'Frame accepted']].map(([label, value]) => <div key={label} className="border border-zinc-800 bg-zinc-950 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-500">{label}</span><strong className={`mt-2 block break-all font-mono text-sm ${label === 'CRC check' && !simulator.crcValid ? 'text-amber-300' : 'text-cyan-200'}`}>{value}</strong></div>)}</div>
          <p className="font-sans text-[11px] leading-relaxed text-zinc-600">This browser simulator demonstrates a short Hamming(7,4) frame and retry decision. Production decoding still depends on the recording’s protocol, framing and connected DSP/FEC services.</p>
        </div>}
      </div>
      <p className="font-sans text-[11px] text-zinc-600">Hamming(7,4) single-bit correction is available in the FEC stage of Signal analysis. These controls demonstrate algorithms; they do not decode the selected recording.</p>
    </section>
  );
}

function Result({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="border border-zinc-800 bg-zinc-950 p-3"><span className="block text-[10px] uppercase tracking-wider text-zinc-500">{label}</span><strong className="mt-2 block break-all font-mono text-lg text-cyan-200">{value}</strong><p className="mt-2 font-sans text-[11px] leading-relaxed text-zinc-500">{detail}</p></div>;
}
