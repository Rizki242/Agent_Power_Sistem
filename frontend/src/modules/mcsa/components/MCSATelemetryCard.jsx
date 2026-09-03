import React from 'react';
import { StatusBadge, LoadingSpinner } from '../../../components/common';

export default function MCSATelemetryCard({ eqDetail, loading }) {
  if (loading) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8">
        <LoadingSpinner message="Memuat parameter telemetri motor..." />
      </div>
    );
  }

  if (!eqDetail) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8 text-center text-muted text-xs">
        Pilih salah satu motor dari daftar di samping untuk melihat telemetri komprehensif.
      </div>
    );
  }

  const latest = eqDetail.latest || {};
  const currentParams = [
    { label: 'Current RMS (A)', val: latest.current_rms !== undefined ? `${latest.current_rms} A` : '-' },
    { label: 'Voltage Dev (%)', val: latest.voltage_dev !== undefined ? `${latest.voltage_dev}%` : '-' },
    { label: 'Current Dev (%)', val: latest.current_dev !== undefined ? `${latest.current_dev}%` : '-' },
    { label: 'Rotor Bar Sideband', val: latest.rotorbar || '-', status: latest.rotorbar_status },
    { label: 'Bearing High Freq', val: latest.bearing || '-', status: latest.bearing_status },
    { label: 'Load Level (%)', val: latest.load !== undefined ? `${latest.load}%` : '-' },
    { label: 'Total Harmonics THD', val: latest.thd !== undefined ? `${latest.thd}%` : '< 5%' },
    { label: 'Phase Angle Dev', val: latest.phase_dev !== undefined ? `${latest.phase_dev}°` : '< 1.5°' }
  ];

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-textMain">{eqDetail.equipment}</h3>
            <StatusBadge status={eqDetail.status} size="lg" />
          </div>
          <p className="text-[11px] text-muted mt-0.5 font-mono">
            Unit: {eqDetail.unit || 'UNIT 1'} · Tegangan: {eqDetail.voltage || '6.0 kV'} · Pengukuran: {eqDetail.latest_date || '-'}
          </p>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-muted block uppercase tracking-wider">Severity Status</span>
          <span className="text-xs font-bold text-cyan">{eqDetail.status || 'NORMAL'}</span>
        </div>
      </div>

      {/* Grid of Key Telemetry Parameters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {currentParams.map((param, i) => (
          <div key={i} className="p-3 bg-panel rounded-xl border border-line">
            <span className="text-[10px] text-muted uppercase tracking-wider block font-semibold">{param.label}</span>
            <strong className="text-sm text-textMain mt-1 block font-mono">{param.val}</strong>
            {param.status && (
              <div className="mt-1">
                <StatusBadge status={param.status} size="xs" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* AI Diagnostician Recommendation Section */}
      <div className="p-4 bg-panel2 rounded-xl border border-line">
        <h4 className="text-xs font-bold text-cyan flex items-center gap-2 mb-1.5">
          <span>🧠</span> Analisis &amp; Rekomendasi Maintenance MCSA
        </h4>
        <p className="text-xs text-textMain leading-relaxed">
          {eqDetail.recommendation || 'Kondisi spektrum arus dan harmonik motor dalam batas normal. Lanjutkan pengujian berkala setiap 30 hari sesuai jadwal predictive maintenance.'}
        </p>
      </div>
    </div>
  );
}
