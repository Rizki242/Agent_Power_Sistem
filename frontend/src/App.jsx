import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Dashboard from './pages/Dashboard';
import ReliabilityCommandCenter from './pages/ReliabilityCommandCenter';
import AssetHealth from './pages/AssetHealth';
import MCSAWorkspace from './pages/MCSAWorkspace';
import VibWorkspace from './pages/VibWorkspace';
import TribologyWorkspace from './pages/TribologyWorkspace';
import ThermalWorkspace from './pages/ThermalWorkspace';
import DGAWorkspace from './pages/DGAWorkspace';
import KnowledgeWorkspace from './pages/KnowledgeWorkspace';
import WorkOrderCenter from './pages/WorkOrderCenter';
import DigitalTwinWorkspace from './pages/DigitalTwinWorkspace';

function AppContent() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-bg bg-hero-gradient text-textMain font-sans grid lg:grid-cols-[268px_1fr]">
      <Sidebar />
      <main className="min-w-0 flex flex-col h-screen overflow-y-auto">
        <Topbar toggleTheme={() => setIsDark(!isDark)} isDark={isDark} />
        <div className="p-4 md:p-6 lg:p-7 max-w-[1680px] w-full mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/fusion" element={<ReliabilityCommandCenter />} />
            <Route path="/twin" element={<DigitalTwinWorkspace />} />
            <Route path="/health" element={<AssetHealth />} />
            <Route path="/mcsa" element={<MCSAWorkspace />} />
            <Route path="/vibration" element={<VibWorkspace />} />
            <Route path="/tribology" element={<TribologyWorkspace />} />
            <Route path="/thermal" element={<ThermalWorkspace />} />
            <Route path="/dga" element={<DGAWorkspace />} />
            <Route path="/knowledge" element={<KnowledgeWorkspace />} />
            <Route path="/workorders" element={<WorkOrderCenter />} />
            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
