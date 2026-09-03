import React, { useState } from 'react';
import { StatusBadge } from '../../../components/common';
import DuvalTriangleVisualizer from './DuvalTriangleVisualizer';

export default function DGACalculator() {
  const [h2, setH2] = useState(15);
  const [ch4, setCh4] = useState(25);
  const [c2h6, setC2h6] = useState(8);
  const [c2h4, setC2h4] = useState(65);
  const [c2h2, setC2h2] = useState(4);
  const [co, setCo] = useState(250);
  const [co2, setCo2] = useState(1800);
  const [simResult, setSimResult] = useState(null);

  const handleManualAnalyze = (e) => {
    e?.preventDefault();
    const tdcg = parseFloat(h2) + parseFloat(ch4) + parseFloat(c2h6) + parseFloat(c2h4) + parseFloat(c2h2) + parseFloat(co);
    const ch4_val = parseFloat(ch4);
    const c2h4_val = parseFloat(c2h4);
    const c2h2_val = parseFloat(c2h2);
    const sum_duval = ch4_val + c2h4_val + c2h2_val || 1;
    const pct_ch4 = (ch4_val / sum_duval) * 100;
    const pct_c2h4 = (c2h4_val / sum_duval) * 100;
    const pct_c2h2 = (c2h2_val / sum_duval) * 100;

    let duvalDiag = 'PD (Partial Discharge)';
    if (pct_c2h2 > 13) {
      duvalDiag = 'D2 (Discharges of High Energy / Arcing)';
    } else if (pct_c2h2 > 4 && pct_c2h4 > 20) {
      duvalDiag = 'D1 (Discharges of Low Energy / Sparking)';
    } else if (pct_c2h4 >= 50) {
      duvalDiag = 'T3 (Thermal Fault T > 700°C)';
    } else if (pct_c2h4 >= 20 && pct_ch4 >= 50) {
      duvalDiag = 'T2 (Thermal Fault 300°C < T < 700°C)';
    } else if (pct_ch4 >= 98) {
      duvalDiag = 'PD (Partial Discharge)';
    } else {
      duvalDiag = 'T1 (Thermal Fault T < 300°C)';
    }

    let ieeeCond = 'Condition 1 (Normal)';
    if (tdcg > 4630) ieeeCond = 'Condition 4 (Critical)';
    else if (tdcg > 1920) ieeeCond = 'Condition 3 (Alarm)';
    else if (tdcg > 720) ieeeCond = 'Condition 2 (Warning)';

    setSimResult({
      tdcg: tdcg.toFixed(0),
      duval: duvalDiag,
      ieee: ieeeCond,
      pct_ch4,
      pct_c2h4,
      pct_c2h2
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
        <h4 className="text-xs font-bold text-cyan uppercase tracking-wider mb-3">
          Simulator Analisis DGA (Input Gas Konsentrasi ppm)
        </h4>

        <form onSubmit={handleManualAnalyze} className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 items-end">
          <div>
            <label className="text-[10px] text-muted block mb-1">H₂ (ppm)</label>
            <input type="number" value={h2} onChange={e => setH2(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">CH₄ (ppm)</label>
            <input type="number" value={ch4} onChange={e => setCh4(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">C₂H₆ (ppm)</label>
            <input type="number" value={c2h6} onChange={e => setC2h6(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">C₂H₄ (ppm)</label>
            <input type="number" value={c2h4} onChange={e => setC2h4(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">C₂H₂ (ppm)</label>
            <input type="number" value={c2h2} onChange={e => setC2h2(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">CO (ppm)</label>
            <input type="number" value={co} onChange={e => setCo(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div>
            <label className="text-[10px] text-muted block mb-1">CO₂ (ppm)</label>
            <input type="number" value={co2} onChange={e => setCo2(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" required />
          </div>
          <div className="col-span-2 sm:col-span-4 lg:col-span-7 mt-2">
            <button type="submit" className="w-full py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs">
              Jalankan Diagnosa Duval &amp; IEEE C57.104
            </button>
          </div>
        </form>
      </div>

      {simResult && (
        <div className="flex flex-col gap-4">
          <div className="p-4 bg-panel rounded-xl border border-cyan/30 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <span className="text-[10px] text-muted block">Hasil Kondisi IEEE C57.104:</span>
              <div className="mt-1">
                <StatusBadge status={simResult.ieee} size="lg" />
              </div>
            </div>
            <div className="font-mono">
              <span className="text-[10px] text-muted block">TDCG Terhitung:</span>
              <strong className="text-sm text-cyan">{simResult.tdcg} ppm</strong>
            </div>
            <div>
              <span className="text-[10px] text-muted block">Diagnosa Duval Triangle:</span>
              <strong className="text-sm text-amber">{simResult.duval}</strong>
            </div>
          </div>

          <DuvalTriangleVisualizer
            pctCh4={simResult.pct_ch4}
            pctC2h4={simResult.pct_c2h4}
            pctC2h2={simResult.pct_c2h2}
            diagnosis={simResult.duval}
          />
        </div>
      )}
    </div>
  );
}
