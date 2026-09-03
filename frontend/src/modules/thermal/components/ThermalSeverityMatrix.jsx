import React from 'react';

export default function ThermalSeverityMatrix() {
  const criteria = [
    { deltaT: '1°C s/d 3°C', condition: 'Possible Deficiency (Normal/Low)', action: 'Monitoring berkala, re-inspeksi sesuai jadwal rutin' },
    { deltaT: '4°C s/d 10°C', condition: 'Probable Deficiency (Prewarning)', action: 'Investigasi pada jadwal pemeliharaan terdekat' },
    { deltaT: '11°C s/d 20°C', condition: 'Deficiency Exists (Warning/High)', action: 'Jadwalkan perbaikan dalam 1-2 minggu' },
    { deltaT: '> 20°C', condition: 'Major Deficiency (Critical/Alarm)', action: 'Tindakan mitigasi atau shutdown segera untuk cegah kebakaran/kerusakan' }
  ];

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 flex flex-col gap-3">
      <div>
        <h4 className="text-xs font-bold text-orange-400 uppercase tracking-wider">
          Standar Evaluasi NETA MTS / IEC Delta-T (ΔT)
        </h4>
        <p className="text-[10px] text-muted mt-0.5">
          Perbedaan temperatur antara komponen uji dan komponen referensi serupa di bawah beban yang sama
        </p>
      </div>

      <div className="overflow-x-auto border border-line rounded-xl bg-panel">
        <table className="w-full text-left text-xs">
          <thead className="bg-panel2 text-[10px] uppercase tracking-wider text-muted border-b border-line">
            <tr>
              <th className="p-2.5">Kategori Delta-T</th>
              <th className="p-2.5">Tingkat Keparahan</th>
              <th className="p-2.5">Tindakan Rekomendasi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/40">
            {criteria.map((c, idx) => (
              <tr key={idx} className="hover:bg-panel2/60 transition-colors">
                <td className="p-2.5 font-mono font-bold text-orange-400">{c.deltaT}</td>
                <td className="p-2.5 font-semibold text-textMain">{c.condition}</td>
                <td className="p-2.5 text-[11px] text-muted">{c.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
