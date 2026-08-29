import React, { useState, useEffect, useCallback } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { StatusBadge, FilterBar, TabNavigation } from '../components/common';
import {
  TribologySummaryCards,
  OilPropertiesGrid,
  WearDebrisPanel,
  OilConditionCalculator
} from '../components/tribology';
import { apiUrl } from '../api';

export default function TribologyWorkspace() {
  // --- Oil Samples List State ---
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [oilTypeFilter, setOilTypeFilter] = useState('ALL');
  const [summary, setSummary] = useState(null);

  // --- Sample Detail State ---
  const [selectedSampleId, setSelectedSampleId] = useState(null);
  const [sampleDetail, setSampleDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('params'); // 'params' | 'wear' | 'history' | 'evaluator'

  const loadSampleDetail = useCallback((id) => {
    setSelectedSampleId(id);
    setLoadingDetail(true);
    fetch(apiUrl(`/api/tribology/samples/${encodeURIComponent(id)}`))
      .then(res => res.json())
      .then(data => {
        setSampleDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Gagal memuat detail sample:', err);
        setLoadingDetail(false);
      });
  }, []);

  // --- Fetch Samples ---
  const fetchSamples = useCallback(() => {
    setLoading(true);
    let url = apiUrl('/api/tribology/samples?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (oilTypeFilter !== 'ALL') url += `oil_type=${encodeURIComponent(oilTypeFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setSamples(data.samples || []);
        setLoading(false);
        if (!selectedSampleId && data.samples && data.samples.length > 0) {
          loadSampleDetail(data.samples[0].sample_id);
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data tribology samples:', err);
        setLoading(false);
      });
  }, [unitFilter, statusFilter, oilTypeFilter, search, selectedSampleId, loadSampleDetail]);

  // --- Fetch Summary ---
  useEffect(() => {
    fetch(apiUrl('/api/tribology/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchSamples();
  }, [fetchSamples]);

  const tribTabs = [
    { id: 'params', label: 'Sifat Fisikokimia (ASTM)', icon: '🧪' },
    { id: 'wear', label: 'Logam Keausan (ppm)', icon: '⚙️' },
    { id: 'history', label: 'Riwayat Uji', icon: '📈' },
    { id: 'evaluator', label: 'Simulator Pelumas', icon: '🎛️' }
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-amber font-bold">Lubrication &amp; Wear Analysis</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Tribology &amp; Oil Diagnostics Workspace</h2>
        </div>
        <div className="text-xs text-muted">ASTM D445 · ASTM D664 · ISO 4406 · ICP-AES Wear</div>
      </div>

      {/* Summary Cards */}
      <TribologySummaryCards summary={summary} />

      {/* Main Layout */}
      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column: Filter + List + Detail */}
        <div className="flex flex-col gap-4">
          {/* Reusable Filter Bar */}
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            onSearchSubmit={fetchSamples}
            searchPlaceholder="Cari Peralatan / Sampel Pelumas..."
            unitFilter={unitFilter}
            onUnitChange={setUnitFilter}
            unitOptions={['ALL', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON']}
            statusFilter={statusFilter}
            onStatusChange={setStatusFilter}
            statusOptions={['ALL', 'NORMAL', 'PREWARNING', 'WARNING', 'CRITICAL']}
            accentColor="amber"
          />

          {/* Sample Table */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs text-muted">Menampilkan <strong className="text-textMain">{samples.length}</strong> titik sampel pelumas</span>
            </div>

            <div className="overflow-x-auto max-h-[280px] overflow-y-auto pr-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-panel border-b border-line z-10">
                  <tr className="text-muted">
                    <th className="py-2.5 px-3 font-semibold">Equipment</th>
                    <th className="py-2.5 px-3 font-semibold">Unit</th>
                    <th className="py-2.5 px-3 font-semibold">Tipe Oli</th>
                    <th className="py-2.5 px-3 font-semibold">Visc @40°C</th>
                    <th className="py-2.5 px-3 font-semibold">Water ppm</th>
                    <th className="py-2.5 px-3 font-semibold">Status</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {loading ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Memuat data sampel pelumas...</td>
                    </tr>
                  ) : samples.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Tidak ada data sampel yang sesuai filter.</td>
                    </tr>
                  ) : (
                    samples.map((s, idx) => (
                      <tr
                        key={idx}
                        className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedSampleId === s.sample_id ? 'bg-panel2 border-l-2 border-l-amber font-medium' : ''}`}
                        onClick={() => loadSampleDetail(s.sample_id)}
                      >
                        <td className="py-2.5 px-3 font-bold text-textMain">{s.equipment}</td>
                        <td className="py-2.5 px-3 text-muted">{s.unit}</td>
                        <td className="py-2.5 px-3 text-muted font-mono">{s.oil_type}</td>
                        <td className="py-2.5 px-3 font-mono text-cyan font-bold">{s.viscosity_40 || '-'} cSt</td>
                        <td className="py-2.5 px-3 font-mono text-textMain">{s.water_ppm || '-'}</td>
                        <td className="py-2.5 px-3"><StatusBadge status={s.status} /></td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={(e) => { e.stopPropagation(); loadSampleDetail(s.sample_id); }}
                            className="px-2.5 py-1 rounded bg-panel border border-line text-amber hover:border-amber text-[11px]"
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

          {/* Sample Detail Card */}
          {selectedSampleId && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 pb-3 border-b border-line">
                <div>
                  <span className="text-[10px] text-amber uppercase tracking-wider font-bold">Hasil Uji Laboratorium Pelumas</span>
                  <h3 className="text-lg font-bold text-textMain mt-0.5">
                    {sampleDetail?.equipment || selectedSampleId}
                    <span className="text-xs text-muted font-normal ml-2">({sampleDetail?.unit} · {sampleDetail?.oil_type})</span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <TabNavigation
                    tabs={tribTabs}
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                    accentColor="amber"
                  />
                  <StatusBadge status={sampleDetail?.status} size="lg" />
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-muted text-xs">Memuat detail spektrometri oli...</div>
              ) : sampleDetail ? (
                <div className="flex flex-col gap-4">
                  {/* TAB 1: Physicochemical Parameters */}
                  {activeTab === 'params' && (
                    <OilPropertiesGrid sampleDetail={sampleDetail} />
                  )}

                  {/* TAB 2: Wear Metals */}
                  {activeTab === 'wear' && (
                    <WearDebrisPanel sampleDetail={sampleDetail} />
                  )}

                  {/* TAB 3: History */}
                  {activeTab === 'history' && (
                    <div className="overflow-x-auto border border-line rounded-xl bg-panel">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-panel2 text-muted border-b border-line">
                          <tr>
                            <th className="p-2.5">Tanggal</th>
                            <th className="p-2.5">Viskositas (cSt)</th>
                            <th className="p-2.5">TAN (mgKOH/g)</th>
                            <th className="p-2.5">Water (ppm)</th>
                            <th className="p-2.5">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-line/40 font-mono">
                          {sampleDetail.history && sampleDetail.history.length > 0 ? (
                            sampleDetail.history.map((h, hIdx) => (
                              <tr key={hIdx} className="hover:bg-panel2">
                                <td className="p-2.5 text-textMain">{h.date}</td>
                                <td className="p-2.5 text-cyan font-bold">{h.viscosity_40}</td>
                                <td className="p-2.5 text-textMain">{h.tan}</td>
                                <td className="p-2.5 text-amber">{h.water_ppm} ppm</td>
                                <td className="p-2.5"><StatusBadge status={h.status} size="xs" /></td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="5" className="p-4 text-center text-muted">Belum ada riwayat uji periodik tercatat.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* TAB 4: Evaluator */}
                  {activeTab === 'evaluator' && (
                    <OilConditionCalculator />
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel defaultPrompt={sampleDetail ? `Bagaimana evaluasi tribologi dan kondisi oli untuk peralatan ${sampleDetail.equipment}? Jelaskan viskositas, TAN, dan partikel keausan.` : undefined} />
        </div>
      </section>
    </div>
  );
}
