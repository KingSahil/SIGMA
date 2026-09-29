'use client';

import { useRouter } from 'next/navigation';
import { HeroNavbar } from '../hero/HeroNavbar';
import { LandingSections, type LandingPage } from './LandingSections';

export function LandingRoutePage({ page }: { page: LandingPage }) {
  const router = useRouter();
  const goHome = () => router.push('/');

  return (
    <div className="min-h-screen bg-[#040814] text-white">
      <HeroNavbar onOpenLab={goHome} active={page === 'all' ? 'home' : page} />
      <LandingSections page={page} onUploadSignal={goHome} onOpenLab={goHome} />
    </div>
  );
}