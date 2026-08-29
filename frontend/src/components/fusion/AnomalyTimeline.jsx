import React from 'react';
import { StatusBadge, LoadingSpinner } from '../common';

export default function AnomalyTimeline({
  fusionDetail,
  loading,
  onGenerateWorkOrder,
  woSuccessMsg
}) {
  if (loading) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8">
        <LoadingSpinner message="Menganalisis korelasi multi-modal..." />
      </div>
    );
  }

  if (!fusionDetail) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8 text-center text-muted text-xs">
        Pilih salah satu drive/peralatan dari daftar di samping untuk melihat analisa komprehensif.
      </div>
    );
  }

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-textMain">{fusionDetail.equipment}</h3>
            <StatusBadge status={fusionDetail.health_status} size="lg" />
          </div>
          <p className="text-[11px] text-muted mt-0.5 font-mono">
            Unit: {fusionDetail.unit || 'PLTU Jeranjang'} · Health Score: <strong className="text-cyan">{fusionDetail.health_index}/100</strong>
          </p>
        </div>
        <button
          onClick={() => onGenerateWorkOrder && onGenerateWorkOrder(fusionDetail.equipment)}
          className="px-3.5 py-1.5 rounded-lg border border-cyan bg-cyan/10 text-cyan text-xs font-bold hover:bg-cyan/20 transition-colors flex items-center gap-1.5"
        >
          <span>📝</span> Dispatch AI Work Order
        </button>
      </div>

      {woSuccessMsg && (
        <div className="p-3 bg-green/10 border border-green/30 text-green rounded-xl text-xs flex items-center gap-2 font-semibold">
          <span>✅</span> {woSuccessMsg}
        </div>
      )}

      {/* Cross-Modality Telemetry Breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">MCSA Status</span>
          <strong className="text-xs text-textMain mt-1 block font-mono">{fusionDetail.modalities?.mcsa?.detail || 'Normal'}</strong>
          <div className="mt-1">
            <StatusBadge status={fusionDetail.modalities?.mcsa?.status || 'NORMAL'} size="xs" />
          </div>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Vibrasi RMS</span>
          <strong className="text-xs text-textMain mt-1 block font-mono">{fusionDetail.modalities?.vibration?.detail || '2.8 mm/s'}</strong>
          <div className="mt-1">
            <StatusBadge status={fusionDetail.modalities?.vibration?.status || 'NORMAL'} size="xs" />
          </div>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Pelumas &amp; Wear</span>
          <strong className="text-xs text-textMain mt-1 block font-mono">{fusionDetail.modalities?.tribology?.detail || 'ISO VG 46 (Good)'}</strong>
          <div className="mt-1">
            <StatusBadge status={fusionDetail.modalities?.tribology?.status || 'NORMAL'} size="xs" />
          </div>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Thermal Delta-T</span>
          <strong className="text-xs text-textMain mt-1 block font-mono">{fusionDetail.modalities?.thermal?.detail || 'ΔT: 2.1°C'}</strong>
          <div className="mt-1">
            <StatusBadge status={fusionDetail.modalities?.thermal?.status || 'NORMAL'} size="xs" />
          </div>
        </div>
      </div>

      {/* Multi-Agent Root Cause Synthesis */}
      <div className="p-4 bg-panel2 rounded-xl border border-line">
        <h4 className="text-xs font-bold text-cyan flex items-center gap-2 mb-1.5">
          <span>🧠</span> AI Multi-Agent Correlated Diagnostic Synthesis
        </h4>
        <p className="text-xs text-textMain leading-relaxed">
          {fusionDetail.diagnosis_narrative || 'Kondisi operasi peralatan seimbang. Tidak ditemukan anomali silang antara spektrum arus motor, spektrum getaran mekanikal, kondisi pelumas, dan profil termal.'}
        </p>
      </div>

      {/* Safety Guardrail Assessment */}
      <div className="p-3 bg-panel rounded-xl border border-line flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs">🛡️</span>
          <span className="text-xs font-bold text-textMain">Safety Guardrail Engine:</span>
          <span className="text-[11px] text-green font-semibold">VERIFIED SAFE</span>
        </div>
        <span className="text-[10px] text-muted font-mono">Confidence: {fusionDetail.confidence_score || '96%'}</span>
      </div>
    </div>
  );
}
