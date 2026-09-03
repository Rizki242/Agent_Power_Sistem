import React, { useState } from 'react';
import { StatusBadge } from '../../../components/common';

export default function ISO10816Evaluator() {
  const [eqName, setEqName] = useState('');
  const [vibVelocity, setVibVelocity] = useState(3.4);
  const [vibAcc, setVibAcc] = useState(1.2);
  const [vibGroup, setVibGroup] = useState('Group 1 (Rigid)');
  const [evalResult, setEvalResult] = useState(null);

  const handleEvaluate = (e) => {
    e.preventDefault();
    const vel = parseFloat(vibVelocity);
    let zone = 'Zone A (Good)';
    let status = 'NORMAL';
    let rec = 'Kondisi getaran sangat baik; lanjutkan monitoring berkala.';

    if (vel > 7.1) {
      zone = 'Zone D (Unacceptable)';
      status = 'HIGH';
      rec = 'Kondisi getaran kritis (>7.1 mm/s RMS). Rencanakan shutdown/mitigasi segera, periksa spektrum untuk unbalance/misalignment berat atau kerusakan bearing.';
    } else if (vel > 4.5) {
      zone = 'Zone C (Restricted Operation)';
      status = 'ALARM';
      rec = 'Getaran dalam rentang waspada (4.5 - 7.1 mm/s RMS). Lakukan survei vibrasi terarah dan periksa kelonggaran baut pondasi/alignment.';
    } else if (vel > 2.8) {
      zone = 'Zone B (Acceptable)';
      status = 'PREWARNING';
      rec = 'Getaran dapat diterima untuk operasi jangka panjang tanpa batasan.';
    }

    setEvalResult({
      equipment: eqName || 'Manual Input',
      velocity_rms: vel,
      acceleration_g: parseFloat(vibAcc),
      iso_zone: zone,
      status: status,
      recommendation: rec
    });
  };

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      <div className="flex justify-between items-center pb-3 border-b border-line">
        <div>
          <h3 className="text-sm font-bold text-cyan flex items-center gap-2">
            <span>🎛️</span> ISO 10816-3 Quick Severity Evaluator
          </h3>
          <p className="text-[10px] text-muted mt-0.5">
            Standar evaluasi getaran mekanikal mesin industri daya &gt; 300 kW (Pondasi Rigid / Flexible)
          </p>
        </div>
      </div>

      <form onSubmit={handleEvaluate} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div>
          <label className="text-[11px] text-muted block mb-1">Nama / Tag Equipment</label>
          <input
            type="text"
            value={eqName}
            onChange={(e) => setEqName(e.target.value)}
            placeholder="mis. BFP 1A, IDF 2B..."
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
          />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">Velocity RMS (mm/s)</label>
          <input
            type="number"
            step="0.01"
            value={vibVelocity}
            onChange={(e) => setVibVelocity(e.target.value)}
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
            required
          />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">Acceleration Peak (g)</label>
          <input
            type="number"
            step="0.01"
            value={vibAcc}
            onChange={(e) => setVibAcc(e.target.value)}
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
          />
        </div>
        <div>
          <button
            type="submit"
            className="w-full py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs"
          >
            Evaluasi Kondisi
          </button>
        </div>
      </form>

      {evalResult && (
        <div className="p-4 bg-panel rounded-xl border border-cyan/30 flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <strong className="text-xs text-textMain">{evalResult.equipment}</strong>
              <StatusBadge status={evalResult.status} size="lg" />
            </div>
            <span className="text-xs font-mono font-bold text-cyan">{evalResult.iso_zone}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-panel2 p-3 rounded-lg border border-line font-mono">
            <div>
              <span className="text-[10px] text-muted block">Velocity RMS:</span>
              <strong className="text-textMain">{evalResult.velocity_rms} mm/s</strong>
            </div>
            <div>
              <span className="text-[10px] text-muted block">Acceleration:</span>
              <strong className="text-textMain">{evalResult.acceleration_g} g</strong>
            </div>
            <div>
              <span className="text-[10px] text-muted block">Zone Limit:</span>
              <span className="text-muted text-[11px]">C: 4.5 | D: 7.1 mm/s</span>
            </div>
            <div>
              <span className="text-[10px] text-muted block">Keputusan CBM:</span>
              <span className="text-cyan font-bold">{evalResult.status}</span>
            </div>
          </div>
          <p className="text-xs text-textMain leading-relaxed bg-panel2/50 p-3 rounded-lg border border-line/60">
            <strong>Rekomendasi Diagnostik:</strong> {evalResult.recommendation}
          </p>
        </div>
      )}
    </div>
  );
}
