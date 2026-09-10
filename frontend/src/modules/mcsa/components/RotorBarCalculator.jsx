import React, { useState } from 'react';
import { StatusBadge } from '../../../components/common';
import { apiFetch, apiUrl } from '../../../api';

export default function RotorBarCalculator({ onClose }) {
  const [calcUpper, setCalcUpper] = useState(-52.0);
  const [calcLower, setCalcLower] = useState(-54.0);
  const [calcHealth, setCalcHealth] = useState(0.85);
  const [calcResult, setCalcResult] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  const handleCalculate = async (e) => {
    e.preventDefault();
    setCalcLoading(true);
    try {
      const res = await apiFetch(apiUrl('/api/rotorbar/calculate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upper_sb: parseFloat(calcUpper),
          lower_sb: parseFloat(calcLower),
          health_index: parseFloat(calcHealth)
        })
      });
      const data = await res.json();
      setCalcResult(data);
    } catch (err) {
      console.error(err);
      alert('Gagal menghitung kondisi rotor bar.');
    } finally {
      setCalcLoading(false);
    }
  };

  return (
    <div className="border border-cyan/40 bg-panel2 rounded-2xl p-5 shadow-neon">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-bold text-cyan flex items-center gap-2">
          <span>⚡</span> Simulator & Evaluasi Severity Rotor Bar (Sideband dB)
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-muted hidden md:inline">
            Ambang: &lt; -54 dB (Normal) | -54 s/d -45 dB (Alarm) | &ge; -45 dB (High)
          </span>
          {onClose && (
            <button 
              onClick={onClose}
              className="text-muted hover:text-textMain text-xs px-2 py-0.5 rounded border border-line"
            >
              ✕ Tutup
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleCalculate} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
        <div>
          <label className="text-[11px] text-muted block mb-1">Upper Sideband (dB)</label>
          <input
            type="number"
            step="0.1"
            value={calcUpper}
            onChange={(e) => setCalcUpper(e.target.value)}
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
            required
          />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">Lower Sideband (dB)</label>
          <input
            type="number"
            step="0.1"
            value={calcLower}
            onChange={(e) => setCalcLower(e.target.value)}
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
            required
          />
        </div>
        <div>
          <label className="text-[11px] text-muted block mb-1">RB Health Index (Opsional)</label>
          <input
            type="number"
            step="0.01"
            value={calcHealth}
            onChange={(e) => setCalcHealth(e.target.value)}
            className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan"
          />
        </div>
        <div>
          <button
            type="submit"
            disabled={calcLoading}
            className="w-full py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs disabled:opacity-50"
          >
            {calcLoading ? 'Menghitung...' : 'Hitung Severity'}
          </button>
        </div>
      </form>

      {calcResult && (
        <div className="mt-4 p-3 bg-panel rounded-xl border border-line grid sm:grid-cols-4 gap-3 items-center">
          <div>
            <span className="text-[10px] text-muted block">Status Evaluasi:</span>
            <div className="mt-1">
              <StatusBadge status={calcResult.status} size="lg" />
            </div>
          </div>
          <div>
            <span className="text-[10px] text-muted block">Severity Level:</span>
            <strong className="text-sm text-textMain">Level {calcResult.severity_level || '-'}</strong>
          </div>
          <div>
            <span className="text-[10px] text-muted block">Sideband Terburuk:</span>
            <strong className="text-sm text-cyan">{calcResult.worst_db !== undefined ? `${calcResult.worst_db} dB` : '-'}</strong>
          </div>
          <div>
            <span className="text-[10px] text-muted block">Rekomendasi Teknis:</span>
            <small className="text-[11px] text-muted block leading-tight">{calcResult.notes || calcResult.recommendation || 'Normal'}</small>
          </div>
        </div>
      )}
    </div>
  );
}
