import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import AIChatPanel from '../components/AIChatPanel';
import { apiFetch, apiUrl } from '../api';
import { HowItWorksModal } from '../components/common';

export default function Dashboard() {
  const [summary, setSummary] = useState({
    total_equipment: 0,
    counts: { Normal: 0, Alarm: 0, High: 0, Standby: 0 },
    status_counts: { Normal: 0, Alarm: 0, High: 0, Standby: 0 },
  });
  const [loading, setLoading] = useState(true);
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    apiFetch(apiUrl('/api/summary'))
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Gagal mengambil data summary:", err);
        setLoading(false);
      });
  }, []);

  const counts = summary.counts || summary.status_counts || { Normal: 0, Alarm: 0, High: 0, Standby: 0 };
  const total = summary.total_equipment || 1;
  const normalCount = counts.Normal || 0;
  const alarmCount = counts.Alarm || 0;
  const highCount = counts.High || 0;
  const healthPercent = Math.round((normalCount / total) * 100) || 0;
  const openAlerts = alarmCount + highCount;

  return (
    <div className="flex flex-col gap-4">
      {/* 4-Step Interactive Workflow Quick Guide Banner */}
      <div className="border border-cyan/30 rounded-2xl bg-panel2 p-4 shadow-neon flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan/10 border border-cyan/40 flex items-center justify-center text-cyan text-lg font-bold shrink-0">
            🧭
          </div>
          <div>
            <div className="text-[10px] text-cyan uppercase font-black tracking-widest">Alur Kerja Cepat (Quick Workflow Guide)</div>
            <h3 className="text-sm font-bold text-textMain mt-0.5">4 Langkah Pemeliharaan Prediktif Berbasis AI CBM</h3>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <NavLink 
            to="/mcsa" 
            className="px-2.5 py-1.5 rounded-lg bg-panel border border-line text-[11px] text-textMain hover:border-cyan transition-colors flex items-center gap-1.5"
          >
            <span className="w-4 h-4 rounded-full bg-cyan/20 text-cyan text-[10px] flex items-center justify-center font-bold">1</span>
            <span>Pilih Aset</span>
          </NavLink>
          <NavLink 
            to="/vibration" 
            className="px-2.5 py-1.5 rounded-lg bg-panel border border-line text-[11px] text-textMain hover:border-blue transition-colors flex items-center gap-1.5"
          >
            <span className="w-4 h-4 rounded-full bg-blue/20 text-blue text-[10px] flex items-center justify-center font-bold">2</span>
            <span>Cek Parameter</span>
          </NavLink>
          <NavLink 
            to="/fusion" 
            className="px-2.5 py-1.5 rounded-lg bg-panel border border-line text-[11px] text-textMain hover:border-purple transition-colors flex items-center gap-1.5"
          >
            <span className="w-4 h-4 rounded-full bg-purple/20 text-purple text-[10px] flex items-center justify-center font-bold">3</span>
            <span>Konsensus AI</span>
          </NavLink>
          <NavLink 
            to="/workorders" 
            className="px-2.5 py-1.5 rounded-lg bg-panel border border-line text-[11px] text-textMain hover:border-amber transition-colors flex items-center gap-1.5"
          >
            <span className="w-4 h-4 rounded-full bg-amber/20 text-amber text-[10px] flex items-center justify-center font-bold">4</span>
            <span>Terbitkan WO</span>
          </NavLink>
          <button
            onClick={() => setGuideOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-cyan text-[#071018] font-bold text-xs hover:bg-cyan/90 transition-all shadow-neon"
          >
            Panduan Lengkap →
          </button>
        </div>
      </div>

      <section className="grid lg:grid-cols-[1.5fr_0.95fr] gap-4">
        {/* Left: Overview */}
        <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
          <div className="flex justify-between items-start gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.15em] text-cyan font-bold">Plant Condition Overview</div>
              <h3 className="text-xl font-bold mt-1 mb-1 text-textMain">Reliability Intelligence Command</h3>
            </div>
            <div className="flex items-center gap-2 text-green text-[11px] border border-green/30 py-1 px-2.5 rounded-full bg-green/5 font-mono">
              <span className="w-1.5 h-1.5 bg-green rounded-full shadow-[0_0_12px_var(--green)]"></span> 8 Sub-Agents Online
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-5">
            <div className="border border-line bg-panel rounded-xl p-3">
              <span className="text-[10px] text-muted uppercase tracking-wider font-bold">Total Monitored</span>
              <strong className="block text-[22px] mt-1.5 tracking-tight text-textMain">{loading ? '...' : summary.total_equipment}</strong>
              <small className="text-[10px] text-muted">Motor, Pompa, Fan</small>
            </div>
            <div className="border border-line bg-panel rounded-xl p-3">
              <span className="text-[10px] text-amber uppercase tracking-wider font-bold">Watchlist Alerts</span>
              <strong className="block text-[22px] mt-1.5 tracking-tight text-amber">{loading ? '...' : openAlerts}</strong>
              <small className="text-[10px] text-muted">Perlu Investigasi</small>
            </div>
            <div className="border border-line bg-panel rounded-xl p-3">
              <span className="text-[10px] text-red uppercase tracking-wider font-bold">Critical (High)</span>
              <strong className="block text-[22px] mt-1.5 tracking-tight text-red">{loading ? '...' : highCount}</strong>
              <small className="text-[10px] text-muted">Mitigasi Segera</small>
            </div>
            <div className="border border-line bg-panel rounded-xl p-3">
              <span className="text-[10px] text-green uppercase tracking-wider font-bold">Plant Health</span>
              <strong className="block text-[22px] mt-1.5 tracking-tight text-green">{loading ? '...' : `${healthPercent}%`}</strong>
              <small className="text-[10px] text-muted">Reliability Score</small>
            </div>
          </div>

          <div className="grid sm:grid-cols-[190px_1fr] gap-4 mt-5 items-center">
            <div className="grid place-items-center relative">
              <div 
                className="w-[150px] h-[150px] rounded-full flex items-center justify-center relative shadow-neon"
                style={{ background: `conic-gradient(var(--green) 0 ${healthPercent}%, var(--line) ${healthPercent}% 100%)` }}
              >
                <div className="absolute inset-[11px] rounded-full bg-panel border border-line"></div>
                <div className="relative text-center z-10">
                  <strong className="text-3xl tracking-tighter text-textMain">{loading ? '-' : healthPercent}</strong>
                  <span className="block text-muted text-[9px] uppercase tracking-widest mt-0.5">Reliability %</span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <NavLink to="/mcsa" className="p-3 border-l-2 border-red bg-panel2 rounded-xl hover:border-cyan transition-colors block shadow-neon">
                <small className="text-amber text-[10px] uppercase font-bold">⚠️ Watchlist Alerts</small>
                <strong className="block mt-1 text-[12px] text-textMain">Periksa {openAlerts} peralatan berstatus Alarm/High →</strong>
              </NavLink>
              <NavLink to="/fusion" className="p-3 border-l-2 border-purple bg-panel2 rounded-xl hover:border-purple transition-colors block shadow-neon">
                <small className="text-purple text-[10px] uppercase font-bold">🤖 Multi-Agent Fusion</small>
                <strong className="block mt-1 text-[12px] text-textMain">Jalankan Diagnosa Konsensus RUL →</strong>
              </NavLink>
            </div>
          </div>
        </div>

        {/* Right: AI Agent Chat */}
        <AIChatPanel />
      </section>

      {/* Module Navigation Grid with Plain Descriptions */}
      <div>
        <div className="text-[10px] text-muted uppercase font-bold tracking-wider mb-2">Pilih Workspace Kondisi Peralatan (PdM Modules):</div>
        <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {[
            { name: '⚡ MCSA (Listrik)', path: '/mcsa', count: `${summary.total_equipment || 31} unit`, desc: 'Arus 3-fasa, unbalance tegangan, & spektrum rotor bar (IEEE 519)', color: 'var(--cyan)' },
            { name: '🌀 GETARAN (Mekanikal)', path: '/vibration', count: 'ISO 10816-3', desc: '18 titik sensor getaran RMS, unbalance 1X, misalignment 2X, & bearing', color: 'var(--blue)' },
            { name: '🛢️ TRIBOLOGI (Oli)', path: '/tribology', count: 'ASTM D445', desc: 'Viskositas 40°C, TAN, water ppm, & keausan logam Fe/Cu', color: 'var(--amber)' },
            { name: '🌡️ TERMAL (IRT)', path: '/thermal', count: 'ISO 18434', desc: 'Inframerah delta-T fasa-ke-fasa & suhu RTD bearing motor', color: 'var(--orange-400)' },
            { name: '🧪 DGA (Trafo)', path: '/dga', count: 'IEEE C57.104', desc: 'Kromatografi gas terlarut trafo, TDCG, & Segitiga Duval 1', color: 'var(--purple)' },
            { name: '📚 KNOWLEDGE BASE', path: '/knowledge', count: '19+ materi', desc: 'SOP, standar teknis, & panduan investigasi lapangan', color: 'var(--text-main)' },
          ].map((item, idx) => (
            <NavLink 
              key={idx}
              to={item.path}
              className="p-3.5 rounded-2xl border border-line bg-panel hover:bg-panel2 transition-all hover:scale-[1.02] flex flex-col justify-between shadow-neon"
            >
              <div>
                <div className="flex justify-between items-start mb-1">
                  <strong className="text-xs font-bold" style={{ color: item.color }}>{item.name}</strong>
                </div>
                <p className="text-[10px] text-muted leading-relaxed">{item.desc}</p>
              </div>
              <div className="mt-2.5 pt-1.5 border-t border-line/40 flex justify-between items-center text-[9px] text-muted font-mono">
                <span>{item.count}</span>
                <span className="text-cyan">Buka →</span>
              </div>
            </NavLink>
          ))}
        </section>
      </div>

      {/* Guide Modal */}
      <HowItWorksModal isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
    </div>
  );
}
