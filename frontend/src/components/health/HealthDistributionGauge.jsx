import React from 'react';

export default function HealthDistributionGauge({
  healthPercent = 85,
  loading = false,
  normalCount = 0,
  alarmCount = 0,
  highCount = 0,
  total = 1
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
      <h3 className="text-sm font-bold text-textMain mb-4">Plant Health Index &amp; Reliability Score</h3>
      <div className="grid sm:grid-cols-[180px_1fr] gap-5 items-center">
        <div className="grid place-items-center relative">
          <div
            className="w-[150px] h-[150px] rounded-full flex items-center justify-center relative"
            style={{
              background: `conic-gradient(var(--green) 0 ${healthPercent}%, var(--line) ${healthPercent}% 100%)`
            }}
          >
            <div className="absolute inset-[10px] rounded-full bg-panel border border-line"></div>
            <div className="relative text-center z-10">
              <strong className="text-3xl tracking-tight text-textMain">{loading ? '-' : `${healthPercent}%`}</strong>
              <span className="block text-muted text-[9px] uppercase tracking-widest mt-0.5">Reliability</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="p-3 bg-panel2 rounded-xl border border-line">
            <div className="text-[11px] text-textMain font-semibold">Distribusi Kondisi Peralatan:</div>
            <div className="w-full bg-panel rounded-full h-3 mt-2 flex overflow-hidden border border-line">
              <div style={{ width: `${(normalCount / total) * 100}%` }} className="bg-green transition-all" title="Normal"></div>
              <div style={{ width: `${(alarmCount / total) * 100}%` }} className="bg-amber transition-all" title="Alarm"></div>
              <div style={{ width: `${(highCount / total) * 100}%` }} className="bg-red transition-all" title="High"></div>
            </div>
            <div className="flex justify-between items-center text-[10px] mt-2 font-mono">
              <span className="text-green font-bold">🟢 Normal: {normalCount} ({Math.round((normalCount / total) * 100)}%)</span>
              <span className="text-amber font-bold">🟡 Alarm: {alarmCount} ({Math.round((alarmCount / total) * 100)}%)</span>
              <span className="text-red font-bold">🔴 High: {highCount} ({Math.round((highCount / total) * 100)}%)</span>
            </div>
          </div>

          <div className="text-[11px] text-muted leading-relaxed">
            Index dihitung secara otomatis berdasarkan status telemetri MCSA, Vibrasi ISO 10816, DGA, Tribology, dan Inspeksi Thermal.
          </div>
        </div>
      </div>
    </div>
  );
}
