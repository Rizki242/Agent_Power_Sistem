import React from 'react';
import { NavLink } from 'react-router-dom';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function AssetHealthMatrix({
  alarmList = [],
  loading = false
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-textMain uppercase tracking-wider flex items-center gap-2">
          <span>⚠️</span> Daftar Prioritas Mitigasi &amp; Watchlist ({alarmList.length})
        </h3>
        <span className="text-[10px] text-red font-mono">Action Required</span>
      </div>

      <div className="overflow-y-auto max-h-[460px] space-y-2 pr-1">
        {loading ? (
          <LoadingSpinner message="Memuat daftar peralatan watchlist..." />
        ) : alarmList.length === 0 ? (
          <EmptyState
            icon="🎉"
            title="Tidak ada equipment berstatus Alarm/High"
            description="Seluruh peralatan beroperasi normal dan memenuhi standar keandalan."
          />
        ) : (
          alarmList.map((eq, idx) => (
            <div
              key={idx}
              className="p-3 bg-panel rounded-xl border border-line/70 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 hover:border-cyan/50 transition-colors"
            >
              <div>
                <div className="flex items-center gap-2">
                  <strong className="text-xs text-textMain font-semibold">{eq.equipment}</strong>
                  <span className="text-[10px] text-muted font-mono">{eq.unit}</span>
                </div>
                <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                  <span>Parameter: {eq.parameter || 'Rotor Bar / Bearing'}</span>
                  <span>·</span>
                  <span>Tgl: {eq.date || '-'}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <StatusBadge status={eq.status} />
                <NavLink
                  to="/mcsa"
                  className="px-2.5 py-1 bg-cyan/10 border border-cyan text-cyan hover:bg-cyan/20 text-[10px] font-bold rounded-lg transition-colors"
                >
                  Detail &rarr;
                </NavLink>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
