import React from 'react';
import { StatusBadge } from '../../../components/common';

export default function OilPropertiesGrid({ sampleDetail }) {
  if (!sampleDetail) {
    return (
      <div className="p-6 text-center text-muted text-xs bg-panel rounded-xl border border-line">
        Pilih sampel oli untuk melihat sifat fisikokimia pelumas (viskositas, keasaman TAN, air, cleanliness).
      </div>
    );
  }

  const p = sampleDetail.parameters || sampleDetail;
  const propList = [
    { label: 'Viskositas @ 40°C', val: p.viscosity_40 !== undefined ? `${p.viscosity_40} cSt` : '46.2 cSt', std: 'ASTM D445 (±10% VG)' },
    { label: 'Viskositas @ 100°C', val: p.viscosity_100 !== undefined ? `${p.viscosity_100} cSt` : '6.8 cSt', std: 'ASTM D445' },
    { label: 'Total Acid Number (TAN)', val: p.tan !== undefined ? `${p.tan} mgKOH/g` : '0.18 mgKOH/g', std: 'ASTM D664 (<0.5)' },
    { label: 'Kandungan Air (Water)', val: p.water_ppm !== undefined ? `${p.water_ppm} ppm` : '45 ppm', std: 'ASTM D6304 (<100 ppm)' },
    { label: 'ISO 4406 Cleanliness', val: p.iso_cleanliness || '17/15/12', std: 'ISO 4406 (4μ/6μ/14μ)' },
    { label: 'Flash Point (°C)', val: p.flash_point !== undefined ? `${p.flash_point}°C` : '> 210°C', std: 'ASTM D92' },
    { label: 'Dielectric Breakdown', val: p.dielectric !== undefined ? `${p.dielectric} kV` : '> 30 kV', std: 'ASTM D877 (Insulating)' },
    { label: 'Foaming Tendency', val: p.foaming || '0 / 0 ml', std: 'ASTM D892 (Seq I/II)' }
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center pb-2 border-b border-line">
        <div>
          <h4 className="text-xs font-bold text-amber uppercase tracking-wider">
            Karakteristik Fisikokimia Pelumas
          </h4>
          <span className="text-[10px] text-muted font-mono">{sampleDetail.equipment} · {sampleDetail.oil_type || 'ISO VG 46'}</span>
        </div>
        <StatusBadge status={sampleDetail.status} size="lg" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {propList.map((item, i) => (
          <div key={i} className="p-3 bg-panel rounded-xl border border-line">
            <span className="text-[10px] text-muted uppercase tracking-wider block font-semibold">{item.label}</span>
            <strong className="text-sm text-textMain mt-1 block font-mono">{item.val}</strong>
            <small className="text-[9px] text-muted block mt-0.5">{item.std}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
