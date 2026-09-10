import React, { useEffect, useState } from 'react';
import { StatusBadge, LoadingSpinner, EmptyState } from '../components/common';
import { apiFetch, apiUrl } from '../api';

const STATUS_DISPLAY = {
  ACTIVE: 'NORMAL',
  DISABLED: 'STANDBY',
  ERROR: 'CRITICAL',
  INCOMPATIBLE: 'WARNING',
};

export default function EngineeringModules() {
  const [modules, setModules] = useState([]);
  const [loadReport, setLoadReport] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([
      apiFetch(apiUrl('/api/v2/modules')).then(res => res.json()),
      apiFetch(apiUrl('/api/v2/module-load-report')).then(res => res.json()),
    ])
      .then(([modulesData, reportData]) => {
        setModules(modulesData.modules || []);
        setLoadReport(reportData.results || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Gagal mengambil daftar engineering module:', err);
        setError(true);
        setLoading(false);
      });
  }, []);

  const statusByModuleId = Object.fromEntries(loadReport.map(r => [r.module_id, r]));

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-bold text-textMain">Engineering Modules</h2>
        <p className="text-xs text-muted mt-1 max-w-2xl">
          Daftar module diagnostik yang dimuat secara dinamis dari manifest (<code className="text-cyan">/api/v2/modules</code>),
          bukan hard-code di frontend. Status pemuatan tiap module (ACTIVE/DISABLED/ERROR/INCOMPATIBLE) diambil dari manifest scan backend.
        </p>
      </div>

      {loading && <LoadingSpinner message="Memuat daftar engineering module..." />}

      {!loading && error && (
        <EmptyState icon="⚠️" title="Gagal memuat module" description="Tidak dapat menghubungi /api/v2/modules. Pastikan backend FastAPI berjalan." />
      )}

      {!loading && !error && modules.length === 0 && (
        <EmptyState icon="🧩" title="Belum ada module terdaftar" description="Tidak ada engineering module yang aktif saat ini." />
      )}

      {!loading && !error && modules.length > 0 && (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {modules.map(module => {
            const report = statusByModuleId[module.id];
            const status = report?.status || 'ACTIVE';
            return (
              <div key={module.id} className="p-4 border border-line rounded-xl bg-panel flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-textMain">{module.name}</h3>
                    <p className="text-[11px] text-muted font-mono mt-0.5">{module.id} · v{module.version}</p>
                  </div>
                  <StatusBadge status={STATUS_DISPLAY[status] || status} size="xs" />
                </div>

                <div>
                  <div className="text-[10px] text-muted uppercase tracking-[0.12em] font-bold mb-1.5">Applicable Equipment</div>
                  <div className="flex flex-wrap gap-1.5">
                    {module.applicable_equipment.length === 0 && (
                      <span className="text-[10px] text-muted">Semua tipe equipment</span>
                    )}
                    {module.applicable_equipment.map(eq => (
                      <span key={eq} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-panel2 border border-line text-muted">
                        {eq}
                      </span>
                    ))}
                  </div>
                </div>

                {report?.detail && (
                  <p className="text-[10px] text-muted italic">{report.detail}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
