import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function ThermalInspectionList({
  inspections = [],
  loading,
  selectedPoint,
  onSelectPoint
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Daftar Inspeksi IR Thermography ({inspections.length})
        </h3>
        <span className="text-[10px] text-orange-400">FLIR Matrix</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat titik inspeksi termal..." />
        ) : inspections.length === 0 ? (
          <EmptyState title="Tidak ada data termal ditemukan" />
        ) : (
          inspections.map((pt, idx) => {
            const isSelected = selectedPoint && (selectedPoint.inspection_id === pt.inspection_id || (selectedPoint.equipment === pt.equipment && selectedPoint.point_name === pt.point_name));
            return (
              <div
                key={idx}
                onClick={() => onSelectPoint(pt)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex justify-between items-center ${
                  isSelected
                    ? 'border-orange-400 bg-orange-500/10 shadow-[0_0_12px_rgba(251,146,60,0.15)]'
                    : 'border-line/70 bg-panel hover:border-orange-400/50 hover:bg-panel2'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-xs text-textMain font-semibold">{pt.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{pt.unit}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                    <span>Titik: {pt.point_name || 'Terminal / Body'}</span>
                    <span>·</span>
                    <span>Tgl: {pt.date || '-'}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={pt.status} />
                  <span className="text-[10px] text-muted font-mono">ΔT: {pt.delta_t !== undefined ? `${pt.delta_t}°C` : '-'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
