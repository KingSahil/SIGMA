'use client';

import React from 'react';
import {
  Activity,
  Binary,
  Check,
  ChevronRight,
  Fingerprint,
  Radio,
  ShieldCheck,
} from 'lucide-react';

const sectionLabel = 'font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-400';
const mono = 'font-mono text-[10px] uppercase tracking-[0.12em]';

function SectionIntro({ label, title, description }: { label: string; title: React.ReactNode; description: string }) {
  return (
    <div className="max-w-2xl">
      <p className={sectionLabel}>{label}</p>
      <h2 className="mt-4 text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-[44px]">{title}</h2>
      <p className="mt-5 max-w-xl text-sm leading-7 text-slate-400 sm:text-base">{description}</p>
    </div>
  );
}

function SpectrumVisual() {
  return (
    <div className="h-24 border border-slate-800 bg-[#060b18] p-3" aria-label="Mini spectrum visualization">
      <div className="flex h-full items-end gap-1 border-b border-l border-slate-800 px-2 pb-1">
        {[16, 22, 18, 28, 20, 34, 56, 78, 46, 27, 22, 33, 62, 42, 24, 18, 25, 21, 30, 19].map((height, index) => (
          <span key={index} className={`w-full ${index === 7 || index === 12 ? 'bg-cyan-300' : 'bg-cyan-500/45'}`} style={{ height: `${height}%` }} />
        ))}
      </div>
    </div>
  );
}

function ConstellationVisual() {
  return (
    <div className="relative h-24 overflow-hidden border border-slate-800 bg-[#060b18]" aria-label="Mini I/Q constellation visualization">
      <div className="absolute inset-x-4 top-1/2 border-t border-slate-800" />
      <div className="absolute inset-y-3 left-1/2 border-l border-slate-800" />
      <div className="absolute left-[24%] top-[25%] h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(103,232,249,0.8)]" />
      <div className="absolute right-[24%] top-[25%] h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(103,232,249,0.8)]" />
      <div className="absolute bottom-[25%] left-[24%] h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(103,232,249,0.8)]" />
      <div className="absolute bottom-[25%] right-[24%] h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(103,232,249,0.8)]" />
    </div>
  );
}

function DecodeVisual() {
  return (
    <div className="flex h-24 items-center justify-between border border-slate-800 bg-[#060b18] px-3" aria-label="Signal to symbols to bits pipeline">
      {['RF', 'SYMBOLS', 'BITS'].map((item, index) => (
        <React.Fragment key={item}>
          <div className="flex h-10 items-center border border-cyan-500/30 px-2 text-cyan-300"><span className={mono}>{item}</span></div>
          {index < 2 && <ChevronRight className="h-4 w-4 text-slate-600" />}
        </React.Fragment>
      ))}
    </div>
  );
}

function BitsVisual() {
  return (
    <div className="h-24 border border-slate-800 bg-[#060b18] p-3 font-mono text-[10px] leading-5" aria-label="Error correction visualization">
      <div className="text-rose-300/70">1011 0010 1100 0110</div>
      <div className="my-1 text-slate-600">────── correction pass ──────</div>
      <div className="text-emerald-300">1011 0010 1000 0110</div>
    </div>
  );
}

function FingerprintVisual() {
  return (
    <div className="relative h-24 overflow-hidden border border-slate-800 bg-[#060b18] p-3" aria-label="Signal fingerprint visualization">
      <div className="absolute inset-x-3 top-1/2 h-px bg-slate-800" />
      <div className="absolute inset-x-3 top-1/2 h-px origin-left -rotate-6 bg-cyan-400/80 shadow-[0_0_10px_rgba(34,211,238,0.5)]" />
      <div className="absolute left-4 top-4 border border-cyan-500/30 px-2 py-1 text-cyan-300"><span className={mono}>FP-7A3C</span></div>
    </div>
  );
}

function ErrorVisual() {
  return (
    <div className="grid h-24 grid-cols-2 gap-2 border border-slate-800 bg-[#060b18] p-3" aria-label="Error control visualization">
      <div className="border border-slate-800 p-2 text-[10px] text-slate-500"><Binary className="mb-1 h-4 w-4 text-cyan-400" />CRC / HAMMING</div>
      <div className="border border-emerald-500/30 p-2 text-[10px] text-emerald-300"><Check className="mb-1 h-4 w-4" />FRAME VALID</div>
    </div>
  );
}

const features = [
  { number: '01', title: 'Spectrum Analysis', subtitle: 'FFT-Powered Frequency Analysis', description: 'Visualize signal energy across the frequency domain and identify dominant frequencies, bandwidth, spectral peaks, and signal characteristics.', icon: Activity, visual: <SpectrumVisual /> },
  { number: '02', title: 'Modulation Identification', subtitle: 'Automatic Modulation Detection', description: 'Identify digital modulation schemes from signal characteristics and constellation behavior.', icon: Activity, visual: <ConstellationVisual /> },
  { number: '03', title: 'Demodulation & Decoding', subtitle: 'Recover the Hidden Data', description: 'Process detected signals through demodulation and decoding stages to reconstruct underlying digital information.', icon: Binary, visual: <DecodeVisual /> },
  { number: '04', title: 'FEC & De-interleaving', subtitle: 'Error Correction Intelligence', description: 'Analyze Forward Error Correction and de-interleaving stages to improve communication reliability and recover data from noisy transmissions.', icon: ShieldCheck, visual: <BitsVisual /> },
  { number: '05', title: 'Signal Fingerprinting', subtitle: 'Create a Signal Identity', description: 'Generate measurable signal fingerprints from characteristics such as frequency, bandwidth, modulation, and signal behavior.', icon: Fingerprint, visual: <FingerprintVisual /> },
  { number: '06', title: 'Error Control Lab', subtitle: 'Understand Communication Reliability', description: 'Explore parity, Hamming distance, CRC, checksums, bit stuffing, frame formation, and ARQ concepts through interactive analysis.', icon: Fingerprint, visual: <ErrorVisual /> },
];

function FeatureCard({ feature }: { feature: (typeof features)[number] }) {
  const Icon = feature.icon;
  return (
    <article className="group border border-slate-800 bg-[#07101f]/70 p-5 transition-colors hover:border-cyan-500/45 hover:bg-[#09172a]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3"><span className={`${mono} text-cyan-500`}>{feature.number}</span><Icon className="h-4 w-4 text-slate-500 transition-colors group-hover:text-cyan-300" /></div>
        <span className="font-mono text-[9px] text-slate-600">SIG / CAPABILITY</span>
      </div>
      <h3 className="mt-6 text-lg font-semibold text-white">{feature.title}</h3>
      <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.1em] text-cyan-300/80">{feature.subtitle}</p>
      <p className="mt-3 min-h-[72px] text-sm leading-6 text-slate-400">{feature.description}</p>
      <div className="mt-5">{feature.visual}</div>
    </article>
  );
}

function FlowColumn({ title, steps, accent = false }: { title: string; steps: string[]; accent?: boolean }) {
  return (
    <div className={`border p-5 ${accent ? 'border-cyan-500/35 bg-cyan-950/10' : 'border-slate-800 bg-[#07101f]/50'}`}>
      <div className="flex items-center justify-between border-b border-slate-800 pb-3"><span className={`${mono} ${accent ? 'text-cyan-300' : 'text-slate-400'}`}>{title}</span><span className="font-mono text-[9px] text-slate-600">FLOW / 0{steps.length}</span></div>
      <div className="mt-5 space-y-2">
        {steps.map((step, index) => <React.Fragment key={step}><div className={`border px-3 py-2.5 font-mono text-[11px] ${accent ? 'border-cyan-500/25 text-cyan-100' : 'border-slate-800 text-slate-400'}`}>{step}</div>{index < steps.length - 1 && <div className={`ml-5 h-4 border-l ${accent ? 'border-cyan-500/40' : 'border-slate-700'}`} />}</React.Fragment>)}
      </div>
    </div>
  );
}

const processSteps = [
  { number: '01', label: 'UPLOAD SIGNAL', title: 'Import IQ or WAV', description: 'Upload a recorded RF signal and provide available capture parameters such as sample rate and center frequency.', tags: ['IQ', 'WAV'], icon: UploadIcon },
  { number: '02', label: 'ANALYZE', title: 'Inspect the Signal', description: 'Examine time-domain and frequency-domain characteristics using waveform, spectrum, spectrogram, and I/Q visualizations.', tags: ['TIME DOMAIN', 'FFT', 'SPECTROGRAM', 'I/Q'], icon: Radio },
  { number: '03', label: 'IDENTIFY', title: 'Extract Signal Characteristics', description: 'Determine measurable parameters including modulation, sampling rate, carrier frequency, bandwidth, and SNR.', tags: [], icon: Activity },
  { number: '04', label: 'DECODE', title: 'Process the Communication Chain', description: 'Apply supported demodulation, synchronization, de-interleaving, FEC, and frame-level processing stages.', tags: ['RF SIGNAL', 'SYMBOLS', 'BITS', 'FEC'], icon: Binary },
  { number: '05', label: 'REPORT', title: 'Generate Structured Results', description: 'Convert the analysis into a readable signal report containing extracted parameters, processing results, and signal fingerprints.', tags: ['PARAMETERS', 'ANALYSIS', 'FINGERPRINT', 'RESULTS'], icon: Activity },
];

function UploadIcon(props: React.ComponentProps<typeof Radio>) { return <Radio {...props} />; }

function ParameterPanel() {
  return <div className="mt-5 grid grid-cols-2 border border-slate-800 bg-[#060b18] font-mono text-[10px] sm:grid-cols-5"><span className="border-b border-slate-800 p-3 text-slate-500 sm:border-b-0 sm:border-r">MODULATION<strong className="mt-1 block text-cyan-300">QPSK</strong></span><span className="border-b border-slate-800 p-3 text-slate-500 sm:border-b-0 sm:border-r">SAMPLE RATE<strong className="mt-1 block text-white">2.4 MS/s</strong></span><span className="border-b border-slate-800 p-3 text-slate-500 sm:border-b-0 sm:border-r">CENTER FREQ<strong className="mt-1 block text-white">433.92 MHz</strong></span><span className="border-b border-slate-800 p-3 text-slate-500 sm:border-b-0 sm:border-r">BANDWIDTH<strong className="mt-1 block text-white">1.8 MHz</strong></span><span className="p-3 text-slate-500">SNR<strong className="mt-1 block text-emerald-300">18.4 dB</strong></span></div>;
}

function ArchitectureDiagram() {
  const nodes = ['SPECTRUM', 'MODULATION', 'DEMOD', 'I/Q'];
  return <div className="border border-slate-800 bg-[#060b18] p-5"><div className="mx-auto w-fit border border-cyan-500/40 px-6 py-2 font-mono text-xs text-cyan-200">SIGNALFORGE</div><div className="mx-auto h-7 w-px bg-cyan-500/45" /><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{nodes.map((node) => <div key={node} className="border border-slate-800 px-2 py-3 text-center font-mono text-[10px] text-slate-400">{node}</div>)}</div><div className="mx-auto h-7 w-px bg-cyan-500/45" /><div className="mx-auto max-w-xs space-y-2 text-center font-mono text-[10px] text-slate-400"><div className="border border-slate-800 px-3 py-2">FEC / DECODING</div><div className="border border-slate-800 px-3 py-2">FRAME CORRELATION</div><div className="border border-cyan-500/35 px-3 py-2 text-cyan-200">SIGNAL FINGERPRINT</div><div className="border border-cyan-500/35 px-3 py-2 text-cyan-200">SIGNAL INTELLIGENCE</div><div className="border border-slate-800 px-3 py-2">FINAL REPORT</div></div></div>;
}

const useCases = [
  { number: '01', title: 'Satellite & Space Communication', description: 'Analyze satellite and CubeSat telemetry captures to investigate modulation, frequency characteristics, signal quality, and transmission parameters.', icon: Radio, meta: 'TELEMETRY / UHF' },
  { number: '02', title: 'RF & Wireless Research', description: 'Analyze captured RF recordings across HF, VHF, and UHF ranges to investigate signal behavior and communication characteristics.', icon: Radio, meta: 'HF / VHF / UHF' },
  { number: '03', title: 'Aerospace & Telemetry', description: 'Examine telemetry recordings through modulation, demodulation, synchronization, and error-control stages.', icon: Radio, meta: 'CHAIN / RECOVERY' },
  { number: '04', title: 'Academic & Laboratory Research', description: 'Experiment with modulation, IQ generation, error correction, Hamming distance, CRC, and frame formation in a controlled environment.', icon: Fingerprint, meta: 'LAB / EXPERIMENT' },
  { number: '05', title: 'Communication Diagnostics', description: 'Examine SNR, bandwidth, spectral characteristics, and error-control behavior to understand transmission performance.', icon: Activity, meta: 'SNR / QUALITY' },
];

export type LandingPage = 'all' | 'features' | 'how-it-works' | 'use-cases' | 'about';

export function LandingSections({ page = 'all', onUploadSignal, onOpenLab }: { page?: LandingPage; onUploadSignal: () => void; onOpenLab: () => void }) {
  return (
    <main className={`landing-sections landing-sections--${page} bg-[#040814] text-white`}>
      <section id="features" className="scroll-mt-8 border-b border-slate-800/80 bg-[#050b18] py-20 sm:py-28"><div className="mx-auto max-w-7xl px-6 xl:px-12"><SectionIntro label="SIGNAL ANALYSIS CAPABILITIES" title={<>Powerful Signal Intelligence,<br /><span className="text-slate-400">From IQ to Insight</span></>} description="Analyze, identify, decode, and understand complex RF signals through an integrated signal-processing workflow." /><div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{features.map((feature) => <FeatureCard key={feature.number} feature={feature} />)}</div></div></section>

      <section className="border-b border-slate-800/80 py-20 sm:py-28"><div className="mx-auto max-w-7xl px-6 xl:px-12"><SectionIntro label="THE SIGNALFORGE APPROACH" title={<>One Signal.<br />One Pipeline.<br /><span className="text-slate-400">Complete Visibility.</span></>} description="SignalForge brings multiple stages of RF signal analysis into a unified workflow, reducing the need to move between disconnected analysis tools." /><div className="relative mt-12 grid gap-5 lg:grid-cols-2"><FlowColumn title="TRADITIONAL WORKFLOW" steps={['RAW CAPTURE', 'SEPARATE ANALYSIS TOOLS', 'MANUAL PARAMETER EXTRACTION', 'SEPARATE DECODING TOOLS', 'SCATTERED RESULTS']} /><FlowColumn title="SIGNALFORGE" accent steps={['IQ / WAV', 'SIGNAL ANALYSIS', 'PARAMETER EXTRACTION', 'MODULATION', 'DEMODULATION', 'FEC / DECODING', 'SIGNAL INTELLIGENCE']} /><div className="pointer-events-none absolute left-1/2 top-1/2 hidden h-px w-10 -translate-x-1/2 bg-cyan-400/70 lg:block" /></div></div></section>

      <section id="how-it-works" className="scroll-mt-8 border-b border-slate-800/80 bg-[#050b18] py-20 sm:py-28"><div className="mx-auto max-w-7xl px-6 xl:px-12"><SectionIntro label="FROM CAPTURE TO INTELLIGENCE" title={<>From Raw Signal<br /><span className="text-slate-400">to Actionable Intelligence</span></>} description="SignalForge transforms IQ and WAV recordings into structured signal intelligence through a guided signal-processing pipeline." /><div className="mt-12 grid gap-4 lg:grid-cols-5">{processSteps.map((step) => { const Icon = step.icon; return <article key={step.number} className="relative border border-slate-800 bg-[#07101f]/70 p-4"><div className="flex items-center justify-between"><span className={`${mono} text-cyan-500`}>{step.number}</span><Icon className="h-4 w-4 text-slate-500" /></div><p className="mt-7 font-mono text-[10px] tracking-[0.16em] text-cyan-300">{step.label}</p><h3 className="mt-2 text-base font-semibold text-white">{step.title}</h3><p className="mt-3 text-sm leading-6 text-slate-400">{step.description}</p>{step.number === '03' ? <ParameterPanel /> : <div className="mt-5 flex flex-wrap gap-1.5">{step.tags.map((tag) => <span key={tag} className="border border-slate-700 px-2 py-1 font-mono text-[9px] text-slate-400">{tag}</span>)}</div>}</article>; })}</div></div></section>

      <section id="use-cases" className="scroll-mt-8 border-b border-slate-800/80 py-20 sm:py-28"><div className="mx-auto max-w-7xl px-6 xl:px-12"><SectionIntro label="APPLICATIONS" title={<>Built for Real-World<br /><span className="text-slate-400">Signal Analysis</span></>} description="Explore how SignalForge can support RF analysis, telemetry investigation, communication research, and signal-processing education." /><div className="mt-12 grid gap-3 lg:grid-cols-5">{useCases.map((item) => { const Icon = item.icon; return <article key={item.number} className="group border border-slate-800 bg-[#07101f]/50 p-5 transition-colors hover:border-cyan-500/40"><div className="flex items-center justify-between"><span className={`${mono} text-cyan-500`}>{item.number}</span><Icon className="h-5 w-5 text-slate-500 group-hover:text-cyan-300" /></div><p className="mt-8 font-mono text-[9px] tracking-[0.16em] text-slate-500">{item.meta}</p><h3 className="mt-2 text-lg font-semibold leading-snug text-white">{item.title}</h3><p className="mt-3 text-sm leading-6 text-slate-400">{item.description}</p><div className="mt-8 h-10 border-t border-slate-800 pt-3"><div className="h-px w-2/3 bg-cyan-500/40 transition-all group-hover:w-full" /></div></article>; })}</div></div></section>

      <section id="about" className="scroll-mt-8 border-b border-slate-800/80 bg-[#050b18] py-20 sm:py-28"><div className="mx-auto grid max-w-7xl gap-12 px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-start xl:px-12"><SectionIntro label="ABOUT SIGNALFORGE" title={<>Making Complex Signals<br /><span className="text-slate-400">Understandable</span></>} description="SignalForge is an integrated RF signal-analysis platform designed to transform complex IQ and WAV recordings into structured signal intelligence. Instead of moving between disconnected tools for spectral analysis, modulation identification, demodulation, error-control analysis, and signal fingerprinting, SignalForge brings these stages together into a unified workflow." /><ArchitectureDiagram /></div></section>

      <section className="border-b border-slate-800/80 py-16 sm:py-20"><div className="mx-auto max-w-7xl px-6 xl:px-12"><div className="flex flex-col justify-between gap-6 border-b border-slate-800 pb-8 sm:flex-row sm:items-end"><div><p className={sectionLabel}>ENGINEERED FOR SIGNAL ANALYSIS</p><h2 className="mt-4 text-2xl font-bold tracking-tight text-white sm:text-3xl">Built Around the Signal,<br /><span className="text-slate-400">Not Around the Interface</span></h2></div><p className="max-w-sm text-sm leading-6 text-slate-500">Measured capabilities for a practical signal-processing workflow.</p></div><div className="mt-7 flex flex-wrap gap-2">{['IQ FILES', 'WAV FILES', 'FFT', 'SPECTROGRAM', 'I/Q ANALYSIS', 'MODULATION', 'DEMODULATION', 'FEC', 'DE-INTERLEAVING', 'FRAME CORRELATION', 'SIGNAL FINGERPRINTING', 'SNR', 'BANDWIDTH', 'CARRIER FREQUENCY', 'SAMPLE RATE'].map((item) => <span key={item} className="border border-slate-800 bg-[#07101f] px-3 py-2 font-mono text-[10px] text-slate-400">{item}</span>)}</div></div></section>

      <section className="relative overflow-hidden py-24 sm:py-32"><div className="absolute inset-y-0 right-0 w-1/2 border-l border-cyan-500/10 bg-cyan-500/[0.02]" /><div className="relative mx-auto max-w-7xl px-6 xl:px-12"><div className="max-w-3xl"><p className={sectionLabel}>SIGNALFORGE / NEXT CAPTURE</p><h2 className="mt-5 text-4xl font-bold leading-tight tracking-tight text-white sm:text-6xl">Ready to Decode<br /><span className="text-cyan-300">the Invisible?</span></h2><p className="mt-6 max-w-xl text-base leading-7 text-slate-400">Upload a signal and move from raw RF data to structured signal intelligence.</p><div className="mt-9 flex flex-wrap gap-3"><button onClick={onUploadSignal} className="flex items-center gap-2 bg-cyan-400 px-5 py-3 font-mono text-xs font-semibold text-slate-950 transition-colors hover:bg-cyan-300">UPLOAD A SIGNAL <ChevronRight className="h-4 w-4" /></button><button onClick={onOpenLab} className="flex items-center gap-2 border border-slate-700 px-5 py-3 font-mono text-xs text-slate-300 transition-colors hover:border-cyan-500/60 hover:text-white">EXPLORE THE PIPELINE <ChevronRight className="h-4 w-4" /></button></div><p className="mt-8 font-mono text-[10px] tracking-[0.18em] text-slate-600">IQ · WAV · FFT · MODULATION · DEMODULATION · FEC · FINGERPRINTING</p></div></div></section>
    </main>
  );
}
