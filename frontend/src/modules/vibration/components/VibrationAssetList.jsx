import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../../../components/common';

export default function VibrationAssetList({
  equipmentList = [],
  loading,
  selectedAssetId,
  onSelectAsset
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Master Aset Vibrasi ({equipmentList.length})
        </h3>
        <span className="text-[10px] text-cyan">ISO 10816 Groups</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat master aset..." />
        ) : equipmentList.length === 0 ? (
          <EmptyState title="Tidak ada aset ditemukan" />
        ) : (
          equipmentList.map((eq, idx) => {
            const isSelected = selectedAssetId === eq.asset_id;
            return (
              <div
                key={idx}
                onClick={() => onSelectAsset(eq.asset_id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex justify-between items-center ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_12px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-xs text-textMain font-semibold">{eq.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{eq.unit}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                    <span>RPM: {eq.rpm || eq.speed_rpm || '-'}</span>
                    <span>·</span>
                    <span>Class: {eq.equipment_class || 'Class III'}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={eq.status || 'NORMAL'} />
                  <span className="text-[10px] text-muted">{eq.bearing_de || 'DE Bearing'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
