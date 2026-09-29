'use client';

import React, { useState } from 'react';
import { SignalProvider, useSignal } from '../context/SignalContext';
import { HeroSection } from '../components/hero/HeroSection';
import { LabWorkbench } from '../components/workbench/LabWorkbench';
import { IngestionModal } from '../components/modules/IngestionModal';

function MainApp() {
  const [viewMode, setViewMode] = useState<'hero' | 'workbench'>('hero');
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const { setStage } = useSignal();

  const handleOpenWorkbench = () => {
    setStage('spectral');
    setViewMode('workbench');
  };

  const handleOpenIngest = () => {
    setIsIngestOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#040814] text-white">
      {viewMode === 'hero' ? (
        <>
          <div id="home">
            <HeroSection
              onOpenLab={handleOpenWorkbench}
              onUploadSignal={handleOpenIngest}
              onWatchDemo={handleOpenWorkbench}
            />
          </div>
          <IngestionModal
            isOpen={isIngestOpen}
            onClose={() => setIsIngestOpen(false)}
            onLaunchWorkbench={() => {
              setIsIngestOpen(false);
              setViewMode('workbench');
            }}
          />
        </>
      ) : (
        <LabWorkbench onBackToOverview={() => setViewMode('hero')} />
      )}
    </div>
  );
}

export default function Home() {
  return (
    <SignalProvider>
      <MainApp />
    </SignalProvider>
  );
}
