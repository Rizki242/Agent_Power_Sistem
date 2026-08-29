import React from 'react';

export default function VibrationBearingSpecs({ eqDetail }) {
  if (!eqDetail) {
    return (
      <div className="p-6 text-center text-muted text-xs bg-panel rounded-xl border border-line">
        Pilih aset untuk melihat spesifikasi bearing dan frekuensi cacat (BPFO, BPFI, BSF, FTF).
      </div>
    );
  }

  const deBearing = eqDetail.bearing_de_info || { model: eqDetail.bearing_de || 'SKF 6318 C3', bpfo: '3.58x', bpfi: '5.42x', bsf: '2.31x', ftf: '0.40x' };
  const ndeBearing = eqDetail.bearing_nde_info || { model: eqDetail.bearing_nde || 'SKF 6316 C3', bpfo: '3.62x', bpfi: '5.38x', bsf: '2.28x', ftf: '0.41x' };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid sm:grid-cols-2 gap-3">
        {/* Drive End (DE) */}
        <div className="p-4 bg-panel rounded-xl border border-line">
          <div className="flex justify-between items-center pb-2 border-b border-line">
            <span className="text-xs font-bold text-cyan uppercase tracking-wider">Drive End (DE) Bearing</span>
            <span className="text-[10px] text-textMain font-mono font-bold bg-panel2 px-2 py-0.5 rounded border border-line">{deBearing.model}</span>
          </div>
          <div className="grid grid-cols-4 gap-2 mt-3 text-center font-mono">
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BPFO</span>
              <strong className="text-xs text-textMain">{deBearing.bpfo || '3.58x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BPFI</span>
              <strong className="text-xs text-textMain">{deBearing.bpfi || '5.42x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BSF</span>
              <strong className="text-xs text-textMain">{deBearing.bsf || '2.31x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">FTF</span>
              <strong className="text-xs text-textMain">{deBearing.ftf || '0.40x'}</strong>
            </div>
          </div>
        </div>

        {/* Non-Drive End (NDE) */}
        <div className="p-4 bg-panel rounded-xl border border-line">
          <div className="flex justify-between items-center pb-2 border-b border-line">
            <span className="text-xs font-bold text-amber uppercase tracking-wider">Non-Drive End (NDE) Bearing</span>
            <span className="text-[10px] text-textMain font-mono font-bold bg-panel2 px-2 py-0.5 rounded border border-line">{ndeBearing.model}</span>
          </div>
          <div className="grid grid-cols-4 gap-2 mt-3 text-center font-mono">
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BPFO</span>
              <strong className="text-xs text-textMain">{ndeBearing.bpfo || '3.62x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BPFI</span>
              <strong className="text-xs text-textMain">{ndeBearing.bpfi || '5.38x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">BSF</span>
              <strong className="text-xs text-textMain">{ndeBearing.bsf || '2.28x'}</strong>
            </div>
            <div className="p-2 bg-panel2 rounded-lg">
              <span className="text-[9px] text-muted block">FTF</span>
              <strong className="text-xs text-textMain">{ndeBearing.ftf || '0.41x'}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Equipment Mechanical Baseline */}
      <div className="p-3.5 bg-panel2 rounded-xl border border-line grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <span className="text-[10px] text-muted block">Kecepatan Rotasi (RPM):</span>
          <strong className="text-textMain font-mono">{eqDetail.rpm || eqDetail.speed_rpm || '1485 RPM'}</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Running Frequency (1X):</span>
          <strong className="text-textMain font-mono">{((eqDetail.rpm || 1485) / 60).toFixed(2)} Hz</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Tipe Pondasi / Mount:</span>
          <strong className="text-textMain">{eqDetail.foundation || 'Rigid Concrete Foundation'}</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Kelas ISO 10816:</span>
          <strong className="text-cyan font-bold">{eqDetail.equipment_class || 'Class III (Group 1 Rigid)'}</strong>
        </div>
      </div>
    </div>
  );
}
