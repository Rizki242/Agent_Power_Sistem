import React from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../common';

export default function VibrationMeasurementList({
  testsList = [],
  loading,
  selectedTest,
  onSelectTest
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Pengujian Periodik ISO 10816 ({testsList.length})
        </h3>
        <span className="text-[10px] text-cyan">Database Riwayat</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] pr-1 space-y-1.5">
        {loading ? (
          <LoadingSpinner message="Memuat rekaman pengujian getaran..." />
        ) : testsList.length === 0 ? (
          <EmptyState title="Tidak ada rekaman pengujian ditemukan" />
        ) : (
          testsList.map((test, idx) => {
            const isSelected = selectedTest && (selectedTest.report_id === test.report_id || (selectedTest.equipment === test.equipment && selectedTest.date === test.date));
            return (
              <div
                key={idx}
                onClick={() => onSelectTest(test)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex justify-between items-center ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_12px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <strong className="text-xs text-textMain font-semibold">{test.equipment}</strong>
                    <span className="text-[10px] text-muted font-mono">{test.unit}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-0.5 flex gap-2">
                    <span>Tgl: {test.date || '-'}</span>
                    <span>·</span>
                    <span>Vel: {test.velocity_rms || test.overall_velocity || '-'} mm/s</span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <StatusBadge status={test.status || test.iso_zone} />
                  <span className="text-[10px] text-muted font-mono">{test.iso_zone || 'ISO 10816'}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
