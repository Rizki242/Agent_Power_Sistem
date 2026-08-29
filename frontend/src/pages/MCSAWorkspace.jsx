import React, { useState, useEffect, useCallback } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { apiUrl } from '../api';

export default function MCSAWorkspace() {
  const [equipmentList, setEquipmentList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [voltageFilter, setVoltageFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [eqDetail, setEqDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'summary' | 'specs' | 'history'

  // Rotor Bar Calculator state
  const [showCalculator, setShowCalculator] = useState(false);
  const [calcUpper, setCalcUpper] = useState(-52.0);
  const [calcLower, setCalcLower] = useState(-54.0);
  const [calcHealth, setCalcHealth] = useState(0.85);
  const [calcResult, setCalcResult] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // Summary state
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetch(apiUrl('/api/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  const fetchEquipment = useCallback(() => {
    setLoading(true);
    let url = apiUrl('/api/equipment?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (voltageFilter !== 'ALL') url += `voltage=${encodeURIComponent(voltageFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setEquipmentList(data.equipment || []);
        setLoading(false);
        if (!selectedEquipment && data.equipment && data.equipment.length > 0) {
          loadEquipmentDetail(data.equipment[0].equipment);
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data equipment:', err);
        setLoading(false);
      });
  }, [unitFilter, voltageFilter, statusFilter, search, selectedEquipment]);

  useEffect(() => {
    fetchEquipment();
  }, [fetchEquipment]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchEquipment();
  };

  const loadEquipmentDetail = (eqName) => {
    setSelectedEquipment(eqName);
    setLoadingDetail(true);
    fetch(apiUrl(`/api/equipment/${encodeURIComponent(eqName)}`))
      .then(res => res.json())
      .then(data => {
        setEqDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Gagal memuat detail equipment:', err);
        setLoadingDetail(false);
      });
  };

  const handleCalculateRotorBar = async (e) => {
    e.preventDefault();
    setCalcLoading(true);
    try {
      const res = await fetch(apiUrl('/api/rotorbar/calculate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upper_sb: parseFloat(calcUpper),
          lower_sb: parseFloat(calcLower),
          health_index: parseFloat(calcHealth)
        })
      });
      const data = await res.json();
      setCalcResult(data);
    } catch (err) {
      console.error(err);
      alert('Gagal menghitung kondisi rotor bar.');
    } finally {
      setCalcLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const s = String(status || '').toUpperCase();
    if (s === 'NORMAL') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-green/10 text-green border border-green/30">NORMAL</span>;
    if (s === 'ALARM' || s === 'WARNING') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber/10 text-amber border border-amber/30">ALARM</span>;
    if (s === 'HIGH' || s === 'CRITICAL') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red/10 text-red border border-red/30 animate-pulse">HIGH</span>;
    if (s === 'STANDBY') return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30">STANDBY</span>;
    return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-muted/10 text-muted border border-line">{status || 'UNKNOWN'}</span>;
  };

  const counts = summary?.counts || { Normal: 0, Alarm: 0, High: 0, Standby: 0 };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-cyan font-black">Electrical Signature Analysis</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">MCSA Monitoring &amp; Parameter Testing</h2>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setShowCalculator(!showCalculator)}
            className="px-3 py-1.5 rounded-xl border border-cyan/40 bg-cyan/10 text-cyan text-xs font-bold hover:bg-cyan/20 transition-all flex items-center gap-1.5 shadow-neon"
          >
            <span>⚡</span> {showCalculator ? 'Tutup Kalkulator' : 'Rotor Bar Calc'}
          </button>
        </div>
      </div>

      {/* KPI Overview Bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-muted block uppercase tracking-wider font-bold">Total Motor MCSA</span>
            <strong className="text-xl text-textMain mt-1 block">{summary.total_equipment || 0} Unit</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-green block uppercase tracking-wider font-bold">Normal</span>
            <strong className="text-xl text-green mt-1 block">{counts.Normal || 0}</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-amber block uppercase tracking-wider font-bold">Alarm / Warning</span>
            <strong className="text-xl text-amber mt-1 block">{counts.Alarm || 0}</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-red block uppercase tracking-wider font-bold">High (Critical)</span>
            <strong className="text-xl text-red mt-1 block">{counts.High || 0}</strong>
          </div>
          <div className="border border-line bg-card-gradient shadow-neon p-3 rounded-2xl text-center">
            <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-bold">Standby</span>
            <strong className="text-xl text-slate-400 mt-1 block">{counts.Standby || 0}</strong>
          </div>
        </div>
      )}

      {/* Simulator Drawer */}
      {showCalculator && (
        <div className="border border-cyan/40 bg-panel2 rounded-2xl p-5 shadow-neon">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-bold text-cyan flex items-center gap-2">
              <span>⚡</span> Simulator Severity Rotor Bar (Sideband dB)
            </h3>
            <span className="text-[10px] text-muted">Ambang: &lt; -54 dB (Normal) | -54 s/d -45 dB (Alarm) | &ge; -45 dB (High)</span>
          </div>
          <form onSubmit={handleCalculateRotorBar} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
            <div>
              <label className="text-[10px] text-muted block mb-1">Upper Sideband (dB)</label>
              <input 
                type="number" 
                step="0.1" 
                value={calcUpper} 
                onChange={(e) => setCalcUpper(e.target.value)}
                className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" 
                required
              />
            </div>
            <div>
              <label className="text-[10px] text-muted block mb-1">Lower Sideband (dB)</label>
              <input 
                type="number" 
                step="0.1" 
                value={calcLower} 
                onChange={(e) => setCalcLower(e.target.value)}
                className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" 
                required
              />
            </div>
            <div>
              <label className="text-[10px] text-muted block mb-1">RB Health Index</label>
              <input 
                type="number" 
                step="0.01" 
                value={calcHealth} 
                onChange={(e) => setCalcHealth(e.target.value)}
                className="w-full bg-panel border border-line rounded-lg p-2 text-xs text-textMain outline-none focus:border-cyan" 
              />
            </div>
            <div>
              <button 
                type="submit" 
                disabled={calcLoading}
                className="w-full py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs disabled:opacity-50"
              >
                {calcLoading ? 'Menghitung...' : 'Hitung Severity'}
              </button>
            </div>
          </form>

          {calcResult && (
            <div className="mt-3 p-3 bg-panel rounded-xl border border-line grid sm:grid-cols-4 gap-3 items-center">
              <div>
                <span className="text-[10px] text-muted block">Status Hasil:</span>
                <div className="mt-1">{getStatusBadge(calcResult.status)}</div>
              </div>
              <div>
                <span className="text-[10px] text-muted block">Severity Level:</span>
                <strong className="text-sm text-textMain mt-1 block">Level {calcResult.severity_level} (1–4)</strong>
              </div>
              <div className="sm:col-span-2">
                <span className="text-[10px] text-muted block">Rekomendasi Tindak Lanjut:</span>
                <p className="text-xs text-textMain mt-0.5">{calcResult.recommendation}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Grid Layout */}
      <section className="grid lg:grid-cols-[1.55fr_0.95fr] gap-4">
        {/* Left Column: Asset Matrix & Telemetry Tabs */}
        <div className="flex flex-col gap-4">
          {/* Filters Bar */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-3.5 flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
            <form onSubmit={handleSearchSubmit} className="flex-1">
              <input 
                type="text" 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Cari Equipment (mis. BFP 1A, CEP 1A, IDF 1A, BC 10.1)..."
                className="w-full bg-panel2 border border-line rounded-lg px-3 py-1.5 text-xs text-textMain outline-none focus:border-cyan"
              />
            </form>
            <div className="flex items-center gap-1.5 flex-wrap">
              <select 
                value={unitFilter} 
                onChange={(e) => setUnitFilter(e.target.value)}
                className="bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-[11px] text-textMain outline-none focus:border-cyan"
              >
                <option value="ALL">Semua Unit</option>
                <option value="UNIT 1">UNIT 1</option>
                <option value="UNIT 2">UNIT 2</option>
                <option value="UNIT 3">UNIT 3</option>
                <option value="UNIT COMMON">UNIT COMMON</option>
              </select>
              <select 
                value={voltageFilter} 
                onChange={(e) => setVoltageFilter(e.target.value)}
                className="bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-[11px] text-textMain outline-none focus:border-cyan"
              >
                <option value="ALL">Semua Voltage</option>
                <option value="6.3 KV">6.3 KV</option>
                <option value="380/400 V">380/400 V</option>
              </select>
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-[11px] text-textMain outline-none focus:border-cyan"
              >
                <option value="ALL">Semua Status</option>
                <option value="Normal">Normal</option>
                <option value="Alarm">Alarm</option>
                <option value="High">High</option>
                <option value="Standby">Standby</option>
              </select>
            </div>
          </div>

          {/* Asset List Table */}
          <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 overflow-hidden">
            <div className="flex justify-between items-center mb-2.5">
              <span className="text-xs text-muted font-bold uppercase tracking-wider">
                Database Pengukuran MCSA ({equipmentList.length} Motor)
              </span>
              <span className="text-[10px] text-cyan">Klik baris untuk memuat parameter lengkap</span>
            </div>

            <div className="overflow-x-auto max-h-[260px] overflow-y-auto pr-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-panel border-b border-line z-10 text-muted">
                  <tr>
                    <th className="py-2 px-2.5">Equipment</th>
                    <th className="py-2 px-2.5">Unit</th>
                    <th className="py-2 px-2.5">Tegangan</th>
                    <th className="py-2 px-2.5">Rotor Bar</th>
                    <th className="py-2 px-2.5">Bearing</th>
                    <th className="py-2 px-2.5">Status</th>
                    <th className="py-2 px-2.5 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {loading ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Memuat database MCSA...</td>
                    </tr>
                  ) : equipmentList.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="py-8 text-center text-muted">Tidak ada equipment yang cocok dengan filter pencarian.</td>
                    </tr>
                  ) : (
                    equipmentList.map((eq, idx) => (
                      <tr 
                        key={idx}
                        onClick={() => loadEquipmentDetail(eq.equipment)}
                        className={`hover:bg-panel2/60 transition-colors cursor-pointer ${selectedEquipment === eq.equipment ? 'bg-panel2 border-l-2 border-l-cyan' : ''}`}
                      >
                        <td className="py-2 px-2.5 font-bold text-textMain">{eq.equipment}</td>
                        <td className="py-2 px-2.5 text-muted text-[11px]">{eq.unit}</td>
                        <td className="py-2 px-2.5 text-muted text-[11px]">{eq.voltage}</td>
                        <td className="py-2 px-2.5">
                          <span className={`text-[11px] font-mono ${eq.rotorbar_status === 'High' ? 'text-red font-bold' : (eq.rotorbar_status === 'Alarm' ? 'text-amber' : 'text-textMain')}`}>
                            {eq.rotorbar_status || 'Normal'}
                          </span>
                        </td>
                        <td className="py-2 px-2.5">
                          <span className={`text-[11px] font-mono ${eq.bearing_status === 'High' ? 'text-red font-bold' : (eq.bearing_status === 'Alarm' ? 'text-amber' : 'text-textMain')}`}>
                            {eq.bearing_status || 'Normal'}
                          </span>
                        </td>
                        <td className="py-2 px-2.5">{getStatusBadge(eq.condition || eq.status)}</td>
                        <td className="py-2 px-2.5 text-right">
                          <button 
                            onClick={(e) => { e.stopPropagation(); loadEquipmentDetail(eq.equipment); }}
                            className="px-2 py-0.5 rounded bg-panel border border-line text-cyan hover:border-cyan text-[10px]"
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

          {/* Equipment Parameter & Telemetry Detail */}
          {selectedEquipment && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 pb-3 border-b border-line">
                <div>
                  <span className="text-[10px] text-cyan uppercase tracking-wider font-bold">Hasil Pengujian &amp; Parameter MCSA</span>
                  <h3 className="text-lg font-bold text-textMain mt-0.5 flex items-center gap-2">
                    {selectedEquipment}
                    <span className="text-xs text-muted font-normal">({eqDetail?.unit || ''} · {eqDetail?.voltage || ''})</span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-lg border border-line p-0.5 bg-panel2 text-xs">
                    <button 
                      onClick={() => setActiveTab('telemetry')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'telemetry' ? 'bg-cyan text-[#071018] font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Nilai Pengujian
                    </button>
                    <button 
                      onClick={() => setActiveTab('summary')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'summary' ? 'bg-cyan text-[#071018] font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Ringkasan Kinerja
                    </button>
                    <button 
                      onClick={() => setActiveTab('specs')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'specs' ? 'bg-cyan text-[#071018] font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Nameplate
                    </button>
                    <button 
                      onClick={() => setActiveTab('history')}
                      className={`px-2.5 py-1 rounded-md transition-colors ${activeTab === 'history' ? 'bg-cyan text-[#071018] font-bold' : 'text-muted hover:text-textMain'}`}
                    >
                      Riwayat Tren
                    </button>
                  </div>
                  {eqDetail && getStatusBadge(eqDetail.condition)}
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-muted text-xs">Memuat detail telemetry peralatan...</div>
              ) : eqDetail ? (
                <div className="flex flex-col gap-4">
                  {/* TAB 1: Structured Telemetry Cards */}
                  {activeTab === 'telemetry' && (
                    <div className="flex flex-col gap-4">
                      {/* Section 1: Electrical Parameters (Arus & Tegangan) */}
                      <div>
                        <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                          <span>⚡</span> Parameter Kelistrikan &amp; Unbalance (Tanggal Uji: {eqDetail.latest_date || '-'})
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Arus Fasa 1 (I1)</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Current 1']?.value || '-'} <span className="text-[10px] font-normal text-muted">A</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Arus Fasa 2 (I2)</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Current 2']?.value || '-'} <span className="text-[10px] font-normal text-muted">A</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Arus Fasa 3 (I3)</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Current 3']?.value || '-'} <span className="text-[10px] font-normal text-muted">A</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Deviasi Arus (Unbalance)</span>
                            <strong className={`text-sm mt-1 block font-mono ${parseFloat(eqDetail.parameters?.['Dev Current']?.value) > 5 ? 'text-amber' : 'text-textMain'}`}>
                              {eqDetail.parameters?.['Dev Current']?.value || '-'} <span className="text-[10px] font-normal text-muted">%</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Tegangan V1</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Voltage 1']?.value || '-'} <span className="text-[10px] font-normal text-muted">V</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Tegangan V2</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Voltage 2']?.value || '-'} <span className="text-[10px] font-normal text-muted">V</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Tegangan V3</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Voltage 3']?.value || '-'} <span className="text-[10px] font-normal text-muted">V</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Deviasi Tegangan</span>
                            <strong className={`text-sm mt-1 block font-mono ${parseFloat(eqDetail.parameters?.['Dev Voltage']?.value) > 3 ? 'text-amber' : 'text-textMain'}`}>
                              {eqDetail.parameters?.['Dev Voltage']?.value || '-'} <span className="text-[10px] font-normal text-muted">%</span>
                            </strong>
                          </div>
                        </div>
                      </div>

                      {/* Section 2: Power Quality & Sideband */}
                      <div>
                        <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                          <span>📊</span> Kualitas Daya, Beban &amp; Spektrum Rotor Bar
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Beban Motor (Load)</span>
                            <strong className="text-sm text-cyan mt-1 block font-mono">
                              {eqDetail.parameters?.['Load']?.value ? `${parseFloat(eqDetail.parameters['Load'].value).toFixed(1)}%` : '-'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Power Factor (cos φ)</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['power factor']?.value || eqDetail.parameters?.['Power Factor']?.value || '-'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Real Power</span>
                            <strong className="text-sm text-textMain mt-1 block font-mono">
                              {eqDetail.parameters?.['Real Power']?.value || '-'} <span className="text-[10px] font-normal text-muted">kW</span>
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">THD Tegangan %</span>
                            <strong className={`text-sm mt-1 block font-mono ${parseFloat(eqDetail.parameters?.['THD Voltage %']?.value) > 5 ? 'text-amber' : 'text-textMain'}`}>
                              {eqDetail.parameters?.['THD Voltage %']?.value ? `${eqDetail.parameters['THD Voltage %'].value}%` : '-'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Upper Sideband (dB)</span>
                            <strong className={`text-sm mt-1 block font-mono ${parseFloat(eqDetail.parameters?.['Upper Sideband']?.value) >= -45 ? 'text-red' : (parseFloat(eqDetail.parameters?.['Upper Sideband']?.value) >= -54 ? 'text-amber' : 'text-textMain')}`}>
                              {eqDetail.parameters?.['Upper Sideband']?.value ? `${parseFloat(eqDetail.parameters['Upper Sideband'].value).toFixed(1)} dB` : '-'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Lower Sideband (dB)</span>
                            <strong className={`text-sm mt-1 block font-mono ${parseFloat(eqDetail.parameters?.['Lower Sideband']?.value) >= -45 ? 'text-red' : (parseFloat(eqDetail.parameters?.['Lower Sideband']?.value) >= -54 ? 'text-amber' : 'text-textMain')}`}>
                              {eqDetail.parameters?.['Lower Sideband']?.value ? `${parseFloat(eqDetail.parameters['Lower Sideband'].value).toFixed(1)} dB` : '-'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Kondisi Rotor Bar</span>
                            <strong className={`text-sm mt-1 block ${eqDetail.parameters?.['Rotorbar']?.value === 'High' ? 'text-red' : (eqDetail.parameters?.['Rotorbar']?.value === 'Alarm' ? 'text-amber' : 'text-green')}`}>
                              {eqDetail.parameters?.['Rotorbar']?.value || 'Normal'}
                            </strong>
                          </div>
                          <div className="bg-panel p-2.5 rounded-xl border border-line">
                            <span className="text-[10px] text-muted block">Status Bearing</span>
                            <strong className={`text-sm mt-1 block ${eqDetail.parameters?.['Bearing']?.value === 'High' ? 'text-red' : (eqDetail.parameters?.['Bearing']?.value === 'Alarm' ? 'text-amber' : 'text-green')}`}>
                              {eqDetail.parameters?.['Bearing']?.value || 'Normal'}
                            </strong>
                          </div>
                        </div>
                      </div>

                      {/* Recommendations */}
                      {eqDetail.recommendations && eqDetail.recommendations.length > 0 && (
                        <div className="bg-panel2 p-3.5 rounded-xl border border-line">
                          <h4 className="text-xs font-bold text-amber mb-1.5 flex items-center gap-1.5">
                            <span>🛠️</span> Rekomendasi Diagnosa &amp; Tindak Lanjut
                          </h4>
                          <ul className="list-disc list-inside text-xs text-textMain space-y-1">
                            {eqDetail.recommendations.map((rec, rIdx) => (
                              <li key={rIdx}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: Performance Summary */}
                  {activeTab === 'summary' && (
                    <div className="flex flex-col gap-3">
                      <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-1">Ringkasan Kinerja Komponen (ATPOLL II &amp; Laporan MCSA)</h4>
                      {eqDetail.performance_summary && Object.keys(eqDetail.performance_summary).length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          {Object.entries(eqDetail.performance_summary).map(([k, v], sIdx) => (
                            <div key={sIdx} className="bg-panel p-3 rounded-xl border border-line">
                              <span className="text-[10px] text-cyan uppercase font-bold block">{k}</span>
                              <p className="text-xs text-textMain mt-1 leading-relaxed">{v}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-4 text-center text-xs text-muted bg-panel rounded-xl border border-line">
                          Tidak ada parameter teks ringkasan kinerja yang tersimpan untuk equipment ini.
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 3: Nameplate Specifications */}
                  {activeTab === 'specs' && (
                    <div className="flex flex-col gap-3">
                      <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-1">Spesifikasi Nameplate Motor</h4>
                      {eqDetail.specification && Object.keys(eqDetail.specification).length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                          {Object.entries(eqDetail.specification).map(([k, v], spIdx) => (
                            <div key={spIdx} className="bg-panel p-2.5 rounded-xl border border-line">
                              <span className="text-[10px] text-muted block">{k.replace(/_/g, ' ')}</span>
                              <strong className="text-xs text-textMain mt-0.5 block font-mono">{String(v)}</strong>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-4 text-center text-xs text-muted bg-panel rounded-xl border border-line">
                          Data spesifikasi nameplate belum terdaftar di database master.
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 4: History Table */}
                  {activeTab === 'history' && (
                    <div className="flex flex-col gap-3">
                      <h4 className="text-[11px] font-bold text-muted uppercase tracking-wider mb-1">Riwayat Pengukuran Berkala</h4>
                      {eqDetail.history && eqDetail.history.length > 0 ? (
                        <div className="overflow-x-auto max-h-[280px] overflow-y-auto">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead className="sticky top-0 bg-panel border-b border-line">
                              <tr className="text-muted">
                                <th className="py-2 px-2.5">Tanggal</th>
                                <th className="py-2 px-2.5">Kondisi</th>
                                <th className="py-2 px-2.5">Load %</th>
                                <th className="py-2 px-2.5">Current 1 (A)</th>
                                <th className="py-2 px-2.5">Voltage 1 (V)</th>
                                <th className="py-2 px-2.5">Dev I %</th>
                                <th className="py-2 px-2.5">Upper SB (dB)</th>
                                <th className="py-2 px-2.5">Rotorbar</th>
                                <th className="py-2 px-2.5">Bearing</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-line/60">
                              {eqDetail.history.map((h, hIdx) => {
                                const loadVal = h.Load !== undefined && h.Load !== '' ? Number(h.Load).toFixed(1) : '-';
                                const c1Val = h['Current 1'] !== undefined && h['Current 1'] !== '' ? Number(h['Current 1']).toFixed(1) : '-';
                                const v1Val = h['Voltage 1'] !== undefined && h['Voltage 1'] !== '' ? Number(h['Voltage 1']).toFixed(0) : '-';
                                const devI = h['Dev Current'] !== undefined && h['Dev Current'] !== '' ? `${Number(h['Dev Current']).toFixed(1)}%` : '-';
                                const sbVal = h['Upper Sideband'] !== undefined && h['Upper Sideband'] !== '' ? `${Number(h['Upper Sideband']).toFixed(1)} dB` : '-';
                                return (
                                  <tr key={hIdx} className="hover:bg-panel2/40">
                                    <td className="py-2 px-2.5 font-mono text-textMain">{h.date}</td>
                                    <td className="py-2 px-2.5">{getStatusBadge(h.Kondisi)}</td>
                                    <td className="py-2 px-2.5 font-mono text-textMain">{loadVal !== '-' ? `${loadVal}%` : '-'}</td>
                                    <td className="py-2 px-2.5 font-mono text-textMain">{c1Val}</td>
                                    <td className="py-2 px-2.5 font-mono text-textMain">{v1Val}</td>
                                    <td className="py-2 px-2.5 font-mono text-muted">{devI}</td>
                                    <td className="py-2 px-2.5 font-mono text-muted">{sbVal}</td>
                                    <td className="py-2 px-2.5 font-mono text-textMain">{h.Rotorbar || '-'}</td>
                                    <td className="py-2 px-2.5 font-mono text-textMain">{h.Bearing || '-'}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-4 text-center text-xs text-muted bg-panel rounded-xl border border-line">
                          Belum ada riwayat pengujian tercatat.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel defaultPrompt={selectedEquipment ? `Bagaimana status dan evaluasi MCSA terkini untuk motor ${selectedEquipment}? Jelaskan kondisi arus, deviasi tegangan, dan rotor bar-nya.` : undefined} />
        </div>
      </section>
    </div>
  );
}
