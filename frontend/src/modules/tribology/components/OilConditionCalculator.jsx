import React, { useState } from 'react';
import { StatusBadge } from '../../../components/common';

export default function OilConditionCalculator() {
  const [inputEq, setInputEq] = useState('Turbine Lube Oil System');
  const [inputVisc, setInputVisc] = useState(46.0);
  const [inputTan, setInputTan] = useState(0.15);
  const [inputWater, setInputWater] = useState(60);
  const [inputFe, setInputFe] = useState(10);
  const [evalResult, setEvalResult] = useState(null);

  const handleEvaluate = (e) => {
    e.preventDefault();
    let status = 'NORMAL';
    let notes = [];
    if (parseFloat(inputWater) > 200) {
      status = 'WARNING';
      notes.push('Kandungan air tinggi (>200 ppm), indikasi kebocoran pendingin atau kondensasi.');
    } else if (parseFloat(inputWater) > 100) {
      status = status === 'WARNING' ? status : 'PREWARNING';
      notes.push('Kandungan air meningkat (>100 ppm), jadwalkan pemurnian (oil purifier/centrifuge).');
    }

    if (parseFloat(inputTan) > 0.6) {
      status = 'WARNING';
      notes.push('Total Acid Number (TAN) kritis (>0.6 mgKOH/g), oli teroksidasi berat.');
    } else if (parseFloat(inputTan) > 0.3) {
      status = status === 'WARNING' ? status : 'PREWARNING';
      notes.push('TAN meningkat (>0.3 mgKOH/g), monitor laju degradasi aditif.');
    }

    if (parseFloat(inputFe) > 50) {
      status = 'WARNING';
      notes.push('Wear debris Fe tinggi (>50 ppm), indikasi keausan mekanikal bearing/komponen.');
    }

    if (notes.length === 0) {
      notes.push('Seluruh parameter oli pelumas berada dalam batas normal operasi.');
    }

    setEvalResult({ equipment: inputEq, status, notes });
  };

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      <div>
        <h4 className="text-xs font-bold text-amber uppercase tracking-wider">
          Quick Oil Condition &amp; Wear Evaluator
        </h4>
        <p className="text-[10px] text-muted mt-0.5">
          Verifikasi cepat status pelumas berdasarkan ambang batas ASTM / ISO 4406
        </p>
      </div>

      <form onSubmit={handleEvaluate} className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
        <div>
          <label className="text-[11px] text-muted block mb-1">Equipment / Sistem</label>
          <input type="text" value={inputEq} onChange={e => setInputEq(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-amber" />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">Viskositas @ 40°C (cSt)</label>
          <input type="number" step="0.1" value={inputVisc} onChange={e => setInputVisc(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-amber" required />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">TAN (mgKOH/g)</label>
          <input type="number" step="0.01" value={inputTan} onChange={e => setInputTan(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-amber" required />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">Water (ppm)</label>
          <input type="number" value={inputWater} onChange={e => setInputWater(e.target.value)} className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-amber" required />
        </div>
        <div>
          <button type="submit" className="w-full py-2 bg-amber text-[#071018] font-bold rounded-lg hover:bg-amber/90 transition-colors text-xs">
            Evaluasi Pelumas
          </button>
        </div>
      </form>

      {evalResult && (
        <div className="p-4 bg-panel rounded-xl border border-amber/30 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <strong className="text-xs text-textMain">{evalResult.equipment}</strong>
            <StatusBadge status={evalResult.status} size="lg" />
          </div>
          <ul className="list-disc list-inside text-xs text-muted space-y-1 mt-1">
            {evalResult.notes.map((note, idx) => (
              <li key={idx} className="text-textMain">{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
