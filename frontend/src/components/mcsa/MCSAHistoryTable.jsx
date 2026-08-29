import React from 'react';
import { StatusBadge } from '../common';

export default function MCSAHistoryTable({ history = [] }) {
  if (!history || history.length === 0) {
    return (
      <div className="p-6 text-center text-muted text-xs bg-panel rounded-xl border border-line">
        Belum ada riwayat pengujian tercatat untuk motor ini.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-line rounded-xl bg-panel">
      <table className="w-full text-left text-xs">
        <thead className="bg-panel2 text-[10px] uppercase tracking-wider text-muted border-b border-line">
          <tr>
            <th className="p-2.5">Tanggal</th>
            <th className="p-2.5">Status</th>
            <th className="p-2.5">Rotor Bar</th>
            <th className="p-2.5">Bearing</th>
            <th className="p-2.5">Dev Volt (%)</th>
            <th className="p-2.5">Dev Curr (%)</th>
            <th className="p-2.5">Load (%)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line/40 font-mono">
          {history.map((row, idx) => (
            <tr key={idx} className="hover:bg-panel2/60 transition-colors">
              <td className="p-2.5 text-textMain">{row.date || '-'}</td>
              <td className="p-2.5">
                <StatusBadge status={row.status} size="xs" />
              </td>
              <td className="p-2.5 text-textMain">{row.rotorbar || '-'}</td>
              <td className="p-2.5 text-textMain">{row.bearing || '-'}</td>
              <td className="p-2.5 text-textMain">{row.voltage_dev !== undefined ? `${row.voltage_dev}%` : '-'}</td>
              <td className="p-2.5 text-textMain">{row.current_dev !== undefined ? `${row.current_dev}%` : '-'}</td>
              <td className="p-2.5 text-textMain">{row.load !== undefined ? `${row.load}%` : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
