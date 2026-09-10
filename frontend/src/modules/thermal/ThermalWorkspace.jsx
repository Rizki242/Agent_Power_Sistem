import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AIChatPanel from '../../components/AIChatPanel';
import { StatusBadge, FilterBar, ErrorState } from '../../components/common';
import {
  ThermalSummaryCards,
  ThermalDetailCard,
  ThermalSeverityMatrix
} from './components';
import { apiFetch, apiUrl, parseApiError } from '../../api';

// Selected inspection point is driven by the route
// (/workspace/thermal/:equipmentId), same redesign as MCSAWorkspace
// (desaindakhir.md / docs/final.md Phase 25). Unlike the other domains
// there's no per-id detail endpoint here - the list response already has
// everything, so selection is just finding the matching row (matches
// services/assetTree.js, which keys thermal leaves on `id` falling back to
// `equipment`).
export default function ThermalWorkspace() {
  const { equipmentId } = useParams();
  const navigate = useNavigate();
  const selectedId = equipmentId ? decodeURIComponent(equipmentId) : null;

  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [summary, setSummary] = useState(null);

  const selectedPoint = useMemo(
    () => inspections.find((p) => (p.id || p.equipment) === selectedId) || null,
    [inspections, selectedId]
  );

  // Navigating (not just setting local state) keeps the sidebar tree's
  // NavLink highlighting and the breadcrumb in sync with selection.
  const goToPoint = useCallback((p, opts) => {
    navigate(`/workspace/thermal/${encodeURIComponent(p.id || p.equipment)}`, opts);
  }, [navigate]);

  const fetchInspections = useCallback(() => {
    setLoading(true);
    setListError(null);
    let url = apiUrl('/api/thermal/inspections?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    apiFetch(url)
      .then(async res => {
        if (!res.ok) {
          const parsed = await parseApiError(res, 'Gagal memuat data thermography');
          throw parsed;
        }
        return res.json();
      })
      .then(data => {
        setInspections(data.inspections || []);
        setLoading(false);
        if (!selectedId && data.inspections && data.inspections.length > 0) {
          goToPoint(data.inspections[0], { replace: true });
        }
      })
      .catch(err => {
        console.error('Gagal memuat data thermography:', err);
        setListError({
          message: err.message || 'Gagal memuat data thermography',
          correlationId: err.correlationId || null
        });
        setLoading(false);
      });
  }, [unitFilter, statusFilter, search, selectedId, goToPoint]);

  useEffect(() => {
    apiFetch(apiUrl('/api/thermal/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchInspections();
  }, [fetchInspections]);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-orange-400 font-bold">Infrared Thermography Diagnostics</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Thermal &amp; Hotspot Monitoring Workspace</h2>
        </div>
        <div className="text-xs text-muted">FLIR IRT Matrix · NETA MTS · Delta-T Standards</div>
      </div>

      {/* Summary Cards */}
      <ThermalSummaryCards summary={summary} />

      {/* Main Workspace Layout */}
      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column */}
        <div className="flex flex-col gap-4">
          {/* Reusable Filter Bar */}
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            onSearchSubmit={fetchInspections}
            searchPlaceholder="Cari Titik Thermal / KKS (mis. CWP, BFP, IDF, PAC)..."
            unitFilter={unitFilter}
            onUnitChange={setUnitFilter}
            unitOptions={['ALL', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON']}
            statusFilter={statusFilter}
            onStatusChange={setStatusFilter}
            statusOptions={['ALL', 'NORMAL', 'PREWARNING', 'WARNING', 'CRITICAL', 'STANDBY']}
            accentColor="orange"
          />

          {/* Inspection Points Table */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs text-muted">Menampilkan <strong className="text-textMain">{inspections.length}</strong> titik inspeksi termal</span>
            </div>

            <div className="overflow-x-auto max-h-[300px] overflow-y-auto pr-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-panel border-b border-line z-10">
                  <tr className="text-muted">
                    <th className="py-2.5 px-3 font-semibold">Equipment / KKS</th>
                    <th className="py-2.5 px-3 font-semibold">Unit</th>
                    <th className="py-2.5 px-3 font-semibold">Titik Inspeksi</th>
                    <th className="py-2.5 px-3 font-semibold">T Max (°C)</th>
                    <th className="py-2.5 px-3 font-semibold">Delta-T (ΔT)</th>
                    <th className="py-2.5 px-3 font-semibold">Status</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {loading ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Memuat data inspeksi thermography...</td>
                    </tr>
                  ) : listError ? (
                    <tr>
                      <td colSpan="7" className="p-4">
                        <ErrorState
                          title="Gagal Mengambil Data Thermography"
                          message={listError.message}
                          correlationId={listError.correlationId}
                          onRetry={fetchInspections}
                        />
                      </td>
                    </tr>
                  ) : inspections.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Tidak ada data thermography yang cocok dengan filter.</td>
                    </tr>
                  ) : (
                    inspections.map((p, idx) => (
                      <tr 
                        key={idx}
                        className={`hover:bg-panel2/60 transition-colors cursor-pointer ${(p.id || p.equipment) === selectedId ? 'bg-panel2 border-l-2 border-l-orange-400 font-medium' : ''}`}
                        onClick={() => goToPoint(p)}
                      >
                        <td className="py-2.5 px-3 font-bold text-textMain">{p.equipment}</td>
                        <td className="py-2.5 px-3 text-muted">{p.unit}</td>
                        <td className="py-2.5 px-3 text-muted font-mono">{p.point_name}</td>
                        <td className="py-2.5 px-3 font-mono font-bold text-textMain">{p.t_max !== undefined ? `${p.t_max}°C` : '-'}</td>
                        <td className="py-2.5 px-3 font-mono font-bold text-orange-400">{p.delta_t !== undefined ? `${p.delta_t}°C` : '-'}</td>
                        <td className="py-2.5 px-3"><StatusBadge status={p.status} /></td>
                        <td className="py-2.5 px-3 text-right">
                          <button 
                            onClick={(e) => { e.stopPropagation(); goToPoint(p); }}
                            className="px-2.5 py-1 rounded bg-panel border border-line text-orange-400 hover:border-orange-400 text-[11px]"
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

          {/* Selected Point Detail Card */}
          <ThermalDetailCard point={selectedPoint} />

          {/* Delta-T Severity Standard Matrix */}
          <ThermalSeverityMatrix />
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel defaultPrompt={selectedPoint ? `Bagaimana evaluasi thermography inframerah untuk titik ${selectedPoint.equipment} - ${selectedPoint.point_name}? Jelaskan arti Delta-T ${selectedPoint.delta_t}°C menurut NETA MTS.` : undefined} />
        </div>
      </section>
    </div>
  );
}
