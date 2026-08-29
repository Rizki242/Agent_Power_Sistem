import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function DGAEquipmentList({
  transformers = [],
  loading,
  selectedId,
  onSelectTransformer
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Daftar Transformator ({transformers.length})
        </h3>
        <span className="text-[10px] text-cyan">IEEE C57.104</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat daftar trafo..." />
        ) : transformers.length === 0 ? (
          <EmptyState title="Tidak ada transformator ditemukan" />
        ) : (
          transformers.map((trf, idx) => {
            const isSelected = selectedId === trf.transformer_id;
            return (
              <div
                key={idx}
                onClick={() => onSelectTransformer(trf.transformer_id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex justify-between items-center ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_12px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-xs text-textMain font-semibold">{trf.name || trf.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{trf.unit}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                    <span>TDCG: {trf.tdcg !== undefined ? `${trf.tdcg} ppm` : '-'}</span>
                    <span>·</span>
                    <span>Tgl: {trf.sample_date || trf.date || '-'}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={trf.ieee_condition || trf.status} />
                  <span className="text-[10px] text-muted font-mono">{trf.duval_diagnosis || trf.diag || '-'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
