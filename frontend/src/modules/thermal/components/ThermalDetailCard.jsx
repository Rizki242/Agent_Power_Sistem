import React from 'react';
import { StatusBadge } from '../../../components/common';

export default function ThermalDetailCard({ point }) {
  if (!point) {
    return (
      <div className="p-6 text-center text-muted text-xs bg-panel rounded-xl border border-line">
        Pilih salah satu titik inspeksi IRT untuk melihat detail profil suhu dan Delta-T.
      </div>
    );
  }

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      <div className="flex justify-between items-start pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-textMain">{point.equipment}</h3>
            <StatusBadge status={point.status} size="lg" />
          </div>
          <p className="text-[11px] text-muted mt-0.5 font-mono">
            {point.point_name || 'Terminal Conn'} · Unit: {point.unit || 'UNIT 1'} · Tanggal: {point.date || '-'}
          </p>
        </div>
        <div className="text-right font-mono">
          <span className="text-[10px] text-muted block uppercase">Delta-T (ΔT)</span>
          <strong className="text-lg text-orange-400 font-bold">{point.delta_t !== undefined ? `${point.delta_t}°C` : '-'}</strong>
        </div>
      </div>

      {/* Temperature parameter metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Max Hotspot Temp</span>
          <strong className="text-base text-red font-mono mt-1 block">{point.t_max !== undefined ? `${point.t_max}°C` : '-'}</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Reference Temp</span>
          <strong className="text-base text-cyan font-mono mt-1 block">{point.t_ref !== undefined ? `${point.t_ref}°C` : '-'}</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Ambient Temp</span>
          <strong className="text-base text-textMain font-mono mt-1 block">{point.t_ambient !== undefined ? `${point.t_ambient}°C` : '32°C'}</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Severity Criteria</span>
          <strong className="text-base text-amber mt-1 block">{point.status || 'NORMAL'}</strong>
        </div>
      </div>

      {/* Recommendation Card */}
      <div className="p-4 bg-panel2 rounded-xl border border-line">
        <h4 className="text-xs font-bold text-orange-400 flex items-center gap-2 mb-1">
          <span>🔍</span> Analisis Termal &amp; Rekomendasi
        </h4>
        <p className="text-xs text-textMain leading-relaxed">
          {point.recommendation || (
            point.delta_t > 15 
              ? 'Terdeteksi hotspot kritis pada sambungan fase. Jadwalkan pembongkaran, pembersihan kontak, dan pengencangan baut torsi segera.'
              : 'Profil suhu dalam batas normal. Lanjutkan inspeksi inframerah periodik sesuai standar NETA MTS.'
          )}
        </p>
      </div>
    </div>
  );
}
