import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertOctagon, AlertTriangle, Calculator,
  CheckCircle2, ChevronRight, ClipboardList, Database, Filter,
  Gauge, RefreshCw, Search, SlidersHorizontal, X, Zap,
} from 'lucide-react'
import {
  calculateRotorBar,
  generateCbmWorkOrder,
  getMcsaEquipmentDetail,
  getMcsaEquipmentList,
  getMcsaSummary,
} from './api.js'

function normalizeStatus(status) {
  const value = String(status || '').toLowerCase()
  if (['normal', 'healthy', 'good', 'baik'].includes(value)) return 'healthy'
  if (['alarm', 'warning', 'alert', 'waspada'].includes(value)) return 'attention'
  if (['high', 'critical', 'kritis', 'danger', 'rusak'].includes(value)) return 'critical'
  return 'neutral'
}

function StatusBadge({ status, label }) {
  const text = label || status || 'Normal'
  const state = normalizeStatus(status)
  return (
    <span className={`status status--${state}`}>
      <i />
      {text}
    </span>
  )
}

function RotorBarBadge({ status }) {
  const s = String(status || 'Normal').toLowerCase()
  let state = 'healthy'
  if (s.includes('critical') || s.includes('high') || s.includes('kritis')) state = 'critical'
  else if (s.includes('alert') || s.includes('alarm') || s.includes('waspada')) state = 'attention'
  return (
    <span className={`status status--${state}`}>
      <i />
      {status || 'Normal'}
    </span>
  )
}

function EquipmentDetailDrawer({ equipmentName, onClose, onOpenWorkOrder }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [woCreating, setWoCreating] = useState(false)
  const [woSuccess, setWoSuccess] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    getMcsaEquipmentDetail(equipmentName, controller.signal)
      .then((res) => {
        setDetail(res)
        setLoading(false)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Gagal memuat detail equipment')
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [equipmentName])

  async function handleCreateWo() {
    if (!detail) return
    setWoCreating(true)
    setWoSuccess(null)
    try {
      const isCrit = String(detail.condition || '').toLowerCase() === 'high'
      const res = await generateCbmWorkOrder({
        equipment: detail.equipment,
        domain: 'MCSA',
        severity: isCrit ? 'CRITICAL' : 'WARNING',
        anomaly_desc: `Temuan anomali MCSA pada ${detail.equipment}: Kondisi=${detail.condition}. RotorBar=${detail.telemetry_groups?.rotor_bar?.['Upper SB']?.value || '-'} dB`,
        created_by: 'Engineer MCSA Workspace',
      })
      setWoSuccess(res.work_order?.wo_number || 'WO Berhasil Diterbitkan')
    } catch (err) {
      alert(`Gagal membuat Work Order: ${err.message}`)
    } finally {
      setWoCreating(false)
    }
  }

  const spec = detail?.specification || {}
  const groups = detail?.telemetry_groups || {}
  const perf = detail?.performance_summary || {}
  const recs = detail?.recommendations || []
  const history = detail?.history || []

  return (
    <aside className="config-panel" style={{ width: 'min(90vw, 680px)', maxWidth: '680px' }} aria-label={`Detail MCSA ${equipmentName}`}>
      <div className="config-panel__header">
        <div>
          <span>Detail Telemetri & Diagnosa MCSA</span>
          <h2>{equipmentName}</h2>
          <code>{detail?.unit || '-'} | {detail?.voltage || '-'}</code>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Tutup"><X size={18} /></button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 20px', gap: '12px', color: 'var(--muted)' }}>
          <RefreshCw size={24} className="spin" />
          <span>Memuat data MCSA motor...</span>
        </div>
      ) : error ? (
        <div className="notice notice--error" style={{ margin: '20px' }}>
          <strong>Gagal memuat telemetri:</strong> {error}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '30px' }}>
          {/* Status Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', background: 'var(--canvas)', borderRadius: '10px', border: '1px solid var(--border)' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)', display: 'block' }}>Kondisi Keseluruhan</span>
              <div style={{ marginTop: '4px' }}>
                <StatusBadge status={detail?.condition} label={detail?.condition || 'Normal'} />
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)', display: 'block' }}>Tanggal Uji Terakhir</span>
              <strong style={{ fontSize: '0.88rem' }}>{detail?.latest_date || '-'}</strong>
            </div>
          </div>

          {/* Action Notification */}
          {woSuccess && (
            <div className="notice" style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} color="#059669" />
                <span>Work Order terbit: <strong>{woSuccess}</strong></span>
              </div>
              <button
                type="button"
                className="button button--secondary"
                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                onClick={() => onOpenWorkOrder && onOpenWorkOrder(woSuccess)}
              >
                Lihat WO
              </button>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="button button--primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={handleCreateWo}
              disabled={woCreating}
            >
              <ClipboardList size={16} />
              {woCreating ? 'Menerbitkan...' : 'Terbitkan WO CBM'}
            </button>
            <a
              href={`/chat?query=${encodeURIComponent(`Bagaimana kondisi motor ${equipmentName} berdasarkan data MCSA terakhir?`)}`}
              className="button button--secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}
            >
              <Zap size={16} />
              Konsultasi AI Bot
            </a>
          </div>

          {/* Nameplate Specifications */}
          {Object.keys(spec).length > 0 && (
            <div className="config-section">
              <div>
                <h3>Spesifikasi Nameplate Motor</h3>
                <p>Parameter rating desain elektro-mekanikal motor.</p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginTop: '10px' }}>
                {Object.entries(spec).map(([k, v]) => (
                  <div key={k} style={{ padding: '10px 12px', background: '#fafcfc', border: '1px solid var(--border)', borderRadius: '8px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'block' }}>{k}</span>
                    <strong style={{ fontSize: '0.85rem', color: 'var(--ink)' }}>{String(v) || '-'}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Telemetry Groups */}
          <div className="config-section">
            <div>
              <h3>Parameter Telemetri Terukur</h3>
              <p>Nilai pengukuran lapangan aktual dan deviasi standar IEEE / EPRI.</p>
            </div>

            {/* Electrical Parameters */}
            {groups.electrical && Object.keys(groups.electrical).length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <strong style={{ fontSize: '0.82rem', color: 'var(--action)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Zap size={15} /> Parameter Kelistrikan & Deviasi Fasa
                </strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                  {Object.entries(groups.electrical).map(([k, v]) => (
                    <div key={k} style={{ padding: '9px 12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'block' }}>{k}</span>
                      <strong style={{ fontSize: '0.88rem', color: 'var(--ink)' }}>
                        {v.value} {v.unit}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rotor Bar Parameters */}
            {groups.rotor_bar && Object.keys(groups.rotor_bar).length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <strong style={{ fontSize: '0.82rem', color: '#b86608', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Activity size={15} /> Indikator Rotor Bar Signature (MCSA Sideband)
                </strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                  {Object.entries(groups.rotor_bar).map(([k, v]) => (
                    <div key={k} style={{ padding: '9px 12px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '8px' }}>
                      <span style={{ fontSize: '0.72rem', color: '#92400e', display: 'block' }}>{k}</span>
                      <strong style={{ fontSize: '0.88rem', color: '#78350f' }}>
                        {v.value} {v.unit}
                      </strong>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '6px' }}>
                  * Standar EPRI: Sideband &lt; -54 dB (Baik), -54 s/d -45 dB (Waspada), &ge; -45 dB (Kritis/Patah)
                </div>
              </div>
            )}

            {/* Power Quality Parameters */}
            {groups.power_quality && Object.keys(groups.power_quality).length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <strong style={{ fontSize: '0.82rem', color: 'var(--healthy)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Gauge size={15} /> Kualitas Daya & Harmonik (IEEE 519)
                </strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                  {Object.entries(groups.power_quality).map(([k, v]) => (
                    <div key={k} style={{ padding: '9px 12px', background: '#f0fdf4', border: '1px solid #dcfce7', borderRadius: '8px' }}>
                      <span style={{ fontSize: '0.72rem', color: '#166534', display: 'block' }}>{k}</span>
                      <strong style={{ fontSize: '0.88rem', color: '#14532d' }}>
                        {v.value} {v.unit}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Performance Summary */}
          {Object.keys(perf).length > 0 && (
            <div className="config-section">
              <div>
                <h3>Ringkasan Kinerja (Performance Summary)</h3>
                <p>Analisis kualitatif teknis kondisi komponen motor.</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                {Object.entries(perf).map(([k, v]) => (
                  <div key={k} style={{ padding: '10px 14px', background: 'var(--canvas)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <strong style={{ fontSize: '0.8rem', color: 'var(--ink)', textTransform: 'capitalize' }}>{k}</strong>
                    <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: 'var(--muted)', lineHeight: '1.45' }}>{String(v)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations & Standards */}
          {recs.length > 0 && (
            <div className="config-section">
              <div>
                <h3>Rekomendasi Tindakan Teknis</h3>
                <p>Instruksi CBM untuk tim pemeliharaan listrik.</p>
              </div>
              <ul style={{ margin: '10px 0 0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {recs.map((rec, idx) => (
                  <li key={idx} style={{ fontSize: '0.82rem', color: 'var(--ink)', lineHeight: '1.45' }}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* History Trend Table */}
          {history.length > 0 && (
            <div className="config-section">
              <div>
                <h3>Riwayat Tren Pengukuran</h3>
                <p>Data time-series pengukuran sebelumnya.</p>
              </div>
              <div style={{ overflowX: 'auto', marginTop: '10px' }}>
                <table className="data-table" style={{ fontSize: '0.78rem' }}>
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Kondisi</th>
                      <th>Upper SB</th>
                      <th>Lower SB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h, i) => (
                      <tr key={i}>
                        <td>{h.date || '-'}</td>
                        <td><StatusBadge status={h.Kondisi || h.condition} /></td>
                        <td>{h['Upper SB'] != null ? `${h['Upper SB']} dB` : '-'}</td>
                        <td>{h['Lower SB'] != null ? `${h['Lower SB']} dB` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </aside>
  )
}

function RotorBarCalculatorModal({ onClose }) {
  const [upperSb, setUpperSb] = useState('-58.0')
  const [lowerSb, setLowerSb] = useState('-57.5')
  const [healthIndex, setHealthIndex] = useState('85')
  const [evaluating, setEvaluating] = useState(false)
  const [result, setResult] = useState(null)

  async function handleEval() {
    setEvaluating(true)
    try {
      const res = await calculateRotorBar({
        upper_sb: Number.parseFloat(upperSb) || -54.0,
        lower_sb: Number.parseFloat(lowerSb) || -54.0,
        health_index: healthIndex ? Number.parseFloat(healthIndex) : null,
      })
      setResult(res)
    } catch (err) {
      alert(`Evaluasi gagal: ${err.message}`)
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 1000, padding: '20px' }}>
      <div className="modal-card" style={{ background: 'var(--surface)', borderRadius: '16px', padding: '24px', maxWidth: '520px', width: '100%', border: '1px solid var(--border)', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#ecfeff', display: 'grid', placeItems: 'center', color: '#0891b2' }}>
              <Calculator size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--ink)' }}>Kalkulator Evaluasi Rotor Bar</h3>
              <span style={{ fontSize: '0.74rem', color: 'var(--muted)' }}>Standar EPRI / IEEE Motor Current Signature</span>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Tutup"><X size={18} /></button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink)', display: 'block', marginBottom: '4px' }}>
              Upper Sideband (dB)
            </label>
            <input
              type="number"
              step="0.1"
              value={upperSb}
              onChange={(e) => setUpperSb(e.target.value)}
              className="search-field"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink)', display: 'block', marginBottom: '4px' }}>
              Lower Sideband (dB)
            </label>
            <input
              type="number"
              step="0.1"
              value={lowerSb}
              onChange={(e) => setLowerSb(e.target.value)}
              className="search-field"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ink)', display: 'block', marginBottom: '4px' }}>
              Health Index (Opsional, 0 - 100)
            </label>
            <input
              type="number"
              value={healthIndex}
              onChange={(e) => setHealthIndex(e.target.value)}
              className="search-field"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}
            />
          </div>

          <button
            type="button"
            className="button button--primary"
            onClick={handleEval}
            disabled={evaluating}
            style={{ width: '100%', marginTop: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
          >
            <Zap size={16} />
            {evaluating ? 'Mengevaluasi...' : 'Hitung Kondisi Rotor Bar'}
          </button>

          {result && (
            <div style={{ marginTop: '12px', padding: '14px', borderRadius: '10px', background: 'var(--canvas)', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>Status Evaluasi:</span>
                <StatusBadge status={result.condition || result.status} />
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--ink)', lineHeight: '1.45' }}>
                <strong>Tingkat Keparahan:</strong> {result.severity || 'Normal'}
              </div>
              {result.recommendation && (
                <div style={{ marginTop: '8px', fontSize: '0.8rem', color: 'var(--muted)', lineHeight: '1.45' }}>
                  <strong>Rekomendasi:</strong> {result.recommendation}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function MCSAWorkspace() {
  const [summary, setSummary] = useState(null)
  const [equipmentList, setEquipmentList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Filters
  const [search, setSearch] = useState('')
  const [selectedUnit, setSelectedUnit] = useState('all')
  const [selectedVoltage, setSelectedVoltage] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')

  // Selected Equipment Drawer
  const [selectedEquipment, setSelectedEquipment] = useState(null)
  const [showCalculator, setShowCalculator] = useState(false)

  const fetchData = useCallback(async (signal) => {
    setLoading(true)
    setError('')
    try {
      const [sumRes, eqRes] = await Promise.all([
        getMcsaSummary(signal),
        getMcsaEquipmentList(
          {
            unit: selectedUnit,
            voltage: selectedVoltage,
            status: selectedStatus,
            search,
          },
          signal,
        ),
      ])
      setSummary(sumRes)
      setEquipmentList(eqRes.equipment || [])
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Gagal memuat data MCSA dari backend')
      }
    } finally {
      setLoading(false)
    }
  }, [selectedUnit, selectedVoltage, selectedStatus, search])

  useEffect(() => {
    const controller = new AbortController()
    fetchData(controller.signal)
    return () => controller.abort()
  }, [fetchData])

  const units = useMemo(() => summary?.units || ['UNIT 1', 'UNIT 2', 'UNIT 3'], [summary])
  const voltages = useMemo(() => summary?.voltages || ['380-400 V', '6.3 kV'], [summary])
  const counts = summary?.counts || { Normal: 0, Alarm: 0, High: 0, Standby: 0 }

  return (
    <div className="page data-page" style={{ paddingBottom: '60px' }}>
      {/* Header */}
      <header className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', fontWeight: 600, color: '#0891b2', background: '#ecfeff', padding: '2px 8px', borderRadius: '99px', border: '1px solid #cffafe' }}>
              <Zap size={12} /> Domain MCSA
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>PLTU Jeranjang 3 × 25 MW</span>
          </div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            MCSA & Kelistrikan Motor
          </h1>
          <p>Monitoring Kondisi Rotor Bar, Kualitas Daya, dan Spektrum Arus Motor Listrik.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => setShowCalculator(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Calculator size={16} />
            Kalkulator Rotor Bar
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => fetchData()}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Muat Ulang
          </button>
        </div>
      </header>

      {/* KPI Cards Strip */}
      <section className="data-summary" aria-label="Ringkasan Status MCSA">
        <div>
          <Database size={19} color="#0891b2" />
          <span>Total Motor Terpantau</span>
          <strong>{loading ? '—' : summary?.total_equipment || equipmentList.length}</strong>
        </div>
        <div>
          <CheckCircle2 size={19} color="var(--healthy)" />
          <span>Normal (Operasi Baik)</span>
          <strong style={{ color: 'var(--healthy)' }}>{loading ? '—' : counts.Normal}</strong>
        </div>
        <div>
          <AlertTriangle size={19} color="var(--attention)" />
          <span>Alarm (Perlu Monitoring)</span>
          <strong style={{ color: 'var(--attention)' }}>{loading ? '—' : counts.Alarm}</strong>
        </div>
        <div>
          <AlertOctagon size={19} color="var(--critical)" />
          <span>High / Kritis (Tindakan Cepat)</span>
          <strong style={{ color: 'var(--critical)' }}>{loading ? '—' : counts.High}</strong>
        </div>
      </section>

      {/* Error Notice */}
      {error && (
        <div className="notice notice--error" style={{ marginBottom: '20px' }}>
          <strong>Gagal memuat data MCSA:</strong> {error}. Pastikan API server FastAPI berjalan di port 8000.
        </div>
      )}

      {/* Table Section */}
      <section className="data-table-panel">
        <div className="data-toolbar">
          <div className="search-field" style={{ flex: '1 1 280px' }}>
            <Search size={18} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari motor (contoh: Coal Crusher, IDF, BFP, PA FAN)..."
              aria-label="Cari equipment motor"
            />
          </div>
          <div className="filter-field">
            <Filter size={16} />
            <select
              value={selectedUnit}
              onChange={(e) => setSelectedUnit(e.target.value)}
              aria-label="Filter Unit"
            >
              <option value="all">Semua Unit</option>
              {units.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
          <div className="filter-field">
            <SlidersHorizontal size={16} />
            <select
              value={selectedVoltage}
              onChange={(e) => setSelectedVoltage(e.target.value)}
              aria-label="Filter Tegangan"
            >
              <option value="all">Semua Tegangan</option>
              {voltages.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
          <div className="filter-field">
            <Gauge size={16} />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              aria-label="Filter Status"
            >
              <option value="all">Semua Kondisi</option>
              <option value="Normal">Normal</option>
              <option value="Alarm">Alarm</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>

        <div className="table-caption" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <strong>Daftar Equipment & Telemetri Motor</strong>
            <span>{equipmentList.length} motor ditampilkan</span>
          </div>
          <span style={{ fontSize: '0.74rem', color: 'var(--muted)' }}>
            Standar: EPRI MCSA &bull; IEEE 519 &bull; IEC 60034
          </span>
        </div>

        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nama Equipment Motor</th>
                <th>Unit</th>
                <th>Tegangan</th>
                <th>Kondisi Keseluruhan</th>
                <th>Status Rotor Bar</th>
                <th>Status Bearing</th>
                <th>Uji Terakhir</th>
                <th><span className="sr-only">Aksi</span></th>
              </tr>
            </thead>
            <tbody>
              {equipmentList.map((item) => (
                <tr key={item.equipment}>
                  <td>
                    <button
                      type="button"
                      className="asset-link"
                      onClick={() => setSelectedEquipment(item.equipment)}
                      style={{ textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                      <strong>{item.equipment}</strong>
                      <code>{item.unit || '-'} | {item.voltage || '-'}</code>
                    </button>
                  </td>
                  <td>{item.unit || '-'}</td>
                  <td>
                    <span style={{ fontSize: '0.76rem', padding: '2px 8px', background: 'var(--canvas)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                      {item.voltage || '-'}
                    </span>
                  </td>
                  <td><StatusBadge status={item.status || item.condition} /></td>
                  <td><RotorBarBadge status={item.rotorbar_status} /></td>
                  <td><StatusBadge status={item.bearing_status} /></td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{item.last_date || item.date || '-'}</td>
                  <td>
                    <button
                      type="button"
                      className="row-action"
                      onClick={() => setSelectedEquipment(item.equipment)}
                      aria-label={`Buka detail ${item.equipment}`}
                      title="Buka detail telemetri"
                    >
                      <ChevronRight size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {loading && (
            <div className="table-state">
              <RefreshCw size={20} className="spin" />
              Memuat data telemetri motor MCSA...
            </div>
          )}

          {!loading && equipmentList.length === 0 && (
            <div className="table-state">
              <Search size={20} />
              Tidak ada motor yang cocok dengan filter yang dipilih.
            </div>
          )}
        </div>
      </section>

      {/* Detail Drawer */}
      {selectedEquipment && (
        <>
          <button
            type="button"
            className="panel-backdrop"
            onClick={() => setSelectedEquipment(null)}
            aria-label="Tutup detail"
          />
          <EquipmentDetailDrawer
            equipmentName={selectedEquipment}
            onClose={() => setSelectedEquipment(null)}
            onOpenWorkOrder={(woNum) => {
              window.location.href = `/work-orders?search=${encodeURIComponent(woNum)}`
            }}
          />
        </>
      )}

      {/* Rotor Bar Calculator Modal */}
      {showCalculator && (
        <RotorBarCalculatorModal onClose={() => setShowCalculator(false)} />
      )}
    </div>
  )
}
