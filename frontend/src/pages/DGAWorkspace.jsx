import React, { useState, useEffect, useCallback } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { StatusBadge, FilterBar, TabNavigation } from '../components/common';
import { DGASummaryCards, DGAGasTable, DuvalTriangleVisualizer, DGACalculator } from '../components/dga';
import { apiUrl } from '../api';

export default function DGAWorkspace() {
  // --- Transformers List State ---
  const [transformers, setTransformers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [summary, setSummary] = useState(null);

  // --- Transformer Detail State ---
  const [selectedId, setSelectedId] = useState(null);
  const [trfDetail, setTrfDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('gases'); // 'gases' | 'duval' | 'history' | 'simulator'

  // --- Upload / Manual Simulator State ---
  const [file, setFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  const loadTransformerDetail = useCallback((id) => {
    setSelectedId(id);
    setLoadingDetail(true);
    fetch(apiUrl(`/api/dga/transformers/${encodeURIComponent(id)}`))
      .then(res => res.json())
      .then(data => {
        setTrfDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Gagal memuat detail trafo:', err);
        setLoadingDetail(false);
      });
  }, []);

  // --- Fetch Transformers ---
  const fetchTransformers = useCallback(() => {
    setLoading(true);
    let url = apiUrl('/api/dga/transformers?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setTransformers(data.transformers || []);
        setLoading(false);
        if (!selectedId && data.transformers && data.transformers.length > 0) {
          loadTransformerDetail(data.transformers[0].transformer_id);
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data trafo:', err);
        setLoading(false);
      });
  }, [unitFilter, statusFilter, search, selectedId, loadTransformerDetail]);

  // --- Fetch Summary ---
  useEffect(() => {
    fetch(apiUrl('/api/dga/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchTransformers();
  }, [fetchTransformers]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Pilih file Excel terlebih dahulu.");
      return;
    }
    setUploadLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(apiUrl('/api/upload/dga'), {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === 'success') {
        alert("File DGA berhasil diproses.");
        fetchTransformers();
      } else {
        alert("Gagal memproses file DGA.");
      }
    } catch (err) {
      console.error(err);
      alert("Terjadi kesalahan jaringan.");
    } finally {
      setUploadLoading(false);
    }
  };

  const dgaTabs = [
    { id: 'gases', label: 'Konsentrasi Gas (ppm)', icon: '🧪' },
    { id: 'duval', label: 'Duval Triangle', icon: '🔺' },
    { id: 'history', label: 'Riwayat Uji', icon: '📈' },
    { id: 'simulator', label: 'Simulator DGA', icon: '⚡' }
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-cyan font-bold">Transformer Oil Diagnostics</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Dissolved Gas Analysis (DGA) Workspace</h2>
        </div>
        <div className="flex items-center gap-2">
          <form onSubmit={handleUpload} className="flex items-center gap-2">
            <input 
              type="file" 
              accept=".xlsx,.xls"
              onChange={(e) => setFile(e.target.files[0])}
              className="text-xs text-muted file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:bg-panel2 file:text-cyan hover:file:bg-panel cursor-pointer"
            />
            <button 
              type="submit" 
              disabled={uploadLoading}
              className="px-3 py-1.5 rounded-lg border border-cyan bg-cyan/10 text-cyan text-xs font-bold hover:bg-cyan/20 transition-colors disabled:opacity-50"
            >
              {uploadLoading ? 'Uploading...' : 'Upload Excel DGA'}
            </button>
          </form>
        </div>
      </div>

      {/* Summary Cards */}
      <DGASummaryCards summary={summary} />

      {/* Main Layout */}
      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column: Filter + List + Detail */}
        <div className="flex flex-col gap-4">
          {/* Reusable Filter Bar */}
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            onSearchSubmit={fetchTransformers}
            searchPlaceholder="Cari Trafo (mis. GSU 1, UAT 2, Trafo Bantu)..."
            unitFilter={unitFilter}
            onUnitChange={setUnitFilter}
            unitOptions={['ALL', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON']}
            statusFilter={statusFilter}
            onStatusChange={setStatusFilter}
            statusOptions={['ALL', 'Condition 1', 'Condition 2', 'Condition 3', 'Condition 4']}
          />

          {/* Transformer Table */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs text-muted">Menampilkan <strong className="text-textMain">{transformers.length}</strong> unit transformator</span>
            </div>

            <div className="overflow-x-auto max-h-[280px] overflow-y-auto pr-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-panel border-b border-line z-10">
                  <tr className="text-muted">
                    <th className="py-2.5 px-3 font-semibold">Nama Trafo</th>
                    <th className="py-2.5 px-3 font-semibold">Unit</th>
                    <th className="py-2.5 px-3 font-semibold">TDCG</th>
                    <th className="py-2.5 px-3 font-semibold">IEEE Condition</th>
                    <th className="py-2.5 px-3 font-semibold">Duval Fault</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {loading ? (
                    <tr>
                      <td colSpan="6" className="py-8 text-center text-muted">Memuat data transformator...</td>
                    </tr>
                  ) : transformers.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="py-8 text-center text-muted">Tidak ada data trafo yang sesuai filter.</td>
                    </tr>
                  ) : (
                    transformers.map((trf, idx) => (
                      <tr 
                        key={idx}
                        className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedId === trf.transformer_id ? 'bg-panel2 border-l-2 border-l-cyan font-medium' : ''}`}
                        onClick={() => loadTransformerDetail(trf.transformer_id)}
                      >
                        <td className="py-2.5 px-3 font-bold text-textMain">{trf.name || trf.equipment}</td>
                        <td className="py-2.5 px-3 text-muted">{trf.unit}</td>
                        <td className="py-2.5 px-3 font-mono font-bold text-cyan">{trf.tdcg !== undefined ? `${trf.tdcg} ppm` : '-'}</td>
                        <td className="py-2.5 px-3"><StatusBadge status={trf.ieee_condition || trf.status} /></td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-muted">{trf.duval_diagnosis || '-'}</td>
                        <td className="py-2.5 px-3 text-right">
                          <button 
                            onClick={(e) => { e.stopPropagation(); loadTransformerDetail(trf.transformer_id); }}
                            className="px-2.5 py-1 rounded bg-panel border border-line text-cyan hover:border-cyan text-[11px]"
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

          {/* Transformer Detail Card */}
          {selectedId && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 pb-3 border-b border-line">
                <div>
                  <span className="text-[10px] text-cyan uppercase tracking-wider font-bold">Diagnosa Gas Terlarut &amp; Duval Triangle</span>
                  <h3 className="text-lg font-bold text-textMain mt-0.5">
                    {trfDetail?.name || trfDetail?.equipment || selectedId}
                    <span className="text-xs text-muted font-normal ml-2">({trfDetail?.unit} · {trfDetail?.capacity || '30 MVA'})</span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <TabNavigation
                    tabs={dgaTabs}
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                    accentColor="cyan"
                  />
                  <StatusBadge status={trfDetail?.ieee_condition || trfDetail?.status} size="lg" />
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-muted text-xs">Memuat detail spektroskopi gas trafo...</div>
              ) : trfDetail ? (
                <div className="flex flex-col gap-4">
                  {/* TAB 1: Gas Concentrations */}
                  {activeTab === 'gases' && (
                    <DGAGasTable trfDetail={trfDetail} />
                  )}

                  {/* TAB 2: Duval Triangle */}
                  {activeTab === 'duval' && (
                    <DuvalTriangleVisualizer
                      pctCh4={trfDetail.pct_ch4 || 26.6}
                      pctC2h4={trfDetail.pct_c2h4 || 69.1}
                      pctC2h2={trfDetail.pct_c2h2 || 4.3}
                      diagnosis={trfDetail.duval_diagnosis || 'T3 (Thermal Fault T > 700°C)'}
                    />
                  )}

                  {/* TAB 3: History */}
                  {activeTab === 'history' && (
                    <div className="overflow-x-auto border border-line rounded-xl bg-panel">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-panel2 text-muted border-b border-line">
                          <tr>
                            <th className="p-2.5">Tanggal</th>
                            <th className="p-2.5">TDCG (ppm)</th>
                            <th className="p-2.5">Kondisi IEEE</th>
                            <th className="p-2.5">Duval Fault</th>
                            <th className="p-2.5">Laju Gas (ppm/hari)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-line/40 font-mono">
                          {trfDetail.history && trfDetail.history.length > 0 ? (
                            trfDetail.history.map((h, hIdx) => (
                              <tr key={hIdx} className="hover:bg-panel2">
                                <td className="p-2.5 text-textMain">{h.date}</td>
                                <td className="p-2.5 font-bold text-cyan">{h.tdcg} ppm</td>
                                <td className="p-2.5"><StatusBadge status={h.ieee_condition} size="xs" /></td>
                                <td className="p-2.5 text-muted">{h.duval_diagnosis}</td>
                                <td className="p-2.5 text-textMain">{h.rate_ppm_day || '< 5'}</td>
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

                  {/* TAB 4: Simulator */}
                  {activeTab === 'simulator' && (
                    <DGACalculator />
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel defaultPrompt={trfDetail ? `Bagaimana analisis DGA untuk transformator ${trfDetail.name || trfDetail.equipment}? Jelaskan evaluasi Duval Triangle dan kondisi IEEE C57.104.` : undefined} />
        </div>
      </section>
    </div>
  );
}
