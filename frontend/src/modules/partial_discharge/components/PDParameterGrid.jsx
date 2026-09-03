import React from 'react';

// Mirrors the "Ringkasan" view of src/pages/pd_page.py: the raw PRPD fields,
// shown as-is. No thresholds are re-derived here - the sample's status comes
// from the API, which uses pd_data._pd_status.
export default function PDParameterGrid({ sampleDetail }) {
  if (!sampleDetail) return null;

  const params = [
    { label: 'Pulse Magnitude', value: sampleDetail.pulse_magnitude_pc, unit: 'pC', accent: 'text-cyan' },
    { label: 'NQN', value: sampleDetail.nqn, unit: '', accent: 'text-cyan' },
    { label: 'Tipe Discharge', value: sampleDetail.pd_type, unit: '', accent: 'text-textMain' },
    { label: 'Phase Clustering', value: sampleDetail.phase_clustering_deg, unit: '°', accent: 'text-textMain' },
    { label: 'Metode Uji', value: sampleDetail.method, unit: '', accent: 'text-textMain' },
    { label: 'Tanggal Uji', value: sampleDetail.test_date, unit: '', accent: 'text-textMain' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-2.5">
      {params.map((p) => (
        <div key={p.label} className="border border-line rounded-xl bg-panel p-3">
          <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1">{p.label}</div>
          <div className={`text-base font-bold font-mono ${p.accent}`}>
            {p.value ?? '-'}{p.value != null && p.unit ? ` ${p.unit}` : ''}
          </div>
        </div>
      ))}
    </div>
  );
}
