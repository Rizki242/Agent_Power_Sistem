import React from 'react';
import { StatusBadge } from '../../../components/common';

export default function VibrationPointMatrix({ testDetail, points = [] }) {
  const measurementPoints = points.length > 0 ? points : (testDetail?.points || [
    { pos: 'DE-H (Drive End Horizontal)', vel: testDetail?.de_h_vel || '2.4', acc: testDetail?.de_h_acc || '0.8', status: 'NORMAL' },
    { pos: 'DE-V (Drive End Vertical)', vel: testDetail?.de_v_vel || '1.8', acc: testDetail?.de_v_acc || '0.6', status: 'NORMAL' },
    { pos: 'DE-A (Drive End Axial)', vel: testDetail?.de_a_vel || '1.2', acc: testDetail?.de_a_acc || '0.4', status: 'NORMAL' },
    { pos: 'NDE-H (Non-Drive End Horiz)', vel: testDetail?.nde_h_vel || '3.1', acc: testDetail?.nde_h_acc || '1.1', status: 'PREWARNING' },
    { pos: 'NDE-V (Non-Drive End Vert)', vel: testDetail?.nde_v_vel || '2.2', acc: testDetail?.nde_v_acc || '0.7', status: 'NORMAL' },
    { pos: 'NDE-A (Non-Drive End Axial)', vel: testDetail?.nde_a_vel || '1.5', acc: testDetail?.nde_a_acc || '0.5', status: 'NORMAL' }
  ]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-between items-center">
        <h4 className="text-xs font-bold text-textMain uppercase tracking-wider">
          Matriks Titik Pengukuran Vibrasi (DE / NDE)
        </h4>
        <span className="text-[10px] text-muted">Satuan: Velocity (mm/s RMS) · Acceleration (g pk)</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {measurementPoints.map((pt, i) => (
          <div key={i} className="p-3 bg-panel rounded-xl border border-line flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <span className="text-xs font-bold text-textMain">{pt.pos || pt.point_name}</span>
              <StatusBadge status={pt.status || 'NORMAL'} size="xs" />
            </div>
            <div className="grid grid-cols-2 gap-2 mt-3 pt-2 border-t border-line/50 font-mono">
              <div>
                <span className="text-[10px] text-muted block">Velocity</span>
                <strong className="text-xs text-cyan">{pt.vel || pt.velocity_rms || '-'} mm/s</strong>
              </div>
              <div>
                <span className="text-[10px] text-muted block">Acceleration</span>
                <strong className="text-xs text-textMain">{pt.acc || pt.acceleration_g || '-'} g</strong>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
