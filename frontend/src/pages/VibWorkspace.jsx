import React, { useState, useEffect, useCallback } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { apiUrl } from '../api';

export default function VibWorkspace() {
  // --- View Mode: Asset Database vs Periodic Measurements ---
  const [dataView, setDataView] = useState('tests'); // 'tests' | 'assets'

  // --- Tests list state ---
  const [testsList, setTestsList] = useState([]);
  const [loadingTests, setLoadingTests] = useState(true);

  // --- Asset list state ---
  const [equipmentList, setEquipmentList] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- Shared filters ---
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [summary, setSummary] = useState(null);

  // --- Detail state ---
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [selectedTest, setSelectedTest] = useState(null);
  const [eqDetail, setEqDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('points'); // 'points' | 'specs' | 'evaluator'

  // --- Quick Evaluator state ---
  const [eqName, setEqName] = useState('Motor BFP 1A');
  const [vibVelocity, setVibVelocity] = useState(3.4);
  const [vibAcc, setVibAcc] = useState(1.2);
  const [vibGroup, setVibGroup] = useState('Group 1 (Rigid)');
  const [evalResult, setEvalResult] = useState(null);

  // --- Fetch Periodic Tests ---
  const fetchTests = useCallback(() => {
    setLoadingTests(true);
    let url = apiUrl('/api/vibration/tests?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setTestsList(data.tests || []);
        setLoadingTests(false);
        if (data.tests && data.tests.length > 0 && !selectedTest) {
          setSelectedTest(data.tests[0]);
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data pengujian vibrasi:', err);
        setLoadingTests(false);
      });
  }, [unitFilter, statusFilter, search, selectedTest]);

  const loadEquipmentDetail = useCallback((assetId) => {
    setSelectedAssetId(assetId);
    setLoadingDetail(true);
    fetch(apiUrl(`/api/vibration/equipment/${encodeURIComponent(assetId)}`))
      .then(res => res.json())
      .then(data => {
        setEqDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Gagal memuat detail equipment:', err);
        setLoadingDetail(false);
      });
  }, []);

  // --- Fetch Asset Database ---
  const fetchEquipment = useCallback(() => {
    setLoading(true);
    let url = apiUrl('/api/vibration/equipment?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setEquipmentList(data.equipment || []);
        setLoading(false);
        if (!selectedAssetId && data.equipment && data.equipment.length > 0) {
          loadEquipmentDetail(data.equipment[0].asset_id);
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data vibration assets:', err);
        setLoading(false);
      });
  }, [unitFilter, statusFilter, search, selectedAssetId, loadEquipmentDetail]);

  // --- Fetch summary ---
  useEffect(() => {
    fetch(apiUrl('/api/vibration/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (dataView === 'tests') {
      fetchTests();
    } else {
      fetchEquipment();
    }
  }, [dataView, fetchTests, fetchEquipment]);

  const handleSelectTest = (test) => {
    setSelectedTest(test);
    // Auto lookup matching asset if any
    const matched = equipmentList.find(e => 
      e.equipment.toLowerCase().includes(test.equipment.toLowerCase()) || 
      test.equipment.toLowerCase().includes(e.equipment.toLowerCase())
    );
    if (matched) {
      loadEquipmentDetail(matched.asset_id);
    }
  };

  const handleEvaluate = (e) => {
    e.preventDefault();
    const v = parseFloat(vibVelocity);
    let zone = 'A';
    let condition = 'NORMAL';
    let color = 'text-green';
    let recommendation = 'Kondisi getaran prima (Zone A). Lanjutkan monitoring rutin.';

    if (v > 7.1) {
      zone = 'D';
      condition = 'CRITICAL';
      color = 'text-red';
      recommendation = 'Getaran sangat berbahaya (Zone D). Segera jadwalkan shutdown dan periksa unbalance / bearing!';
    } else if (v > 4.5) {
      zone = 'C';
      condition = 'ALARM';
      color = 'text-red';
      recommendation = 'Getaran di atas batas izin operasi kontinu (Zone C). Rencanakan tindakan korektif.';
    } else if (v > 2.8) {
      zone = 'B';
      condition = 'WARNING';
      color = 'text-amber';
      recommendation = 'Getaran dapat diterima untuk operasi jangka panjang (Zone B). Monitor tren getaran.';
    }

    setEvalResult({
      zone,
      condition,
      color,
      recommendation,
      velocity: v,
      acc: parseFloat(vibAcc),
      group: vibGroup
    });
  };

  const getStatusBadge = (status) => {
    const s = String(status || '').toUpperCase();
    if (s === 'NORMAL') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-green/10 text-green border border-green/30">NORMAL</span>;
    if (s === 'PREWARNING' || s === 'WARNING') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber/10 text-amber border border-amber/30">WARNING</span>;
    if (s === 'ALARM' || s === 'HIGH' || s === 'CRITICAL') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red/10 text-red border border-red/30 animate-pulse">ALARM</span>;
    if (s === 'STANDBY') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30">STANDBY</span>;
    return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-muted/10 text-muted border border-line">{status || 'UNKNOWN'}</span>;
  };

  // Active points to display: selectedTest points OR eqDetail points
  const activePoints = selectedTest?.points || eqDetail?.points || {};
  const activeVMax = selectedTest?.velocity_max ?? eqDetail?.velocity_max ?? 0.0;
  const activeStatus = selectedTest?.status || eqDetail?.status || 'NORMAL';
  const activeEqTitle = selectedTest?.equipment || eqDetail?.equipment || 'Pilih Peralatan';

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-blue font-black">Mechanical Vibration Diagnostics</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Vibration Analysis &amp; ISO 10816-3</h2>
        </div>
        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex rounded-xl border border-line p-0.5 bg-panel2 text-xs">
            <button
              onClick={() => setDataView('tests')}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold ${dataView === 'tests' ? 'bg-blue text-white shadow-neon' : 'text-muted hover:text-textMain'}`}
            >
              📋 Hasil Uji Berkala (99)
            </button>
            <button
              onClick={() => setDataView('assets')}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold ${dataView === 'assets' ? 'bg-blue text-white shadow-neon' : 'text-muted hover:text-textMain'}`}
            >
              🏷️ Master Asset (68)
            </button>
          </div>
        </div>
      </div>

      {/* KPI Overview Bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Total Monitored Drives</span>
            <strong className="text-xl text-textMain mt-1 block">{summary.total_assets || 68} Unit</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-green block uppercase tracking-wider font-bold">Zone A/B (Normal)</span>
            <strong className="text-xl text-green mt-1 block">{summary.by_status?.NORMAL || 58}</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-amber block uppercase tracking-wider font-bold">Zone C (Warning)</span>
            <strong className="text-xl text-amber mt-1 block">{summary.by_status?.WARNING || summary.by_status?.PREWARNING || 7}</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-red block uppercase tracking-wider font-bold">Zone D (Critical)</span>
            <strong className="text-xl text-red mt-1 block">{summary.by_status?.ALARM || summary.by_status?.HIGH || 3}</strong>
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <section className="grid lg:grid-cols-[1.55fr_0.95fr] gap-4">
        {/* Left Column: Tables & Measurement Detail */}
        <div className="flex flex-col gap-4">
          {/* Filters Bar */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-3.5 flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
            <input 
              type="text" 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari Equipment Vibrasi (mis. ID Fan 1#1, BFP 1A, CWP)..."
              className="bg-panel2 border border-line rounded-lg px-3 py-1.5 text-xs text-textMain outline-none focus:border-blue flex-1"
            />
            <div className="flex items-center gap-1.5">
              <select 
                value={unitFilter} 
                onChange={(e) => setUnitFilter(e.target.value)}
                className="bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-[11px] text-textMain outline-none focus:border-blue"
              >
                <option value="ALL">Semua Unit</option>
                <option value="UNIT 1">UNIT 1</option>
                <option value="UNIT 2">UNIT 2</option>
                <option value="UNIT 3">UNIT 3</option>
                <option value="UNIT COMMON">UNIT COMMON</option>
              </select>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-[11px] text-textMain outline-none focus:border-blue"
              >
                <option value="ALL">Semua Status</option>
                <option value="NORMAL">Normal</option>
                <option value="WARNING">Warning</option>
                <option value="ALARM">Alarm</option>
              </select>
            </div>
          </div>

          {/* TABLE VIEW 1: Periodic Monthly Vibration Tests */}
          {dataView === 'tests' && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
              <div className="flex justify-between items-center mb-2.5">
                <span className="text-xs text-muted font-bold uppercase tracking-wider">
                  Hasil Pengujian Getaran Berkala ({testsList.length} Pengujian)
                </span>
                <span className="text-[10px] text-blue">Klik baris untuk melihat titik sensor</span>
              </div>

              <div className="overflow-x-auto max-h-[260px] overflow-y-auto pr-1">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="sticky top-0 bg-panel border-b border-line z-10 text-muted">
                    <tr>
                      <th className="py-2 px-2.5">No</th>
                      <th className="py-2 px-2.5">Equipment</th>
                      <th className="py-2 px-2.5">Unit</th>
                      <th className="py-2 px-2.5">ISO Group</th>
                      <th className="py-2 px-2.5">V Max (mm/s)</th>
                      <th className="py-2 px-2.5">Titik 1H</th>
                      <th className="py-2 px-2.5">Titik 2H</th>
                      <th className="py-2 px-2.5">Status</th>
                      <th className="py-2 px-2.5 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/60">
                    {loadingTests ? (
                      <tr>
                        <td colSpan="9" className="py-8 text-center text-muted">Memuat data pengujian vibrasi...</td>
                      </tr>
                    ) : testsList.length === 0 ? (
                      <tr>
                        <td colSpan="9" className="py-8 text-center text-muted">Tidak ada data pengujian yang cocok dengan filter.</td>
                      </tr>
                    ) : (
                      testsList.map((t, idx) => (
                        <tr
                          key={idx}
                          className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedTest?.equipment === t.equipment ? 'bg-panel2 border-l-2 border-l-blue font-medium' : ''}`}
                          onClick={() => handleSelectTest(t)}
                        >
                          <td className="py-2 px-2.5 text-muted">{t.no}</td>
                          <td className="py-2 px-2.5 font-bold text-textMain">{t.equipment}</td>
                          <td className="py-2 px-2.5 text-muted text-[11px]">{t.unit}</td>
                          <td className="py-2 px-2.5 text-muted text-[11px]">{t.iso_group}</td>
                          <td className={`py-2 px-2.5 font-mono font-bold ${t.velocity_max > 4.5 ? 'text-red' : (t.velocity_max > 2.8 ? 'text-amber' : 'text-textMain')}`}>
                            {t.velocity_max}
                          </td>
                          <td className="py-2 px-2.5 font-mono text-muted">{t.points?.['1H'] || '-'}</td>
                          <td className="py-2 px-2.5 font-mono text-muted">{t.points?.['2H'] || '-'}</td>
                          <td className="py-2 px-2.5">{getStatusBadge(t.status)}</td>
                          <td className="py-2 px-2.5 text-right">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleSelectTest(t); }}
                              className="px-2 py-0.5 rounded bg-panel border border-line text-blue hover:border-blue text-[10px]"
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
          )}

          {/* TABLE VIEW 2: Asset Master Database */}
          {dataView === 'assets' && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
              <div className="flex justify-between items-center mb-2.5">
                <span className="text-xs text-muted font-bold uppercase tracking-wider">
                  Master Asset Database ({equipmentList.length} Unit)
                </span>
                <span className="text-[10px] text-blue">Spesifikasi Motor, Pompa/Fan, &amp; Bearing</span>
              </div>

              <div className="overflow-x-auto max-h-[260px] overflow-y-auto pr-1">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="sticky top-0 bg-panel border-b border-line z-10 text-muted">
                    <tr>
                      <th className="py-2 px-2.5">Asset ID</th>
                      <th className="py-2 px-2.5">Equipment</th>
                      <th className="py-2 px-2.5">Unit</th>
                      <th className="py-2 px-2.5">Kategori</th>
                      <th className="py-2 px-2.5">Speed (RPM)</th>
                      <th className="py-2 px-2.5">Pondasi</th>
                      <th className="py-2 px-2.5">Status</th>
                      <th className="py-2 px-2.5 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/60">
                    {loading ? (
                      <tr>
                        <td colSpan="8" className="py-8 text-center text-muted">Memuat database Vibrasi...</td>
                      </tr>
                    ) : equipmentList.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="py-8 text-center text-muted">Tidak ada equipment yang cocok dengan filter.</td>
                      </tr>
                    ) : (
                      equipmentList.map((eq, idx) => (
                        <tr
                          key={idx}
                          className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedAssetId === eq.asset_id ? 'bg-panel2 border-l-2 border-l-blue font-medium' : ''}`}
                          onClick={() => loadEquipmentDetail(eq.asset_id)}
                        >
                          <td className="py-2 px-2.5 font-mono text-blue text-[11px]">{eq.asset_id}</td>
                          <td className="py-2 px-2.5 font-bold text-textMain">{eq.equipment}</td>
                          <td className="py-2 px-2.5 text-muted text-[11px]">{eq.unit}</td>
                          <td className="py-2 px-2.5 text-muted text-[11px]">{eq.category}</td>
                          <td className="py-2 px-2.5 text-muted font-mono text-[11px]">{eq.c1_speed || '-'}</td>
                          <td className="py-2 px-2.5 text-muted">{eq.c1_foundation || '-'}</td>
                          <td className="py-2 px-2.5">{getStatusBadge(eq.status)}</td>
                          <td className="py-2 px-2.5 text-right">
                            <button
                              onClick={(e) => { e.stopPropagation(); loadEquipmentDetail(eq.asset_id); }}
                              className="px-2 py-0.5 rounded bg-panel border border-line text-blue hover:border-blue text-[10px]"
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
          )}

          {/* Detailed Inspection Panel */}
          {(selectedTest || eqDetail) && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 pb-3 border-b border-line">
                <div>
                  <span className="text-[10px] text-blue uppercase tracking-wider font-bold">Hasil Pengukuran &amp; Titik Sensor Vibrasi</span>
                  <h3 className="text-lg font-bold text-textMain mt-0.5">
                    {activeEqTitle}
                    <span className="text-xs text-muted font-normal ml-2">
                      ({selectedTest?.unit || eqDetail?.unit} · {selectedTest?.iso_group || eqDetail?.equipment_class})
                    </span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-lg border border-line p-0.5 bg-panel2 text-xs">
                    <button
                      onClick={() => setActiveTab('points')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'points' ? 'bg-blue text-white font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Titik Sensor (18 Points)
                    </button>
                    <button
                      onClick={() => setActiveTab('specs')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'specs' ? 'bg-blue text-white font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Spesifikasi Mekanikal
                    </button>
                    <button
                      onClick={() => setActiveTab('evaluator')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'evaluator' ? 'bg-blue text-white font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Simulator ISO 10816
                    </button>
                  </div>
                  {getStatusBadge(activeStatus)}
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-muted text-xs">Memuat detail sensor vibrasi...</div>
              ) : (
                <div className="flex flex-col gap-4">
                  {/* TAB 1: Measurement Points (1V, 1H, 1A, etc.) */}
                  {activeTab === 'points' && (
                    <div className="flex flex-col gap-4">
                      {/* Vmax highlight cards */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                        <div className="bg-panel p-2.5 rounded-xl border border-line">
                          <span className="text-[10px] text-muted block">Velocity RMS Max</span>
                          <strong className={`text-lg mt-0.5 block font-mono ${activeVMax > 4.5 ? 'text-red' : (activeVMax > 2.8 ? 'text-amber' : 'text-green')}`}>
                            {activeVMax > 0 ? `${activeVMax} mm/s` : '-'}
                          </strong>
                        </div>
                        <div className="bg-panel p-2.5 rounded-xl border border-line">
                          <span className="text-[10px] text-muted block">Klasifikasi ISO 10816</span>
                          <strong className="text-xs text-textMain mt-0.5 block">
                            {activeVMax > 7.1 ? 'Zone D (Unacceptable)' : (activeVMax > 4.5 ? 'Zone C (Restricted)' : (activeVMax > 2.8 ? 'Zone B (Acceptable)' : 'Zone A (Good)'))}
                          </strong>
                        </div>
                        <div className="bg-panel p-2.5 rounded-xl border border-line">
                          <span className="text-[10px] text-muted block">Grup Pondasi</span>
                          <strong className="text-xs text-textMain mt-0.5 block">{selectedTest?.iso_group || eqDetail?.c1_foundation || 'GROUP 1 (Rigid)'}</strong>
                        </div>
                        <div className="bg-panel p-2.5 rounded-xl border border-line">
                          <span className="text-[10px] text-muted block">Tanggal Uji</span>
                          <strong className="text-xs text-textMain mt-0.5 block font-mono">{selectedTest?.test_date || eqDetail?.measurement_date || 'Januari 2026'}</strong>
                        </div>
                      </div>

                      {/* Sensor Points Grid (18 standard points) */}
                      <div>
                        <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2">
                          Nilai Pengukuran Seluruh Posisi Sensor (mm/s RMS Velocity)
                        </h4>
                        {activePoints && Object.keys(activePoints).length > 0 ? (
                          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                            {Object.entries(activePoints).map(([pos, val], pIdx) => {
                              const vNum = parseFloat(val);
                              return (
                                <div key={pIdx} className="bg-panel p-2.5 rounded-xl border border-line text-center">
                                  <span className="text-[10px] text-muted block font-bold">{pos}</span>
                                  <strong className={`text-sm block mt-1 font-mono ${vNum > 4.5 ? 'text-red font-bold' : (vNum > 2.8 ? 'text-amber font-bold' : 'text-textMain')}`}>
                                    {val}
                                  </strong>
                                  <span className="text-[9px] text-muted">mm/s</span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="p-4 bg-panel rounded-xl text-center text-xs text-muted">
                            Peralatan berstatus Standby atau pengukuran titik sensor tercatat pada logbook offline.
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 2: Specifications */}
                  {activeTab === 'specs' && (
                    <div className="flex flex-col gap-4">
                      {eqDetail ? (
                        <>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                            <div className="bg-panel p-2.5 rounded-xl border border-line">
                              <span className="text-[10px] text-muted block">Asset ID</span>
                              <strong className="text-sm text-blue mt-0.5 block font-mono">{eqDetail.asset_id}</strong>
                            </div>
                            <div className="bg-panel p-2.5 rounded-xl border border-line">
                              <span className="text-[10px] text-muted block">ISO Class</span>
                              <strong className="text-[11px] text-textMain mt-0.5 block">{eqDetail.equipment_class || '-'}</strong>
                            </div>
                            <div className="bg-panel p-2.5 rounded-xl border border-line">
                              <span className="text-[10px] text-muted block">PM Week</span>
                              <strong className="text-sm text-textMain mt-0.5 block">{eqDetail.pm_week || '-'}</strong>
                            </div>
                            <div className="bg-panel p-2.5 rounded-xl border border-line">
                              <span className="text-[10px] text-muted block">Pondasi</span>
                              <strong className="text-sm text-textMain mt-0.5 block">{eqDetail.c1_foundation || 'Rigid'}</strong>
                            </div>
                          </div>

                          {eqDetail.motor_specs && Object.keys(eqDetail.motor_specs).length > 0 && (
                            <div>
                              <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2">Motor — Spesifikasi</h4>
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                                {Object.entries(eqDetail.motor_specs).map(([param, value], pIdx) => (
                                  <div key={pIdx} className="bg-panel p-2.5 rounded-xl border border-line flex flex-col justify-between">
                                    <span className="text-[10px] text-muted block truncate" title={param}>{param}</span>
                                    <strong className="text-xs text-textMain mt-1 block truncate font-mono" title={value}>{value}</strong>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {eqDetail.driven_specs && Object.keys(eqDetail.driven_specs).length > 0 && (
                            <div>
                              <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2">Driven Equipment (Fan / Pompa)</h4>
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                                {Object.entries(eqDetail.driven_specs).map(([param, value], pIdx) => (
                                  <div key={pIdx} className="bg-panel p-2.5 rounded-xl border border-line flex flex-col justify-between">
                                    <span className="text-[10px] text-muted block truncate" title={param}>{param}</span>
                                    <strong className="text-xs text-textMain mt-1 block truncate font-mono" title={value}>{value}</strong>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {eqDetail.recommendation && (
                            <div className="bg-panel2 p-3.5 rounded-xl border border-line">
                              <h4 className="text-xs font-bold text-blue mb-1.5 flex items-center gap-1.5">
                                <span>🛠️</span> Evaluasi &amp; Rekomendasi Getaran
                              </h4>
                              <p className="text-xs text-textMain leading-relaxed">{eqDetail.recommendation}</p>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="p-4 text-center text-xs text-muted bg-panel rounded-xl">
                          Silakan klik tab "Master Asset" di atas dan pilih unit untuk melihat spesifikasi detail.
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 3: Simulator */}
                  {activeTab === 'evaluator' && (
                    <div className="flex flex-col gap-4">
                      <div className="p-4 bg-panel rounded-xl border border-line">
                        <h4 className="text-xs font-bold text-blue mb-3">Simulator Cepat Evaluasi Getaran ISO 10816-3</h4>
                        <form onSubmit={handleEvaluate} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
                          <div>
                            <label className="text-[10px] text-muted block mb-1">Nama Peralatan</label>
                            <input 
                              type="text" 
                              value={eqName} 
                              onChange={(e) => setEqName(e.target.value)} 
                              className="w-full bg-panel2 border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-blue"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-muted block mb-1">Velocity RMS (mm/s)</label>
                            <input 
                              type="number" 
                              step="0.01" 
                              value={vibVelocity} 
                              onChange={(e) => setVibVelocity(e.target.value)} 
                              className="w-full bg-panel2 border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-blue"
                              required
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-muted block mb-1">Grup Mesin ISO</label>
                            <select 
                              value={vibGroup} 
                              onChange={(e) => setVibGroup(e.target.value)}
                              className="w-full bg-panel2 border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-blue"
                            >
                              <option value="Group 1 (Rigid)">Group 1: Medium/Large (Rigid, &gt;300kW)</option>
                              <option value="Group 1 (Flexible)">Group 1: Medium/Large (Flexible)</option>
                              <option value="Group 2 (Rigid)">Group 2: Medium (Rigid, 15–300kW)</option>
                              <option value="Group 2 (Flexible)">Group 2: Medium (Flexible)</option>
                            </select>
                          </div>
                          <div>
                            <button 
                              type="submit" 
                              className="w-full py-2 bg-blue text-white font-bold rounded-lg hover:bg-blue/90 transition-colors text-xs"
                            >
                              Evaluasi ISO
                            </button>
                          </div>
                        </form>

                        {evalResult && (
                          <div className="mt-4 p-3.5 bg-panel2 rounded-xl border border-line flex flex-col gap-2">
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-bold text-textMain">Zona ISO: <strong>Zone {evalResult.zone}</strong></span>
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${evalResult.color}`}>
                                {evalResult.condition} ({evalResult.velocity} mm/s)
                              </span>
                            </div>
                            <p className="text-xs text-textMain">{evalResult.recommendation}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Live Voice & Chat */}
        <div>
          <AIChatPanel defaultPrompt={activeEqTitle !== 'Pilih Peralatan' ? `Bagaimana analisa getaran dan diagnosa unbalance / misalignment untuk ${activeEqTitle}?` : undefined} />
        </div>
      </section>
    </div>
  );
}
