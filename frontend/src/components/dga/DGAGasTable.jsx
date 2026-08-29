import React from 'react';

export default function DGAGasTable({ trfDetail }) {
  if (!trfDetail) {
    return (
      <div className="p-6 text-center text-muted text-xs bg-panel rounded-xl border border-line">
        Pilih transformator untuk melihat konsentrasi gas terlarut (ppm) dan rasio diagnostik.
      </div>
    );
  }

  const g = trfDetail.gases || trfDetail.latest_sample || {};
  const gasRows = [
    { name: 'Hydrogen (H₂)', ppm: g.h2 ?? 15, limit: '100 ppm', fault: 'Partial Discharge / Corona' },
    { name: 'Methane (CH₄)', ppm: g.ch4 ?? 25, limit: '120 ppm', fault: 'Low Temp Thermal (<150°C)' },
    { name: 'Ethane (C₂H₆)', ppm: g.c2h6 ?? 8, limit: '65 ppm', fault: 'Thermal Fault (150-300°C)' },
    { name: 'Ethylene (C₂H₄)', ppm: g.c2h4 ?? 65, limit: '50 ppm', fault: 'High Temp Thermal (>300°C)' },
    { name: 'Acetylene (C₂H₂)', ppm: g.c2h2 ?? 4, limit: '1 ppm', fault: 'Arcing / High Energy Discharge' },
    { name: 'Carbon Monoxide (CO)', ppm: g.co ?? 250, limit: '350 ppm', fault: 'Cellulose Insulation Degradation' },
    { name: 'Carbon Dioxide (CO₂)', ppm: g.co2 ?? 1800, limit: '2500 ppm', fault: 'Paper Thermal Ageing' },
    { name: 'Oxygen (O₂)', ppm: g.o2 ?? 4200, limit: 'N/A', fault: 'Atmospheric Ingress' },
    { name: 'Nitrogen (N₂)', ppm: g.n2 ?? 48000, limit: 'N/A', fault: 'Atmospheric Baseline' }
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto border border-line rounded-xl bg-panel">
        <table className="w-full text-left text-xs">
          <thead className="bg-panel2 text-[10px] uppercase tracking-wider text-muted border-b border-line">
            <tr>
              <th className="p-2.5">Gas Terlarut</th>
              <th className="p-2.5">Konsentrasi (ppm)</th>
              <th className="p-2.5">Batas Normal IEEE</th>
              <th className="p-2.5">Indikasi Kerusakan Utama</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/40 font-mono">
            {gasRows.map((row, idx) => (
              <tr key={idx} className="hover:bg-panel2/60 transition-colors">
                <td className="p-2.5 font-bold text-textMain">{row.name}</td>
                <td className="p-2.5 font-bold text-cyan">{row.ppm} ppm</td>
                <td className="p-2.5 text-muted">{row.limit}</td>
                <td className="p-2.5 text-[11px] text-textMain font-sans">{row.fault}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary Gas Metric Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">TDCG Score</span>
          <strong className="text-sm text-cyan font-mono">{trfDetail.tdcg ?? (g.h2 + g.ch4 + g.c2h6 + g.c2h4 + g.c2h2 + g.co)} ppm</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">CO₂ / CO Ratio</span>
          <strong className="text-sm text-textMain font-mono">{((g.co2 || 1800) / (g.co || 250)).toFixed(2)}</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Rogers Ratio CH₄/H₂</span>
          <strong className="text-sm text-textMain font-mono">{((g.ch4 || 25) / (g.h2 || 15)).toFixed(2)}</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block uppercase">Rogers Ratio C₂H₄/C₂H₆</span>
          <strong className="text-sm text-textMain font-mono">{((g.c2h4 || 65) / (g.c2h6 || 8)).toFixed(2)}</strong>
        </div>
      </div>
    </div>
  );
}
