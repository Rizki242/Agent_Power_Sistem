import React from 'react';

export default function WearDebrisPanel({ sampleDetail }) {
  const w = sampleDetail?.wear_metals || {
    fe: 8,
    cu: 3,
    al: 2,
    pb: 1,
    cr: 0.5,
    sn: 0.2,
    si: 12,
    na: 4
  };

  const wearMetals = [
    { element: 'Besi (Fe)', ppm: w.fe, limit: '< 30 ppm', source: 'Cylinder / Shaft / Gear tooth wear' },
    { element: 'Tembaga (Cu)', ppm: w.cu, limit: '< 15 ppm', source: 'Brass cage / Bushing / Cooler tube' },
    { element: 'Aluminium (Al)', ppm: w.al, limit: '< 10 ppm', source: 'Piston / Housing / Impeller' },
    { element: 'Timbal (Pb)', ppm: w.pb, limit: '< 10 ppm', source: 'Babbitt journal bearing overlay' },
    { element: 'Kromium (Cr)', ppm: w.cr, limit: '< 5 ppm', source: 'Piston ring / Roller bearing' },
    { element: 'Silikon (Si)', ppm: w.si, limit: '< 20 ppm', source: 'Dirt / Airborne dust / Antifoam' },
    { element: 'Natrium (Na)', ppm: w.na, limit: '< 20 ppm', source: 'Coolant leak / Saltwater ingress' },
    { element: 'Timah (Sn)', ppm: w.sn, limit: '< 10 ppm', source: 'Babbitt alloy lining' }
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto border border-line rounded-xl bg-panel">
        <table className="w-full text-left text-xs">
          <thead className="bg-panel2 text-[10px] uppercase tracking-wider text-muted border-b border-line">
            <tr>
              <th className="p-2.5">Unsur Logam Keausan / Kontaminan</th>
              <th className="p-2.5">Konsentrasi (ppm)</th>
              <th className="p-2.5">Limit Normal</th>
              <th className="p-2.5">Potensi Sumber Komponen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/40 font-mono">
            {wearMetals.map((m, idx) => (
              <tr key={idx} className="hover:bg-panel2/60 transition-colors">
                <td className="p-2.5 font-bold text-textMain">{m.element}</td>
                <td className="p-2.5 font-bold text-amber">{m.ppm} ppm</td>
                <td className="p-2.5 text-muted">{m.limit}</td>
                <td className="p-2.5 text-[11px] text-textMain font-sans">{m.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
