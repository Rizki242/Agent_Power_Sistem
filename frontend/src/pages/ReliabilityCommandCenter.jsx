import React, { useState, useEffect } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { StatusBadge, FilterBar } from '../components/common';
import {
  FusionSummaryCards,
  SpecialistAgentStatus,
  AnomalyTimeline
} from '../components/fusion';
import { apiUrl } from '../api';

export default function ReliabilityCommandCenter() {
  const [fleetData, setFleetData] = useState(null);
  const [loadingFleet, setLoadingFleet] = useState(true);
  const [selectedEq, setSelectedEq] = useState(null);
  const [fusionDetail, setFusionDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [woSuccessMsg, setWoSuccessMsg] = useState('');

  // Multi-Agent Collaboration Modal State
  const [collabModalOpen, setCollabModalOpen] = useState(false);
  const [collabLoading, setCollabLoading] = useState(false);
  const [collabResult, setCollabResult] = useState(null);

  // Fetch fleet summary
  useEffect(() => {
    setLoadingFleet(true);
    fetch(apiUrl('/api/reliability/fleet'))
      .then(res => res.json())
      .then(data => {
        setFleetData(data);
        setLoadingFleet(false);
        if (data.asset_matrix && data.asset_matrix.length > 0) {
          loadEquipmentFusion(data.asset_matrix[0].equipment);
        }
      })
      .catch(err => {
        console.error('Failed to load fleet reliability data:', err);
        setLoadingFleet(false);
      });
  }, []);

  const loadEquipmentFusion = (eqName) => {
    setSelectedEq(eqName);
    setLoadingDetail(true);
    setWoSuccessMsg('');
    fetch(apiUrl(`/api/reliability/fusion/${encodeURIComponent(eqName)}`))
      .then(res => res.json())
      .then(data => {
        setFusionDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Failed to load fusion detail:', err);
        setLoadingDetail(false);
      });
  };

  const handleRunMultiAgentCollab = async (eqName) => {
    const target = eqName || selectedEq || 'BFP 1A';
    setCollabLoading(true);
    setCollabModalOpen(true);
    try {
      const res = await fetch(apiUrl('/api/agents/collaborate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ equipment: target, query: `Diagnosa kolaboratif menyeluruh ${target}` })
      });
      const data = await res.json();
      setCollabResult(data);
    } catch (err) {
      console.error(err);
      alert('Gagal menjalankan multi-agent consensus diagnosis.');
    } finally {
      setCollabLoading(false);
    }
  };

  const handleCreateWorkOrder = async (eqName) => {
    try {
      const res = await fetch(apiUrl('/api/workorders/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ equipment: eqName })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setWoSuccessMsg(`Work Order ${data.work_order.wo_number} diterbitkan ke EAM Maximo/SAP!`);
      }
    } catch (err) {
      console.error(err);
      alert('Gagal membuat work order otomatis.');
    }
  };

  const filteredAssets = fleetData?.asset_matrix?.filter(a => {
    if (filterStatus !== 'ALL' && a.health_status !== filterStatus) return false;
    if (searchQuery.trim() && !a.equipment.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  }) || [];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-cyan font-black">Multi-Modal Condition Fusion</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">AI O&amp;M Reliability Command Center</h2>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleRunMultiAgentCollab(selectedEq)}
            className="px-3.5 py-1.5 rounded-xl border border-cyan bg-cyan/15 text-cyan text-xs font-bold hover:bg-cyan/25 transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(50,213,255,0.2)]"
          >
            <span>🤖</span> Multi-Agent Consensus ({selectedEq || 'Pilih Asset'})
          </button>
          <div className="text-xs text-muted flex items-center gap-2">
            <span>PLTU Jeranjang (3x25 MW)</span>
            <span className="w-2 h-2 rounded-full bg-green animate-pulse"></span>
          </div>
        </div>
      </div>

      {/* Fleet Health KPI Overview Bar */}
      <FusionSummaryCards fleetData={fleetData} />

      {/* Specialist Agent Synchronization Banner */}
      <SpecialistAgentStatus onSelectAgent={(ag) => handleRunMultiAgentCollab(selectedEq)} />

      {/* Multi-Agent Collaborative Diagnostic Modal */}
      {collabModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-panel2 border border-cyan/40 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-5 shadow-[0_0_40px_rgba(50,213,255,0.2)] flex flex-col gap-4 animate-fade-in">
            <div className="flex justify-between items-center pb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <span className="text-lg">🤖</span>
                <div>
                  <h3 className="text-sm font-bold text-cyan">Multi-Agent Collaborative Diagnostic Trace</h3>
                  <span className="text-[11px] text-muted">Target: <strong className="text-textMain">{collabResult?.equipment || selectedEq}</strong> ({collabResult?.unit || 'UNIT 1'})</span>
                </div>
              </div>
              <button
                onClick={() => setCollabModalOpen(false)}
                className="w-7 h-7 rounded-lg bg-panel border border-line text-muted hover:text-textMain flex items-center justify-center text-xs"
              >
                ✕
              </button>
            </div>

            {collabLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3">
                <div className="w-10 h-10 border-2 border-cyan border-t-transparent rounded-full animate-spin"></div>
                <span className="text-xs text-cyan font-bold">Mendelegasikan analisis ke 8 Specialist Sub-Agents...</span>
                <span className="text-[10px] text-muted">Vibration • MCSA • DGA • PD • Tribology • Thermal • Fusion • Safety</span>
              </div>
            ) : collabResult ? (
              <div className="flex flex-col gap-4">
                {/* Consensus Header Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-panel rounded-xl border border-line text-center">
                    <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Consolidated Health</span>
                    <strong className={`text-xl mt-1 block font-mono ${collabResult.consensus_health_index < 60 ? 'text-red' : (collabResult.consensus_health_index < 75 ? 'text-amber' : 'text-green')}`}>
                      {collabResult.consensus_health_index}/100
                    </strong>
                    <span className="text-[10px] font-bold text-muted">{collabResult.consensus_health_status}</span>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line text-center">
                    <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Confidence</span>
                    <strong className="text-xl text-cyan mt-1 block font-mono">
                      {Math.round((collabResult.consensus_confidence || 0.95) * 100)}%
                    </strong>
                    <span className="text-[10px] text-muted">Bayesian Fusion</span>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line text-center">
                    <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Estimated RUL</span>
                    <strong className="text-xl text-textMain mt-1 block font-mono">
                      {collabResult.predictive_rul?.estimated_rul_days || 90} Hari
                    </strong>
                    <span className="text-[10px] text-muted">P-F Curve Degradation</span>
                  </div>
                  <div className="p-3 bg-panel rounded-xl border border-line text-center">
                    <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Safety Clearance</span>
                    <strong className={`text-base mt-1.5 block font-bold ${collabResult.safety_clearance ? 'text-green' : 'text-red'}`}>
                      {collabResult.safety_clearance ? '✅ APPROVED' : '⚠️ INTERCEPTED'}
                    </strong>
                    <span className="text-[9px] text-muted">HITL Guardrail</span>
                  </div>
                </div>

                {/* Consensus Failure Mode */}
                <div className="p-3.5 bg-panel rounded-xl border border-cyan/30">
                  <span className="text-[10px] text-cyan font-bold uppercase tracking-wider block">Diagnosa Konsensus Utama (Primary Root Cause)</span>
                  <h4 className="text-sm font-bold text-textMain mt-0.5">{collabResult.consensus_failure_mode}</h4>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {collabResult.fused_evidence?.map((ev, evIdx) => (
                      <span key={evIdx} className="px-2 py-0.5 rounded bg-panel2 border border-line text-[10px] text-textMain">
                        • {ev}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Sub-Agent Trace Grid */}
                <div>
                  <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2">Jejak Analisis 8 Specialist Sub-Agents ({collabResult.execution_duration_ms} ms)</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {collabResult.subagent_traces?.map((tr, trIdx) => (
                      <div key={trIdx} className="p-3 bg-panel rounded-xl border border-line flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs font-bold text-textMain flex items-center gap-1.5">
                            <span>{tr.subagent?.icon}</span>
                            <span>{tr.subagent?.name}</span>
                          </span>
                          <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${tr.status === 'HEALTHY' || tr.status === 'APPROVED' ? 'bg-green/10 text-green border border-green/30' : 'bg-amber/10 text-amber border border-amber/30'}`}>
                            {tr.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted leading-relaxed mt-1">{tr.key_finding}</p>
                        <div className="mt-2 pt-1 border-t border-line/40 flex justify-between text-[9px] text-cyan font-mono">
                          <span>{tr.subagent?.standards?.[0] || tr.subagent?.domain}</span>
                          <span>Score: {tr.health_score || 90}/100</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Action Footer */}
                <div className="flex justify-between items-center pt-3 border-t border-line">
                  <span className="text-xs text-muted">
                    Rekomendasi: <strong className="text-textMain">{collabResult.maintenance_decision?.action_decision || 'Inspeksi Berkala'}</strong>
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleCreateWorkOrder(collabResult.equipment)}
                      className="px-3.5 py-1.5 rounded-xl bg-cyan text-[#071018] font-bold text-xs hover:bg-cyan/90 transition-all shadow-neon"
                    >
                      Terbitkan Work Order Maximo →
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Main Grid: Multi-Modal Fusion Matrix & Root Cause Analytics */}
      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column: Asset Matrix + Live Fusion Detail */}
        <div className="flex flex-col gap-4">
          {/* Reusable Filter Bar */}
          <FilterBar
            search={searchQuery}
            onSearchChange={setSearchQuery}
            onSearchSubmit={() => {}}
            searchPlaceholder="Cari Drive / Pompa / Fan / Trafo..."
            statusFilter={filterStatus}
            onStatusChange={setFilterStatus}
            statusOptions={['ALL', 'HEALTHY', 'WATCH', 'WARNING', 'ALERT', 'CRITICAL']}
            accentColor="cyan"
          />

          {/* Asset Matrix Table */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
                Asset Condition Matrix ({filteredAssets.length})
              </h3>
              <span className="text-[10px] text-cyan">Multi-Modal Cross-Correlation</span>
            </div>

            <div className="overflow-x-auto max-h-[300px] overflow-y-auto pr-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-panel border-b border-line z-10">
                  <tr className="text-muted">
                    <th className="py-2 px-3 font-semibold">Equipment</th>
                    <th className="py-2 px-3 font-semibold">Health Score</th>
                    <th className="py-2 px-3 font-semibold">Status</th>
                    <th className="py-2 px-3 font-semibold">Modalitas Utama</th>
                    <th className="py-2 px-3 font-semibold">Anomali Terdeteksi</th>
                    <th className="py-2 px-3 font-semibold text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60 font-mono">
                  {loadingFleet ? (
                    <tr>
                      <td colSpan="6" className="py-6 text-center text-muted">Menganalisis matriks keandalan multi-modal...</td>
                    </tr>
                  ) : filteredAssets.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="py-6 text-center text-muted">Tidak ada asset matching filter.</td>
                    </tr>
                  ) : (
                    filteredAssets.map((asset, idx) => (
                      <tr
                        key={idx}
                        onClick={() => loadEquipmentFusion(asset.equipment)}
                        className={`hover:bg-panel2/60 transition-colors cursor-pointer ${
                          selectedEq === asset.equipment ? 'bg-panel2 border-l-2 border-l-cyan font-bold' : ''
                        }`}
                      >
                        <td className="py-2 px-3 font-bold text-textMain font-sans">{asset.equipment}</td>
                        <td className="py-2 px-3">
                          <span className={`font-bold ${asset.health_index < 50 ? 'text-red' : asset.health_index < 75 ? 'text-amber' : 'text-green'}`}>
                            {asset.health_index}/100
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <StatusBadge status={asset.health_status} />
                        </td>
                        <td className="py-2 px-3 text-muted text-[10px]">{asset.primary_modality || 'MCSA+VIB'}</td>
                        <td className="py-2 px-3 text-muted text-[10px] font-sans truncate max-w-[160px]">{asset.anomaly_driver || 'None'}</td>
                        <td className="py-2 px-3 text-right flex items-center justify-end gap-1.5">
                          <button
                            onClick={(e) => { e.stopPropagation(); loadEquipmentFusion(asset.equipment); }}
                            className="px-2 py-0.5 rounded bg-panel border border-line text-cyan hover:border-cyan text-[10px]"
                          >
                            Fusion →
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleRunMultiAgentCollab(asset.equipment); }}
                            className="px-2 py-0.5 rounded bg-panel border border-cyan/40 text-cyan hover:bg-cyan/10 text-[10px]"
                            title="Jalankan Diagnosa 8 Sub-Agent"
                          >
                            🤖
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Real-time Multi-Modal Fusion Card */}
          <AnomalyTimeline
            fusionDetail={fusionDetail}
            loading={loadingDetail}
            onGenerateWorkOrder={handleCreateWorkOrder}
            woSuccessMsg={woSuccessMsg}
          />
        </div>

        {/* Right Column: AI Specialist Agent Multi-Modal Chat */}
        <div>
          <AIChatPanel defaultPrompt={selectedEq ? `Lakukan audit multi-modal mendalam untuk peralatan ${selectedEq}. Korelasikan data MCSA, Vibrasi, Oli, DGA, dan Thermal untuk mengidentifikasi akar masalah (RCA).` : undefined} />
        </div>
      </section>
    </div>
  );
}
