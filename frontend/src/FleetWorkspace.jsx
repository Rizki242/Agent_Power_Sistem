import { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight,
  CheckCircle2,
  ClipboardList,
  Clock,
  Filter,
  RefreshCw,
  Search,
  ShieldAlert,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { generateCbmWorkOrder, getFleetReliability } from './api.js'

const HEALTH_COLORS = {
  HEALTHY: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: '#10b981' },
  WATCH: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa', border: '#3b82f6' },
  WARNING: { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: '#f59e0b' },
  ALERT: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', border: '#f97316' },
  CRITICAL: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', border: '#ef4444' },
}

export default function FleetWorkspace() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterText, setFilterText] = useState('')
  const [unitFilter, setUnitFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [woSuccessMsg, setWoSuccessMsg] = useState(null)

  const fetchData = async (signal) => {
    setLoading(true)
    setError(null)
    try {
      const res = await getFleetReliability(signal)
      setData(res)
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Gagal memuat data keandalan armada')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    fetchData(controller.signal)
    return () => controller.abort()
  }, [])

  const handleQuickWo = async (item) => {
    try {
      const res = await generateCbmWorkOrder({
        equipment: item.equipment,
        domain: item.primary_failure_mode ? `CBM: ${item.primary_failure_mode}` : 'Fleet Reliability Fusion',
        severity: item.health_status === 'CRITICAL' ? 'CRITICAL' : 'WARNING',
        anomaly_desc: `Kondisi kesehatan ${item.health_status} (${item.health_index.toFixed(1)}%). Mode kegagalan: ${item.primary_failure_mode || 'Anomali CBM'}. Sisa estimasi umur: ${item.rul_days || '-'} hari.`,
        recommendations: [
          'Lakukan inspeksi visual dan pengukuran lanjutan',
          'Verifikasi pelumasan dan keselarasan (alignment)',
        ],
        created_by: 'Fleet Command Center',
      })
      setWoSuccessMsg(`Work Order ${res.work_order?.wo_number} untuk ${item.equipment} berhasil dibuat!`)
      setTimeout(() => setWoSuccessMsg(null), 6000)
    } catch (err) {
      alert(`Gagal menerbitkan Work Order: ${err.message}`)
    }
  }

  // Filter asset matrix
  const assetList = data?.asset_matrix || []
  const filteredAssets = useMemo(() => {
    return assetList.filter((item) => {
      const matchText =
        !filterText.trim() ||
        String(item.equipment || '').toLowerCase().includes(filterText.toLowerCase()) ||
        String(item.system || '').toLowerCase().includes(filterText.toLowerCase()) ||
        String(item.primary_failure_mode || '').toLowerCase().includes(filterText.toLowerCase())

      const matchUnit =
        unitFilter === 'ALL' ||
        String(item.unit || '').toUpperCase() === unitFilter.toUpperCase()

      const matchStatus =
        statusFilter === 'ALL' ||
        String(item.health_status || '').toUpperCase() === statusFilter.toUpperCase()

      return matchText && matchUnit && matchStatus
    })
  }, [assetList, filterText, unitFilter, statusFilter])

  // Watchlist & Unit Summary
  const watchlist = data?.critical_watchlist || []
  const unitSummary = data?.unit_summary || {}

  return (
    <div className="page fleet-workspace">
      {/* Header */}
      <header className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="domain-pill" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
              PLTU JERANJANG (3 × 25 MW)
            </span>
            <span style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>CBM Reliability & Condition Fusion</span>
          </div>
          <h1>Fleet Reliability Command Center</h1>
          <p>Pemantauan keandalan armada pembangkit, fusi kondisi multi-domain CBM, matriks risiko, dan deteksi anomali kritis.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            className="button"
            onClick={() => fetchData()}
            disabled={loading}
            title="Muat ulang data armada"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            <span>Segarkan Data</span>
          </button>
          <Link to="/work-orders" className="button button--primary" style={{ textDecoration: 'none' }}>
            <ClipboardList size={16} />
            <span>Daftar Work Orders</span>
          </Link>
        </div>
      </header>

      {woSuccessMsg && (
        <div className="notice notice--success" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} style={{ color: '#10b981' }} />
            <span>{woSuccessMsg}</span>
          </div>
          <Link to="/work-orders" style={{ fontSize: '0.85rem', color: '#10b981', fontWeight: 'bold' }}>
            Buka Tiket <ArrowUpRight size={14} />
          </Link>
        </div>
      )}

      {loading && !data ? (
        <div className="empty-state" style={{ minHeight: '350px' }}>
          <div className="chat-typing-indicator"><span /><span /><span /></div>
          <span>Menganalisis fusi keandalan seluruh armada pembangkit...</span>
        </div>
      ) : error ? (
        <div className="notice notice--error">
          <strong>Gagal Memuat Keandalan Armada</strong>
          <span>{error}</span>
        </div>
      ) : (
        <>
          {/* Executive KPI Strip */}
          <section className="overview-strip" aria-label="Ringkasan Kesehatan Armada" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', marginBottom: '24px' }}>
            <div>
              <span>Rata-Rata Kesehatan Armada</span>
              <strong style={{ color: data?.fleet_health_average >= 85 ? '#10b981' : data?.fleet_health_average >= 70 ? '#f59e0b' : '#ef4444', fontSize: '1.4rem' }}>
                {data?.fleet_health_average ? `${data.fleet_health_average.toFixed(1)}%` : '—'}
              </strong>
            </div>
            <div>
              <span>Total Mesin Dipantau</span>
              <strong>{data?.total_assets || 0} unit</strong>
            </div>
            <div>
              <span style={{ color: '#10b981' }}>Healthy (Normal)</span>
              <strong style={{ color: '#10b981' }}>{data?.health_summary?.HEALTHY || 0}</strong>
            </div>
            <div>
              <span style={{ color: '#60a5fa' }}>Watch (Pantau)</span>
              <strong style={{ color: '#60a5fa' }}>{data?.health_summary?.WATCH || 0}</strong>
            </div>
            <div>
              <span style={{ color: '#f59e0b' }}>Warning (Waspada)</span>
              <strong style={{ color: '#f59e0b' }}>{data?.health_summary?.WARNING || 0}</strong>
            </div>
            <div>
              <span style={{ color: '#ef4444' }}>Alert / Critical</span>
              <strong style={{ color: '#ef4444' }}>
                {(data?.health_summary?.ALERT || 0) + (data?.health_summary?.CRITICAL || 0)}
              </strong>
            </div>
          </section>

          {/* Unit Breakdown Cards (3x25 MW) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            {['UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON'].map((uKey) => {
              const uData = unitSummary[uKey] || { total: 0, avg_health: 90, HEALTHY: 0, WATCH: 0, WARNING: 0, ALERT: 0, CRITICAL: 0 }
              const avg = uData.avg_health || 90
              const healthColor = avg >= 85 ? '#10b981' : avg >= 70 ? '#f59e0b' : '#ef4444'

              return (
                <div
                  key={uKey}
                  style={{
                    background: 'var(--panel)',
                    border: '1px solid var(--border)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Zap size={18} style={{ color: healthColor }} />
                      <strong style={{ fontSize: '1.05rem', color: '#f8fafc' }}>{uKey}</strong>
                    </div>
                    <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: healthColor, background: `${healthColor}18`, padding: '2px 8px', borderRadius: '4px', border: `1px solid ${healthColor}33` }}>
                      {avg.toFixed(1)}% Health
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden', marginBottom: '12px' }}>
                    <div style={{ height: '100%', width: `${Math.min(Math.max(avg, 0), 100)}%`, background: healthColor, borderRadius: '3px' }} />
                  </div>

                  {/* Stats pills */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--muted)' }}>
                    <span>Total: <strong style={{ color: '#cbd5e1' }}>{uData.total} aset</strong></span>
                    <span>Anomali: <strong style={{ color: (uData.ALERT + uData.CRITICAL) > 0 ? '#ef4444' : '#10b981' }}>{uData.ALERT + uData.CRITICAL}</strong></span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Critical Watchlist & Bad Actors */}
          {watchlist.length > 0 && (
            <div style={{ marginBottom: '24px', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '12px', padding: '18px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <ShieldAlert size={20} style={{ color: '#ef4444' }} />
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc' }}>
                  Critical Watchlist — Tindakan Prioritas Segera ({watchlist.length})
                </h3>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {watchlist.map((item, idx) => {
                  const styleColor = HEALTH_COLORS[item.health_status] || HEALTH_COLORS.CRITICAL
                  return (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--panel)',
                        border: `1px solid ${styleColor.border}`,
                        borderRadius: '10px',
                        padding: '14px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                          <div>
                            <strong style={{ fontSize: '1.02rem', color: '#f8fafc' }}>{item.equipment}</strong>
                            <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{item.unit} • {item.system || 'Sistem Utama'}</div>
                          </div>
                          <span style={{ fontSize: '0.75rem', fontWeight: 'bold', padding: '2px 7px', borderRadius: '4px', background: styleColor.bg, color: styleColor.text, border: `1px solid ${styleColor.border}` }}>
                            {item.health_status} ({item.health_index.toFixed(0)}%)
                          </span>
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#cbd5e1', margin: '6px 0' }}>
                          <span style={{ color: '#94a3b8' }}>Mode Anomali:</span> {item.primary_failure_mode || 'Degradasi Komponen'}
                        </div>
                        {item.rul_days && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#f59e0b', marginBottom: '10px' }}>
                            <Clock size={13} />
                            <span>Perkiraan Sisa Umur (RUL): <strong>{item.rul_days} hari</strong></span>
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border)' }}>
                        <button
                          type="button"
                          className="button button--small button--primary"
                          style={{ flex: 1, justifyContent: 'center', fontSize: '0.78rem' }}
                          onClick={() => handleQuickWo(item)}
                        >
                          <ClipboardList size={13} />
                          <span>Terbitkan WO</span>
                        </button>
                        <Link
                          to="/chat"
                          className="button button--small"
                          style={{ textDecoration: 'none', fontSize: '0.78rem' }}
                          title="Tanyakan detail diagnosa ke AI Chatbot"
                        >
                          <span>Diagnosa AI</span>
                        </Link>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Full Asset Matrix Toolbar */}
          <div className="fleet-toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', margin: '20px 0 16px', padding: '14px 18px', background: 'var(--panel)', borderRadius: '10px', border: '1px solid var(--border)' }}>
            <div style={{ position: 'relative', flex: '1 1 240px' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
              <input
                type="text"
                className="input"
                style={{ paddingLeft: '36px', width: '100%' }}
                placeholder="Cari nama peralatan, sistem, atau mode kegagalan..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Filter size={15} style={{ color: 'var(--muted)' }} />
              <select
                className="input"
                value={unitFilter}
                onChange={(e) => setUnitFilter(e.target.value)}
                style={{ width: 'auto' }}
              >
                <option value="ALL">Semua Unit</option>
                <option value="UNIT 1">Unit 1</option>
                <option value="UNIT 2">Unit 2</option>
                <option value="UNIT 3">Unit 3</option>
                <option value="COMMON">Common</option>
              </select>

              <select
                className="input"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{ width: 'auto' }}
              >
                <option value="ALL">Semua Status</option>
                <option value="HEALTHY">Healthy</option>
                <option value="WATCH">Watch</option>
                <option value="WARNING">Warning</option>
                <option value="ALERT">Alert</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>

          {/* Fleet Table */}
          <div className="fleet-table-wrapper" style={{ overflowX: 'auto', background: 'var(--panel)', borderRadius: '10px', border: '1px solid var(--border)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(255, 255, 255, 0.02)', color: 'var(--muted)' }}>
                  <th style={{ padding: '12px 16px' }}>Peralatan</th>
                  <th style={{ padding: '12px 16px' }}>Unit & Sistem</th>
                  <th style={{ padding: '12px 16px' }}>Kekritisan</th>
                  <th style={{ padding: '12px 16px' }}>Health Score</th>
                  <th style={{ padding: '12px 16px' }}>Status Fusi CBM</th>
                  <th style={{ padding: '12px 16px' }}>Mode Kegagalan</th>
                  <th style={{ padding: '12px 16px' }}>Estimasi RUL</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '36px', textAlign: 'center', color: 'var(--muted)' }}>
                      Tidak ada peralatan yang cocok dengan filter pencarian.
                    </td>
                  </tr>
                ) : (
                  filteredAssets.map((item, idx) => {
                    const statusConfig = HEALTH_COLORS[item.health_status] || HEALTH_COLORS.HEALTHY
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }} className="fleet-row">
                        <td style={{ padding: '12px 16px', fontWeight: '600', color: '#f8fafc' }}>
                          {item.equipment}
                        </td>
                        <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                          <div>{item.unit}</div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{item.system || 'Pembangkit'}</div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ fontSize: '0.78rem', padding: '2px 7px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: '#cbd5e1' }}>
                            Kelas {item.criticality || 'B'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <strong style={{ color: statusConfig.text, width: '42px' }}>
                              {item.health_index?.toFixed(1)}%
                            </strong>
                            <div style={{ width: '60px', height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                              <div style={{ width: `${Math.min(Math.max(item.health_index, 0), 100)}%`, height: '100%', background: statusConfig.text }} />
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ display: 'inline-block', fontSize: '0.78rem', fontWeight: '600', padding: '3px 8px', borderRadius: '4px', background: statusConfig.bg, color: statusConfig.text, border: `1px solid ${statusConfig.border}` }}>
                            {item.health_status}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', color: '#cbd5e1', fontSize: '0.84rem', maxWidth: '200px' }}>
                          {item.primary_failure_mode || 'Normal (Tanpa Anomali)'}
                        </td>
                        <td style={{ padding: '12px 16px', color: item.rul_days ? '#f59e0b' : '#94a3b8', fontSize: '0.84rem' }}>
                          {item.rul_days ? `${item.rul_days} hari` : 'Normal'}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <button
                            type="button"
                            className="button button--small"
                            onClick={() => handleQuickWo(item)}
                            title="Terbitkan Work Order CBM"
                          >
                            <ClipboardList size={13} />
                            <span>WO</span>
                          </button>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
