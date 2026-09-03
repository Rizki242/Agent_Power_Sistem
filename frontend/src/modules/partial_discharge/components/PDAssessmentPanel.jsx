import React from 'react';
import { StatusBadge } from '../../../components/common';

// React counterpart of src/components/agent_result.py's render_agent_result,
// fed by GET /api/pd/samples/{id}/assessment (which runs PDAgent server-side).
// Nothing is scored here - this only presents what the agent returned.
const SEVERITY_STYLES = {
  4: 'border-red/40 bg-red/10 text-red',
  3: 'border-amber/40 bg-amber/10 text-amber',
  2: 'border-yellow-400/40 bg-yellow-400/10 text-yellow-400',
  1: 'border-green/40 bg-green/10 text-green',
};

const METRIC_LABELS = {
  pulse_magnitude_pc: 'Pulse Magnitude (pC)',
  nqn: 'NQN',
  pd_type: 'Tipe Discharge',
  phase_clustering_deg: 'Phase Clustering (deg)',
};

export default function PDAssessmentPanel({ assessment, loading }) {
  if (loading) {
    return <div className="py-8 text-center text-muted text-xs">Menjalankan analisa PD Agent...</div>;
  }
  if (!assessment) {
    return <div className="py-8 text-center text-muted text-xs">Analisa belum tersedia untuk sampel ini.</div>;
  }

  const severity = Number(assessment.severity ?? 1);
  const severityClass = SEVERITY_STYLES[severity] || SEVERITY_STYLES[1];
  const evidence = assessment.evidence || [];
  const recommendations = assessment.recommendation || [];
  const metrics = assessment.metrics || {};

  return (
    <div className="flex flex-col gap-4">
      {/* Verdict */}
      <div className={`border rounded-xl px-3.5 py-3 ${severityClass}`}>
        <div className="text-[10px] uppercase tracking-wider font-bold opacity-80">
          Severity {severity} · {assessment.domain}
        </div>
        <div className="text-sm font-bold mt-0.5">{assessment.failure_mode || '-'}</div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-3 gap-2.5">
        <div className="border border-line rounded-xl bg-panel p-3">
          <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1">Kondisi</div>
          <StatusBadge status={assessment.condition} />
        </div>
        <div className="border border-line rounded-xl bg-panel p-3">
          <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1">Health Score</div>
          <div className="text-base font-bold font-mono text-cyan">{assessment.health_score ?? '-'}</div>
        </div>
        <div className="border border-line rounded-xl bg-panel p-3">
          <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1">Confidence</div>
          <div className="text-base font-bold font-mono text-textMain">
            {assessment.confidence != null ? `${Math.round(assessment.confidence * 100)}%` : '-'}
          </div>
        </div>
      </div>

      {/* Evidence */}
      <div>
        <div className="text-[10px] text-muted uppercase tracking-wider font-bold mb-1.5">Bukti Teknis</div>
        {evidence.length > 0 ? (
          <ul className="flex flex-col gap-1.5 m-0 pl-4">
            {evidence.map((e, i) => (
              <li key={i} className="text-xs text-textMain leading-relaxed">{e}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted m-0">Tidak ada indikasi anomali yang tercatat.</p>
        )}
      </div>

      {/* Recommendations */}
      <div>
        <div className="text-[10px] text-muted uppercase tracking-wider font-bold mb-1.5">Rekomendasi Tindak Lanjut</div>
        <ul className="flex flex-col gap-1.5 m-0 pl-4">
          {recommendations.map((r, i) => (
            <li key={i} className="text-xs text-textMain leading-relaxed">{r}</li>
          ))}
        </ul>
      </div>

      {/* Metrics used */}
      {Object.keys(metrics).length > 0 && (
        <div className="overflow-x-auto border border-line rounded-xl bg-panel">
          <table className="w-full text-left text-xs">
            <thead className="bg-panel2 text-muted border-b border-line">
              <tr>
                <th className="p-2.5">Parameter</th>
                <th className="p-2.5">Nilai</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/40 font-mono">
              {Object.entries(metrics).map(([key, value]) => (
                <tr key={key} className="hover:bg-panel2">
                  <td className="p-2.5 text-muted">{METRIC_LABELS[key] || key}</td>
                  <td className="p-2.5 text-textMain">{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
