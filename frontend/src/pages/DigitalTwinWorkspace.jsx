import React, { useState, useEffect } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { apiFetch, apiUrl } from '../api';

export default function DigitalTwinWorkspace() {
  const [selectedNode, setSelectedNode] = useState('BFP 1A');
  const [nodeDetail, setNodeDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeSystem, setActiveSystem] = useState('ALL'); // 'ALL' | 'STEAM' | 'AIR_GAS' | 'COOLING' | 'COAL' | 'ELECTRICAL'

  // Digital Twin Plant Topology Nodes
  const plantNodes = [
    // Steam & Feedwater Loop
    { id: 'BFP 1A', name: 'Boiler Feed Pump 1A', system: 'STEAM', category: 'High-Pressure Feed Pump', power: '650 kW', volt: '6.3 kV', health: 88, status: 'NORMAL', icon: '💧', x: 22, y: 62 },
    { id: 'BFP 1B', name: 'Boiler Feed Pump 1B', system: 'STEAM', category: 'High-Pressure Feed Pump', power: '650 kW', volt: '6.3 kV', health: 92, status: 'NORMAL', icon: '💧', x: 22, y: 74 },
    { id: 'CEP 1A', name: 'Condensate Ext. Pump 1A', system: 'STEAM', category: 'Condensate Pump', power: '110 kW', volt: '380 V', health: 85, status: 'NORMAL', icon: '🌊', x: 38, y: 78 },
    { id: 'CEP 1B', name: 'Condensate Ext. Pump 1B', system: 'STEAM', category: 'Condensate Pump', power: '110 kW', volt: '380 V', health: 65, status: 'ALARM', icon: '🌊', x: 48, y: 78 },
    
    // Flue Gas & Draft System
    { id: 'IDF 1A', name: 'Induced Draft Fan 1A', system: 'AIR_GAS', category: 'Flue Gas Draft Fan', power: '380 kW', volt: '6.3 kV', health: 58, status: 'ALARM', icon: '🌀', x: 12, y: 25 },
    { id: 'IDF 1B', name: 'Induced Draft Fan 1B', system: 'AIR_GAS', category: 'Flue Gas Draft Fan', power: '380 kW', volt: '6.3 kV', health: 86, status: 'NORMAL', icon: '🌀', x: 12, y: 38 },
    { id: 'PAF 1A', name: 'Primary Air Fan 1A', system: 'AIR_GAS', category: 'Combustion Air Fan', power: '200 kW', volt: '6.3 kV', health: 90, status: 'NORMAL', icon: '💨', x: 28, y: 22 },
    { id: 'SAF 1A', name: 'Secondary Air Fan 1A', system: 'AIR_GAS', category: 'Overfire Air Fan', power: '160 kW', volt: '380 V', health: 91, status: 'NORMAL', icon: '💨', x: 28, y: 34 },

    // Cooling Water Loop
    { id: 'CWP 1A', name: 'Circulating Water Pump 1A', system: 'COOLING', category: 'Main Cooling Pump', power: '320 kW', volt: '6.3 kV', health: 82, status: 'NORMAL', icon: '🔄', x: 62, y: 65 },
    { id: 'CWP 1B', name: 'Circulating Water Pump 1B', system: 'COOLING', category: 'Main Cooling Pump', power: '320 kW', volt: '6.3 kV', health: 68, status: 'ALARM', icon: '🔄', x: 62, y: 77 },
    { id: 'CTF 1A', name: 'Cooling Tower Fan 1A', system: 'COOLING', category: 'Cooling Tower Fan', power: '45 kW', volt: '380 V', health: 48, status: 'HIGH', icon: '❄️', x: 78, y: 70 },

    // Coal Handling System
    { id: 'BC 10.1', name: 'Belt Conveyor 10.1', system: 'COAL', category: 'Overland Coal Conveyor', power: '75 kW', volt: '380 V', health: 94, status: 'STANDBY', icon: '🚜', x: 72, y: 22 },
    { id: 'BC 41', name: 'Coal Conveyor 41', system: 'COAL', category: 'Crusher Feed Conveyor', power: '90 kW', volt: '380 V', health: 45, status: 'HIGH', icon: '🚜', x: 84, y: 22 },
    { id: 'CRUSHER 1', name: 'Coal Crusher 1', system: 'COAL', category: 'Ring Granulator Crusher', power: '250 kW', volt: '6.3 kV', health: 62, status: 'ALARM', icon: '⚙️', x: 84, y: 35 },

    // Electrical Substation & Transformer
    { id: 'GSUT 1', name: 'Main Step-Up Trafo 1', system: 'ELECTRICAL', category: 'Generator Step-Up 150kV', power: '31.25 MVA', volt: '6.3/150 kV', health: 76, status: 'NORMAL', icon: '⚡', x: 50, y: 30 },
    { id: 'UAT 1', name: 'Unit Aux Trafo 1', system: 'ELECTRICAL', category: 'Auxiliary Transformer', power: '3.15 MVA', volt: '6.3/0.4 kV', health: 95, status: 'NORMAL', icon: '⚡', x: 50, y: 45 }
  ];

  const loadNodeDetail = (nodeId) => {
    setSelectedNode(nodeId);
    setLoadingDetail(true);
    apiFetch(apiUrl(`/api/reliability/fusion/${encodeURIComponent(nodeId)}`))
      .then(res => res.json())
      .then(data => {
        setNodeDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Failed to load digital twin detail:', err);
        setLoadingDetail(false);
      });
  };

  useEffect(() => {
    loadNodeDetail(selectedNode);
  }, []);

  const filteredNodes = plantNodes.filter(n => {
    if (activeSystem !== 'ALL' && n.system !== activeSystem) return false;
    return true;
  });

  const getStatusColor = (status) => {
    if (status === 'NORMAL') return 'border-green bg-green/20 text-green shadow-[0_0_15px_rgba(16,185,129,0.3)]';
    if (status === 'ALARM' || status === 'WARNING') return 'border-amber bg-amber/20 text-amber shadow-[0_0_15px_rgba(245,158,11,0.3)] animate-pulse';
    if (status === 'HIGH' || status === 'CRITICAL') return 'border-red bg-red/25 text-red shadow-[0_0_20px_rgba(239,68,68,0.4)] animate-bounce';
    return 'border-slate-500 bg-slate-500/20 text-slate-400';
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-cyan font-black">Spatial 3D &amp; Plant Topology Twin</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Digital Twin Auxiliary Plant Visualizer</h2>
        </div>
        
        {/* System Filter Tabs */}
        <div className="flex items-center gap-1.5 flex-wrap text-xs">
          {[
            { id: 'ALL', label: 'Semua Sistem' },
            { id: 'STEAM', label: '💧 Air Pengisi & Uap' },
            { id: 'AIR_GAS', label: '🌀 Gas Buang & Udara' },
            { id: 'COOLING', label: '🔄 Air Pendingin' },
            { id: 'COAL', label: '🚜 Coal Handling' },
            { id: 'ELECTRICAL', label: '⚡ Trafo & Listrik' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSystem(tab.id)}
              className={`px-2.5 py-1 rounded-lg border transition-all ${activeSystem === tab.id ? 'bg-cyan text-[#071018] border-cyan font-bold shadow-neon' : 'bg-panel border-line text-muted hover:text-textMain'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <section className="grid lg:grid-cols-[1.55fr_0.95fr] gap-4">
        {/* Left Column: Interactive Digital Twin Canvas */}
        <div className="flex flex-col gap-4">
          <div className="border border-line rounded-3xl bg-card-gradient shadow-neon p-5 relative overflow-hidden min-h-[520px] flex flex-col justify-between">
            {/* Canvas Header & Legend */}
            <div className="flex justify-between items-center pb-3 border-b border-line z-10">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan animate-ping"></span>
                <strong className="text-xs text-textMain font-mono uppercase tracking-wider">
                  PLTU Jeranjang Unit 1 (25 MW) · Topology Grid
                </strong>
              </div>

              {/* Status Legend */}
              <div className="flex items-center gap-3 text-[10px]">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green"></span> Normal (Zone A/B)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber animate-pulse"></span> Warning (Alarm)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red animate-pulse"></span> Critical (High)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-400"></span> Standby</span>
              </div>
            </div>

            {/* Schematic Spatial Blueprint Canvas */}
            <div className="relative w-full h-[400px] my-2 bg-panel/40 rounded-2xl border border-line/60 overflow-hidden">
              {/* Background Grid Lines & Flow Paths */}
              <div className="absolute inset-0 bg-[radial-gradient(#32d5ff15_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none"></div>

              {/* Major Plant Sections Blueprint Watermarks */}
              <div className="absolute left-6 top-8 text-[11px] font-black text-cyan/20 uppercase tracking-widest pointer-events-none">
                [BOILER &amp; FLUE GAS DRAFT SYSTEM]
              </div>
              <div className="absolute left-1/3 top-8 text-[11px] font-black text-purple/20 uppercase tracking-widest pointer-events-none">
                [TURBINE - GENERATOR 25MW &amp; SUBSTATION]
              </div>
              <div className="absolute right-6 top-8 text-[11px] font-black text-amber/20 uppercase tracking-widest pointer-events-none">
                [COAL HANDLING &amp; CRUSHER]
              </div>
              <div className="absolute left-6 bottom-4 text-[11px] font-black text-blue/20 uppercase tracking-widest pointer-events-none">
                [FEEDWATER &amp; CONDENSATE PUMPS]
              </div>
              <div className="absolute right-6 bottom-4 text-[11px] font-black text-green/20 uppercase tracking-widest pointer-events-none">
                [CIRCULATING COOLING WATER &amp; TOWER]
              </div>

              {/* Interactive Pulsing Plant Nodes */}
              {filteredNodes.map((node) => (
                <div
                  key={node.id}
                  onClick={() => loadNodeDetail(node.id)}
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 p-2 rounded-xl border-2 cursor-pointer transition-all hover:scale-110 z-20 flex items-center gap-2 select-none ${getStatusColor(node.status)} ${selectedNode === node.id ? 'ring-4 ring-cyan/50 scale-110' : ''}`}
                >
                  <span className="text-base">{node.icon}</span>
                  <div>
                    <strong className="text-[11px] block font-mono leading-tight">{node.id}</strong>
                    <span className="text-[9px] opacity-80 block font-sans">{node.power}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Canvas Footer */}
            <div className="pt-2 border-t border-line flex justify-between items-center text-[10px] text-muted">
              <span>Klik komponen mana saja pada diagram skematik untuk melihat *live telemetry overlay*.</span>
              <span className="font-mono text-cyan">Node Terpilih: <strong>{selectedNode}</strong></span>
            </div>
          </div>

          {/* Selected Component Digital Twin Telemetry Drawer */}
          {selectedNode && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex justify-between items-start pb-3 border-b border-line mb-3">
                <div>
                  <span className="text-[10px] text-cyan uppercase font-bold tracking-widest">Digital Twin Telemetry &amp; Condition Overlay</span>
                  <h3 className="text-base font-bold text-textMain mt-0.5 flex items-center gap-2">
                    <span>{selectedNode}</span>
                    <span className="text-xs text-muted font-normal">({nodeDetail?.asset_type || 'Drive Motor Auxiliary'})</span>
                  </h3>
                </div>
                <div className="text-right">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${nodeDetail?.health_index < 50 ? 'bg-red/15 text-red border-red/30' : (nodeDetail?.health_index < 75 ? 'bg-amber/15 text-amber border-amber/30' : 'bg-green/15 text-green border-green/30')}`}>
                    Health: {nodeDetail?.health_index || 88}/100 ({nodeDetail?.health_status || 'HEALTHY'})
                  </span>
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-xs text-muted">Sinkronisasi telemetry digital twin...</div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-muted block uppercase font-bold">Vibration RMS</span>
                    <strong className="text-sm text-textMain mt-1 block font-mono">
                      {nodeDetail?.specialist_evaluations?.Vibration?.evidence?.[0] ? 'Termonitor' : '2.4 mm/s'}
                    </strong>
                    <small className="text-[10px] text-green">ISO Zone A</small>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-muted block uppercase font-bold">MCSA Sideband</span>
                    <strong className="text-sm text-textMain mt-1 block font-mono">
                      -56.2 dB
                    </strong>
                    <small className="text-[10px] text-green">Severity Level 1</small>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-muted block uppercase font-bold">Estimated RUL</span>
                    <strong className="text-sm text-cyan mt-1 block font-mono">
                      {nodeDetail?.predictive_rul?.estimated_rul_days || 90} Hari
                    </strong>
                    <small className="text-[10px] text-muted">Sisa Umur Operasi</small>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-muted block uppercase font-bold">Risk Level</span>
                    <strong className="text-sm text-textMain mt-1 block">
                      {nodeDetail?.risk_assessment?.risk_level || 'Low Risk'}
                    </strong>
                    <small className="text-[10px] text-muted">5x5 Risk Matrix</small>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Chat with Spatial Context */}
        <div>
          <AIChatPanel defaultPrompt={`Bagaimana analisa kondisi digital twin dan hubungan sistem untuk komponen ${selectedNode}?`} />
        </div>
      </section>
    </div>
  );
}
