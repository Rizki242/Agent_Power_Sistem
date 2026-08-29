import React from 'react';

export default function WorkOrderDetailCard({
  selectedWO,
  engineerName,
  onAction
}) {
  if (!selectedWO) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8 text-center text-muted text-xs">
        Pilih Work Order dari daftar di samping untuk melakukan verifikasi teknis dan otorisasi.
      </div>
    );
  }

  const isApproved = selectedWO.status === 'APPROVED' || selectedWO.status === 'IN-PROGRESS';

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      {/* Header Info */}
      <div className="flex justify-between items-start pb-3 border-b border-line">
        <div>
          <span className="text-[10px] font-mono text-cyan font-bold block uppercase tracking-wider">{selectedWO.wo_number}</span>
          <h3 className="text-base font-bold text-textMain mt-0.5">{selectedWO.task_title || selectedWO.equipment}</h3>
        </div>
        <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${
          isApproved 
            ? 'bg-green/10 text-green border-green/30' 
            : 'bg-amber/10 text-amber border-amber/30'
        }`}>
          {selectedWO.status}
        </span>
      </div>

      {/* Target Equipment & Scope Detail */}
      <div className="grid grid-cols-2 gap-2 text-xs bg-panel p-3 rounded-xl border border-line">
        <div>
          <span className="text-[10px] text-muted block">Target Unit / Asset:</span>
          <strong className="text-textMain font-mono">{selectedWO.equipment}</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Estimasi Durasi / Man-hours:</span>
          <strong className="text-cyan font-mono">{selectedWO.estimated_hours || '4.0 Jam (2 Teknisi)'}</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Spesialisasi Tim:</span>
          <strong className="text-textMain">{selectedWO.assigned_discipline || 'Mechanical / Electrical Maintenance'}</strong>
        </div>
        <div>
          <span className="text-[10px] text-muted block">Tools &amp; Spare Parts:</span>
          <strong className="text-textMain">{selectedWO.parts_required || 'Torque Wrench, Alignment Kit'}</strong>
        </div>
      </div>

      {/* Action Steps Scope */}
      <div className="p-4 bg-panel2 rounded-xl border border-line">
        <h4 className="text-xs font-bold text-cyan flex items-center gap-1.5 mb-2">
          <span>🛠️</span> Ruang Lingkup Tindakan Pemeliharaan
        </h4>
        <p className="text-xs text-textMain leading-relaxed whitespace-pre-line">
          {selectedWO.description || selectedWO.action_plan}
        </p>
      </div>

      {/* Human In The Loop Approval Action Box */}
      <div className="p-4 bg-panel rounded-xl border border-cyan/30 flex flex-col gap-3">
        <div className="flex justify-between items-center text-xs">
          <div>
            <span className="text-[10px] text-muted block">Otorisator (Human-in-the-Loop):</span>
            <strong className="text-textMain">{engineerName}</strong>
          </div>
          {selectedWO.approved_by && (
            <span className="text-[10px] text-green font-mono">Disetujui oleh: {selectedWO.approved_by}</span>
          )}
        </div>

        <div className="flex gap-2 pt-2 border-t border-line/40">
          <button
            onClick={() => onAction && onAction('APPROVE')}
            disabled={isApproved}
            className="flex-1 py-2 bg-green/20 border border-green text-green font-bold rounded-lg hover:bg-green/30 transition-colors text-xs disabled:opacity-40"
          >
            {isApproved ? '✓ Sudah Disetujui' : 'Setujui & Terbitkan ke CMMS'}
          </button>
          <button
            onClick={() => onAction && onAction('REVISE')}
            className="px-4 py-2 bg-panel2 border border-line text-muted font-bold rounded-lg hover:text-textMain transition-colors text-xs"
          >
            Minta Revisi
          </button>
        </div>
      </div>
    </div>
  );
}
