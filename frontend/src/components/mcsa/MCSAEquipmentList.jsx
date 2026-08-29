import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function MCSAEquipmentList({
  equipmentList,
  loading,
  selectedEquipment,
  onSelectEquipment
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Daftar Motor Listrik ({equipmentList.length})
        </h3>
        <span className="text-[10px] text-cyan">Live Telemetry</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat daftar motor..." />
        ) : equipmentList.length === 0 ? (
          <EmptyState title="Tidak ada motor ditemukan" />
        ) : (
          equipmentList.map((eq, idx) => {
            const isSelected = selectedEquipment === eq.equipment;
            return (
              <div
                key={idx}
                onClick={() => onSelectEquipment(eq.equipment)}
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
                    <span>Volt: {eq.voltage || '6 kV'}</span>
                    <span>·</span>
                    <span>Tgl: {eq.date || '-'}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={eq.status} />
                  <span className="text-[10px] text-muted">RB: {eq.rotorbar || '-'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
