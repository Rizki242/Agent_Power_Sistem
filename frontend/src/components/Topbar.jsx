import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { HowItWorksModal, AlarmAnnunciator } from './common';

export default function Topbar({ toggleTheme, isDark }) {
  const [guideOpen, setGuideOpen] = useState(false);

  return (
    <>
      <header className="h-[70px] border-b border-line flex items-center justify-between px-5 md:px-7 bg-bg/80 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="lg:hidden w-8 h-8 rounded-lg border border-cyan/40 flex items-center justify-center text-cyan font-bold bg-cyan/10 text-xs">
            ⚡
          </div>
          <div>
            <h2 className="text-sm md:text-base font-bold m-0 text-textMain leading-tight">PPLE Intelligence Command Center</h2>
            <p className="m-0 mt-0.5 text-muted text-[10px] md:text-[11px]">Autonomous Predictive Maintenance · MCSA · Vibration · DGA · Tribology</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2.5">
          {/* Real-time Alarm Annunciator Dropdown */}
          <AlarmAnnunciator />

          {/* Interactive How-It-Works Guide Button */}
          <button
            onClick={() => setGuideOpen(true)}
            className="h-8 px-3 rounded-lg border border-cyan/40 bg-cyan/10 text-cyan font-bold text-xs hover:bg-cyan/20 hover:border-cyan transition-all flex items-center gap-1.5 shadow-[0_0_12px_rgba(50,213,255,0.15)]"
            title="Buka Panduan & Cara Kerja Sistem AI CBM"
          >
            <span>💡</span>
            <span className="hidden sm:inline">Cara Kerja Sistem</span>
          </button>

          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-line bg-panel2 text-[11px] text-muted font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse"></span>
            PLTU JERANJANG
          </div>

          <button 
            onClick={toggleTheme} 
            className="h-8 w-8 flex items-center justify-center rounded-lg border border-line bg-panel2 text-textMain text-xs hover:border-cyan transition-colors" 
            title="Ganti Tema Gelap / Terang"
          >
            {isDark ? '🌞' : '🌙'}
          </button>

          <NavLink 
            to="/fusion" 
            className="h-8 px-3 rounded-lg border border-purple bg-purple/10 text-purple font-bold text-xs hover:bg-purple/20 transition-colors flex items-center gap-1"
          >
            <span>🤖</span> Multi-Agent
          </NavLink>
        </div>
      </header>

      {/* Guide Modal */}
      <HowItWorksModal isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
    </>
  );
}
