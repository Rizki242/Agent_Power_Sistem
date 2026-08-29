import React from 'react';
import { LoadingSpinner, EmptyState } from '../common';

export default function WorkOrderTable({
  workOrders = [],
  loading,
  selectedWO,
  onSelectWO,
  onAction
}) {
  const getPriorityBadge = (prio) => {
    const p = String(prio || '').toUpperCase();
    if (p.includes('P1') || p.includes('CRITICAL')) return <span className="px-2 py-0.5 rounded bg-red/10 text-red border border-red/30 text-[10px] font-bold">P1 - CRITICAL</span>;
    if (p.includes('P2') || p.includes('HIGH')) return <span className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/30 text-[10px] font-bold">P2 - HIGH</span>;
    if (p.includes('P3') || p.includes('MEDIUM')) return <span className="px-2 py-0.5 rounded bg-amber/10 text-amber border border-amber/30 text-[10px] font-bold">P3 - MEDIUM</span>;
    return <span className="px-2 py-0.5 rounded bg-blue/10 text-blue border border-blue/30 text-[10px] font-bold">P4 - ROUTINE</span>;
  };

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Daftar Work Order AI ({workOrders.length})
        </h3>
        <span className="text-[10px] text-cyan">Integrasi SAP / Maximo CMMS</span>
      </div>

      <div className="overflow-y-auto max-h-[520px] space-y-2.5 pr-1">
        {loading ? (
          <LoadingSpinner message="Memuat antrean Work Order..." />
        ) : workOrders.length === 0 ? (
          <EmptyState title="Tidak ada antrean Work Order" />
        ) : (
          workOrders.map((wo, idx) => {
            const isSelected = selectedWO?.wo_number === wo.wo_number;
            return (
              <div
                key={idx}
                onClick={() => onSelectWO(wo)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_15px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-mono text-cyan font-bold block">{wo.wo_number}</span>
                    <strong className="text-xs text-textMain">{wo.equipment}</strong>
                  </div>
                  {getPriorityBadge(wo.priority)}
                </div>

                <p className="text-[11px] text-muted line-clamp-2 mt-1.5 leading-relaxed">{wo.task_title || wo.description}</p>

                <div className="flex justify-between items-center mt-2.5 pt-2 border-t border-line/40 text-[10px]">
                  <span className="text-muted font-mono">Status: <strong className="text-textMain">{wo.status}</strong></span>
                  <span className="text-muted">Target: <strong className="text-textMain">{wo.target_date || '7 Hari'}</strong></span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
