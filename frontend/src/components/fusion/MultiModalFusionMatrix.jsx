import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function MultiModalFusionMatrix({
  assets = [],
  loading,
  selectedEq,
  onSelectEquipment
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Multi-Modal Condition Matrix ({assets.length})
        </h3>
        <span className="text-[10px] text-cyan">Unified CBM Fusion</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat matriks fusion..." />
        ) : assets.length === 0 ? (
          <EmptyState title="Tidak ada aset matching kriteria" />
        ) : (
          assets.map((asset, idx) => {
            const isSelected = selectedEq === asset.equipment;
            const modalities = asset.modalities || {};
            return (
              <div
                key={idx}
                onClick={() => onSelectEquipment(asset.equipment)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col gap-2 ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_12px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <strong className="text-xs text-textMain font-semibold block">{asset.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{asset.unit || 'PLTU Jeranjang'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-cyan">{asset.health_index || 85}/100</span>
                    <StatusBadge status={asset.health_status} size="xs" />
                  </div>
                </div>

                {/* Modality Status Badges */}
                <div className="grid grid-cols-5 gap-1 text-[9px] pt-2 border-t border-line/40 text-center font-mono">
                  <div className="p-1 bg-panel2 rounded">
                    <span className="text-muted block text-[8px]">MCSA</span>
                    <span className={modalities.mcsa === 'CRITICAL' ? 'text-red font-bold' : modalities.mcsa === 'WARNING' ? 'text-amber' : 'text-green'}>
                      {modalities.mcsa || 'NORMAL'}
                    </span>
                  </div>
                  <div className="p-1 bg-panel2 rounded">
                    <span className="text-muted block text-[8px]">VIBRASI</span>
                    <span className={modalities.vibration === 'CRITICAL' ? 'text-red font-bold' : modalities.vibration === 'WARNING' ? 'text-amber' : 'text-green'}>
                      {modalities.vibration || 'NORMAL'}
                    </span>
                  </div>
                  <div className="p-1 bg-panel2 rounded">
                    <span className="text-muted block text-[8px]">OLI</span>
                    <span className={modalities.tribology === 'CRITICAL' ? 'text-red font-bold' : modalities.tribology === 'WARNING' ? 'text-amber' : 'text-green'}>
                      {modalities.tribology || 'NORMAL'}
                    </span>
                  </div>
                  <div className="p-1 bg-panel2 rounded">
                    <span className="text-muted block text-[8px]">THERMAL</span>
                    <span className={modalities.thermal === 'CRITICAL' ? 'text-red font-bold' : modalities.thermal === 'WARNING' ? 'text-amber' : 'text-green'}>
                      {modalities.thermal || 'NORMAL'}
                    </span>
                  </div>
                  <div className="p-1 bg-panel2 rounded">
                    <span className="text-muted block text-[8px]">DGA</span>
                    <span className={modalities.dga === 'CRITICAL' ? 'text-red font-bold' : modalities.dga === 'WARNING' ? 'text-amber' : 'text-green'}>
                      {modalities.dga || 'NORMAL'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
