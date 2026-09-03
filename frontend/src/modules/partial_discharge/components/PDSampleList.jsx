import React from 'react';
import { StatusBadge } from '../../../components/common';

export default function PDSampleList({ samples, loading, selectedSampleId, onSelect }) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-xs text-muted">
          Menampilkan <strong className="text-textMain">{samples.length}</strong> titik pengukuran PD
        </span>
      </div>

      <div className="overflow-x-auto max-h-[280px] overflow-y-auto pr-1">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 bg-panel border-b border-line z-10">
            <tr className="text-muted">
              <th className="py-2.5 px-3 font-semibold">Equipment</th>
              <th className="py-2.5 px-3 font-semibold">Unit</th>
              <th className="py-2.5 px-3 font-semibold">Metode</th>
              <th className="py-2.5 px-3 font-semibold">Magnitudo (pC)</th>
              <th className="py-2.5 px-3 font-semibold">NQN</th>
              <th className="py-2.5 px-3 font-semibold">Tipe Discharge</th>
              <th className="py-2.5 px-3 font-semibold">Status</th>
              <th className="py-2.5 px-3 font-semibold text-right">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {loading ? (
              <tr>
                <td colSpan="8" className="py-8 text-center text-muted">Memuat data sampel partial discharge...</td>
              </tr>
            ) : samples.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-8 text-center text-muted">Tidak ada sampel yang sesuai filter.</td>
              </tr>
            ) : (
              samples.map((s) => (
                <tr
                  key={s.sample_id}
                  className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedSampleId === s.sample_id ? 'bg-panel2 border-l-2 border-l-purple-400 font-medium' : ''}`}
                  onClick={() => onSelect(s.sample_id)}
                >
                  <td className="py-2.5 px-3 font-bold text-textMain">{s.equipment}</td>
                  <td className="py-2.5 px-3 text-muted">{s.unit}</td>
                  <td className="py-2.5 px-3 text-muted">{s.method || '-'}</td>
                  <td className="py-2.5 px-3 font-mono text-cyan font-bold">{s.pulse_magnitude_pc ?? '-'}</td>
                  <td className="py-2.5 px-3 font-mono text-textMain">{s.nqn ?? '-'}</td>
                  <td className="py-2.5 px-3 text-muted">{s.pd_type || '-'}</td>
                  <td className="py-2.5 px-3"><StatusBadge status={s.status} /></td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); onSelect(s.sample_id); }}
                      className="px-2.5 py-1 rounded bg-panel border border-line text-purple-400 hover:border-purple-400 text-[11px]"
                    >
                      Detail →
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
