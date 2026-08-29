import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function OilSampleList({
  samples = [],
  loading,
  selectedSampleId,
  onSelectSample
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Daftar Sampel Pelumas ({samples.length})
        </h3>
        <span className="text-[10px] text-amber">ASTM D445 / D664</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat daftar sampel oli..." />
        ) : samples.length === 0 ? (
          <EmptyState title="Tidak ada sampel oli ditemukan" />
        ) : (
          samples.map((s, idx) => {
            const isSelected = selectedSampleId === s.sample_id;
            return (
              <div
                key={idx}
                onClick={() => onSelectSample(s.sample_id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex justify-between items-center ${
                  isSelected
                    ? 'border-amber bg-amber/10 shadow-[0_0_12px_rgba(251,191,36,0.15)]'
                    : 'border-line/70 bg-panel hover:border-amber/50 hover:bg-panel2'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-xs text-textMain font-semibold">{s.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{s.unit}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                    <span>Oli: {s.oil_type || 'ISO VG 46'}</span>
                    <span>·</span>
                    <span>Tgl: {s.sample_date || s.date || '-'}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={s.status} />
                  <span className="text-[10px] text-muted font-mono">H₂O: {s.water_ppm !== undefined ? `${s.water_ppm} ppm` : '-'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
