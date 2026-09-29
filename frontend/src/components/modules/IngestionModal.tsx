'use client';

import React, { useState, useRef } from 'react';
import { Upload, X, ArrowRight, Check } from 'lucide-react';
import { useSignal } from '../../context/SignalContext';

interface IngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLaunchWorkbench: () => void;
}

export function IngestionModal({
  isOpen,
  onClose,
  onLaunchWorkbench,
}: IngestionModalProps) {
  const { presets, loadPreset, uploadCustomSignal, metadata } = useSignal();
  const [selectedPresetId, setSelectedPresetId] = useState('cubesat_qpsk_433');
  const [activeTab, setActiveTab] = useState<'presets' | 'upload'>('presets');
  const [dragOver, setDragOver] = useState(false);
  const [sampleRate, setSampleRate] = useState(2400000);
  const [centerFrequencyMhz, setCenterFrequencyMhz] = useState(433.92);
  const [loadedFile, setLoadedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleSelectPreset = (id: string) => {
    setSelectedPresetId(id);
    loadPreset(id);
  };

  const loadFile = async (file: File) => {
    let detectedRate = sampleRate;
    if (file.name.toLowerCase().endsWith('.wav')) {
      try {
        const header = await file.slice(0, 44).arrayBuffer();
        const view = new DataView(header);
        const waveRate = view.byteLength >= 28 ? view.getUint32(24, true) : 0;
        if (waveRate > 0) { detectedRate = waveRate; setSampleRate(waveRate); }
      } catch { /* Keep the editable sample-rate value. */ }
    }
    setSampleRate(detectedRate);
    setLoadedFile(file);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      void loadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      void loadFile(e.target.files[0]);
    }
  };

  const handleProceed = () => {
    if (activeTab === 'upload' && loadedFile) uploadCustomSignal(loadedFile, sampleRate, centerFrequencyMhz * 1e6);
    onClose();
    onLaunchWorkbench();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#090d16] border border-slate-800 shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80">
          <div>
            <h3 className="text-base font-semibold text-white tracking-tight">
              Select Signal
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Choose a pre-recorded capture or upload your own raw file
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Clean Segmented Tabs */}
        <div className="px-6 pt-4 pb-1">
          <div className="flex p-1 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-medium">
            <button
              onClick={() => setActiveTab('presets')}
              className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeTab === 'presets'
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Preset Benchmarks
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Upload Local File
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 pt-3 space-y-3">
          {activeTab === 'presets' ? (
            <div className="space-y-2">
              {presets.map((preset) => {
                const isSelected = selectedPresetId === preset.id;
                return (
                  <div
                    key={preset.id}
                    onClick={() => handleSelectPreset(preset.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'border-cyan-500/50 bg-cyan-950/20 text-white shadow-sm'
                        : 'border-slate-800/80 bg-slate-900/40 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {/* Selection indicator */}
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-colors ${
                          isSelected
                            ? 'border-cyan-400 bg-cyan-400 text-slate-950'
                            : 'border-slate-600'
                        }`}
                      >
                        {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">
                            {preset.name}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                            {preset.format}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                          <span className="text-cyan-400 font-mono">
                            {(preset.centerFreqHz / 1e6).toFixed(2)} MHz
                          </span>
                          <span>·</span>
                          <span>{preset.defaultModulation}</span>
                          <span>·</span>
                          <span className="text-emerald-400 font-mono">{preset.snrDb} dB SNR</span>
                        </div>
                      </div>
                    </div>

                    <span className="text-xs font-mono text-slate-400">
                      {(preset.sampleRateHz / 1e6).toFixed(1)} MSps
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div>
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center text-center ${
                  dragOver
                    ? 'border-cyan-400 bg-cyan-950/20'
                    : 'border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/60'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".iq,.wav,.bin,.raw"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                <div className="w-10 h-10 rounded-lg bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-cyan-400 mb-2.5">
                  <Upload className="w-4 h-4" />
                </div>
                <h4 className="text-sm font-medium text-white">
                  Drop .IQ or .WAV file here
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  or click to browse local files
                </p>

                {(loadedFile || (metadata && !metadata.isPreset)) && (
                  <div className="mt-3 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
                    Selected: {loadedFile?.name ?? metadata?.name} ({((loadedFile?.size ?? metadata?.sizeBytes ?? 0) / (1024 * 1024)).toFixed(1)} MB)
                  </div>
                )}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <label className="text-[11px] text-slate-400">Sample rate (S/s)
                  <input type="number" min="1" step="1000" value={sampleRate} onChange={(event) => setSampleRate(Number(event.target.value) || 1)} className="mt-1 w-full border border-slate-700 bg-slate-950 px-2.5 py-2 font-mono text-xs text-white outline-none focus:border-cyan-700" />
                </label>
                <label className="text-[11px] text-slate-400">Center frequency (MHz)
                  <input type="number" min="0" step="0.001" value={centerFrequencyMhz} onChange={(event) => setCenterFrequencyMhz(Number(event.target.value) || 0)} className="mt-1 w-full border border-slate-700 bg-slate-950 px-2.5 py-2 font-mono text-xs text-white outline-none focus:border-cyan-700" />
                </label>
              </div>
              <p className="mt-2 text-[10px] text-slate-500">For WAV, the header sample rate is detected on selection. Values can be adjusted before analysis.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800/80 bg-slate-900/30">
          <button
            onClick={onClose}
            className="text-xs font-medium text-slate-400 hover:text-white px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            Cancel
          </button>

          <button
            onClick={handleProceed}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all cursor-pointer"
          >
            <span>Load Signal</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
