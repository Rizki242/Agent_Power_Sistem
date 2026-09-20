import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileText,
  Filter,
  HardHat,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Wrench,
  X,
} from 'lucide-react'
import { approveWorkOrder, createNewWorkOrder, getWorkOrders } from './api.js'

const PRIORITY_BADGES = {
  'P1 - Critical': { label: 'P1 - Kritis', color: 'badge--critical', border: '#ef4444' },
  'P2 - High': { label: 'P2 - Tinggi', color: 'badge--high', border: '#f97316' },
  'P3 - Medium': { label: 'P3 - Menengah', color: 'badge--medium', border: '#f59e0b' },
  'P4 - Low': { label: 'P4 - Rendah', color: 'badge--low', border: '#10b981' },
}

const LOTO_ITEMS = [
  { id: 'electrical', label: 'Isolasi Kelistrikan: Breaker Open, Rack-out, dan Terpasang Padlock & Tag Out' },
  { id: 'mechanical', label: 'Isolasi Mekanikal: Valve Inlet/Outlet Ditutup, Terkunci Rantai (Chained & Tagged)' },
  { id: 'pressure', label: 'Pelepasan Energi Tersimpan: Pressure Relieved, Jalur Pipa / Vessel Didrainase' },
  { id: 'zero_energy', label: 'Verifikasi Zero Energy: Pengujian Voltase Nol (Zero Voltage Test) Sebelum Bekerja' },
  { id: 'ppe', label: 'Kelayakan APD Spesifik: Helm Safety, Safety Shoes, Sarung Tangan, & Safety Glasses' },
]

export default function WorkOrdersWorkspace() {
  const [workOrders, setWorkOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterText, setFilterText] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [priorityFilter, setPriorityFilter] = useState('ALL')

  // Modal States
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedWo, setSelectedWo] = useState(null)
  const [lotoChecked, setLotoChecked] = useState({})
  const [approverName, setApproverName] = useState('Supervisor Pemeliharaan')
  const [actionLoading, setActionLoading] = useState(false)
  const [feedbackMsg, setFeedbackMsg] = useState(null)

  // New WO Form State
  const [newForm, setNewForm] = useState({
    equipment: '',
    title: '',
    priority: 'P3 - Medium',
    domain: 'General',
    reason: '',
    required_tools: 'Vibration Analyzer, Toolkit Mekanik',
    required_parts: 'Gasket, Bearing Grease',
    required_manpower: '2 Teknisi Pemeliharaan',
    target_completion_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
  })

  const loadData = async (signal) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getWorkOrders({}, signal)
      setWorkOrders(data.work_orders || [])
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Gagal memuat daftar Work Order')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    loadData(controller.signal)
    return () => controller.abort()
  }, [])

  // Metrics Calculation
  const metrics = useMemo(() => {
    const total = workOrders.length
    const p1 = workOrders.filter((w) => String(w.priority).includes('P1')).length
    const p2 = workOrders.filter((w) => String(w.priority).includes('P2')).length
    const draft = workOrders.filter((w) => String(w.status).toLowerCase().includes('draft') || String(w.status).toLowerCase().includes('awaiting')).length
    const inProgress = workOrders.filter((w) => String(w.status).toLowerCase().includes('progress') || String(w.status).toLowerCase().includes('approved')).length
    const completed = workOrders.filter((w) => String(w.status).toLowerCase().includes('completed') || String(w.status).toLowerCase().includes('closed')).length
    return { total, p1, p2, draft, inProgress, completed }
  }, [workOrders])

  // Filtered List
  const filteredOrders = useMemo(() => {
    return workOrders.filter((wo) => {
      const matchText =
        !filterText.trim() ||
        String(wo.wo_number || '').toLowerCase().includes(filterText.toLowerCase()) ||
        String(wo.equipment || '').toLowerCase().includes(filterText.toLowerCase()) ||
        String(wo.title || '').toLowerCase().includes(filterText.toLowerCase()) ||
        String(wo.reason || '').toLowerCase().includes(filterText.toLowerCase())

      const matchStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'DRAFT' && (String(wo.status).toLowerCase().includes('draft') || String(wo.status).toLowerCase().includes('awaiting'))) ||
        (statusFilter === 'IN_PROGRESS' && (String(wo.status).toLowerCase().includes('progress') || String(wo.status).toLowerCase().includes('approved'))) ||
        (statusFilter === 'COMPLETED' && (String(wo.status).toLowerCase().includes('complete') || String(wo.status).toLowerCase().includes('closed')))

      const matchPriority =
        priorityFilter === 'ALL' || String(wo.priority || '').startsWith(priorityFilter)

      return matchText && matchStatus && matchPriority
    })
  }, [workOrders, filterText, statusFilter, priorityFilter])

  // Handle Approve / Complete / Reject
  const handleApprovalAction = async (actionType) => {
    if (!selectedWo) return

    // Require LOTO confirmation for approval
    if (actionType === 'Approve') {
      const allChecked = LOTO_ITEMS.every((item) => lotoChecked[item.id])
      if (!allChecked) {
        alert('Mohon verifikasi dan centang seluruh 5 persyaratan LOTO & Keselamatan Kerja sebelum menyetujui Work Order.')
        return
      }
    }

    setActionLoading(true)
    try {
      await approveWorkOrder({
        woNumber: selectedWo.wo_number,
        approvedBy: approverName.trim() || 'Supervisor Pemeliharaan',
        action: actionType,
      })
      setFeedbackMsg({
        type: 'success',
        text: `Work Order ${selectedWo.wo_number} berhasil diproses: ${actionType}!`,
      })
      setSelectedWo(null)
      setLotoChecked({})
      loadData()
    } catch (err) {
      alert(`Gagal memproses Work Order: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  // Handle Create New WO
  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    if (!newForm.equipment.trim() || !newForm.title.trim()) {
      alert('Peralatan dan Judul Pekerjaan wajib diisi.')
      return
    }

    setActionLoading(true)
    try {
      const tools = newForm.required_tools.split(',').map((s) => s.trim()).filter(Boolean)
      const parts = newForm.required_parts.split(',').map((s) => s.trim()).filter(Boolean)

      await createNewWorkOrder({
        equipment: newForm.equipment.trim(),
        title: newForm.title.trim(),
        priority: newForm.priority,
        domain: newForm.domain,
        reason: newForm.reason.trim(),
        required_tools: tools,
        required_parts: parts,
        required_manpower: newForm.required_manpower.trim(),
        target_completion_date: newForm.target_completion_date,
        created_by: 'Engineer CBM (React UI)',
      })

      setFeedbackMsg({
        type: 'success',
        text: `Work Order baru untuk ${newForm.equipment} berhasil diterbitkan!`,
      })
      setIsCreateOpen(false)
      setNewForm({
        equipment: '',
        title: '',
        priority: 'P3 - Medium',
        domain: 'General',
        reason: '',
        required_tools: 'Vibration Analyzer, Toolkit Mekanik',
        required_parts: 'Gasket, Bearing Grease',
        required_manpower: '2 Teknisi Pemeliharaan',
        target_completion_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
      })
      loadData()
    } catch (err) {
      alert(`Gagal membuat Work Order: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  // Copy Briefing to Clipboard
  const handleCopyBriefing = (wo) => {
    const text = `*DISPATCH WORK ORDER CBM - PLTU JERANJANG*
No. WO: ${wo.wo_number}
Form: FORM.JRG.F.05.006 (Rev 01)
Peralatan: ${wo.equipment}
Prioritas: ${wo.priority}
Judul: ${wo.title}
Alasan/Temuan: ${wo.reason || '-'}
Alat Kerja: ${(wo.required_tools || []).join(', ') || '-'}
Spare Parts: ${(wo.required_parts || []).join(', ') || '-'}
Personel: ${wo.required_manpower || '-'}
Target Selesai: ${wo.target_completion_date || '-'}
Status: ${wo.status}`

    navigator.clipboard.writeText(text)
    alert(`Ringkasan briefing untuk ${wo.wo_number} berhasil disalin ke clipboard! Siap dikirim ke tim lapangan.`)
  }

  return (
    <div className="page work-orders-workspace">
      {/* Header */}
      <header className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span className="domain-pill" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              FORM.JRG.F.05.006 (Rev 01)
            </span>
            <span style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>PT INDONESIA POWER UJP JERANJANG</span>
          </div>
          <h1>Manajemen Work Order CBM</h1>
          <p>Tindak lanjut pemeliharaan berbasis kondisi (PdM/CBM), verifikasi isolasi LOTO, dan dispatch tiket lapangan.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            className="button"
            onClick={() => loadData()}
            disabled={loading}
            title="Muat ulang daftar"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            <span>Muat Ulang</span>
          </button>
          <button
            type="button"
            className="button button--primary"
            onClick={() => setIsCreateOpen(true)}
          >
            <Plus size={16} />
            <span>Terbitkan WO Baru</span>
          </button>
        </div>
      </header>

      {feedbackMsg && (
        <div className={`notice notice--${feedbackMsg.type}`} style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CheckCircle2 size={18} />
            <span>{feedbackMsg.text}</span>
          </div>
          <button type="button" className="icon-button" onClick={() => setFeedbackMsg(null)} aria-label="Tutup">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Metrics Banner */}
      <section className="overview-strip" aria-label="Ringkasan Work Orders" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
        <div>
          <span>Total Work Order</span>
          <strong>{metrics.total}</strong>
        </div>
        <div>
          <span style={{ color: '#ef4444' }}>P1 - Critical</span>
          <strong style={{ color: '#ef4444' }}>{metrics.p1}</strong>
        </div>
        <div>
          <span style={{ color: '#f97316' }}>P2 - High</span>
          <strong style={{ color: '#f97316' }}>{metrics.p2}</strong>
        </div>
        <div>
          <span style={{ color: '#f59e0b' }}>Awaiting Approval</span>
          <strong style={{ color: '#f59e0b' }}>{metrics.draft}</strong>
        </div>
        <div>
          <span style={{ color: '#3b82f6' }}>In Progress</span>
          <strong style={{ color: '#3b82f6' }}>{metrics.inProgress}</strong>
        </div>
        <div>
          <span style={{ color: '#10b981' }}>Completed</span>
          <strong style={{ color: '#10b981' }}>{metrics.completed}</strong>
        </div>
      </section>

      {/* Filters Toolbar */}
      <div className="wo-toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', margin: '20px 0 16px', padding: '14px 18px', background: 'var(--panel)', borderRadius: '10px', border: '1px solid var(--border)' }}>
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input
            type="text"
            className="input"
            style={{ paddingLeft: '36px', width: '100%' }}
            placeholder="Cari No. WO, peralatan, KKS, atau deskripsi..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <Filter size={15} style={{ color: 'var(--muted)' }} />
          <select
            className="input"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="ALL">Semua Status</option>
            <option value="DRAFT">Draft / Menunggu Approval</option>
            <option value="IN_PROGRESS">Approved / In Progress</option>
            <option value="COMPLETED">Completed / Closed</option>
          </select>

          <select
            className="input"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="ALL">Semua Prioritas</option>
            <option value="P1">P1 - Critical</option>
            <option value="P2">P2 - High</option>
            <option value="P3">P3 - Medium</option>
            <option value="P4">P4 - Low</option>
          </select>
        </div>
      </div>

      {/* Table / List */}
      {loading ? (
        <div className="empty-state" style={{ minHeight: '300px' }}>
          <div className="chat-typing-indicator"><span /><span /><span /></div>
          <span>Memuat data Work Order...</span>
        </div>
      ) : error ? (
        <div className="notice notice--error">
          <strong>Gagal Memuat Data</strong>
          <span>{error}</span>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="empty-state" style={{ padding: '48px 24px', textAlign: 'center', background: 'var(--panel)', borderRadius: '12px', border: '1px dashed var(--border)' }}>
          <ClipboardList size={38} style={{ opacity: 0.5, marginBottom: '12px' }} />
          <strong>Tidak ada Work Order yang cocok</strong>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>Coba ubah filter pencarian atau buat Work Order baru.</p>
        </div>
      ) : (
        <div className="wo-table-wrapper" style={{ overflowX: 'auto', background: 'var(--panel)', borderRadius: '10px', border: '1px solid var(--border)' }}>
          <table className="wo-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(255, 255, 255, 0.02)', color: 'var(--muted)' }}>
                <th style={{ padding: '12px 16px' }}>No. WO</th>
                <th style={{ padding: '12px 16px' }}>Peralatan</th>
                <th style={{ padding: '12px 16px' }}>Prioritas</th>
                <th style={{ padding: '12px 16px' }}>Pekerjaan & Temuan</th>
                <th style={{ padding: '12px 16px' }}>Target Selesai</th>
                <th style={{ padding: '12px 16px' }}>Status</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((wo) => {
                const priorityInfo = PRIORITY_BADGES[wo.priority] || { label: wo.priority || 'Normal', border: '#64748b' }
                const isDraft = String(wo.status).toLowerCase().includes('draft') || String(wo.status).toLowerCase().includes('awaiting')
                const isInProgress = String(wo.status).toLowerCase().includes('progress') || String(wo.status).toLowerCase().includes('approved')
                const isCompleted = String(wo.status).toLowerCase().includes('complete') || String(wo.status).toLowerCase().includes('closed')

                return (
                  <tr key={wo.wo_number} style={{ borderBottom: '1px solid var(--border)' }} className="wo-row">
                    <td style={{ padding: '14px 16px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                      <strong style={{ color: '#60a5fa', fontFamily: 'monospace', fontSize: '0.95rem' }}>{wo.wo_number}</strong>
                      <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: '2px' }}>{wo.created_at || '-'}</div>
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                      <strong style={{ fontSize: '0.95rem', color: '#f8fafc' }}>{wo.equipment}</strong>
                      <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                        <span className="tag-source">{wo.domain || 'CBM'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.78rem',
                          fontWeight: '600',
                          border: `1px solid ${priorityInfo.border}`,
                          color: priorityInfo.border,
                          background: `${priorityInfo.border}18`,
                        }}
                      >
                        {wo.priority}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top', maxWidth: '320px' }}>
                      <div style={{ fontWeight: '600', color: '#f1f5f9', marginBottom: '4px' }}>{wo.title}</div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--muted)', lineHeight: '1.4' }}>
                        {wo.reason || 'Pekerjaan pemeliharaan preventif/korektif.'}
                      </div>
                      {wo.required_tools && wo.required_tools.length > 0 && (
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
                          🔧 <strong>Alat:</strong> {wo.required_tools.join(', ')}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top', whiteSpace: 'nowrap', color: '#cbd5e1' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} style={{ color: 'var(--muted)' }} />
                        <span>{wo.target_completion_date || '-'}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px' }}>
                        {wo.required_manpower || '1 Teknisi'}
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '4px 9px',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          fontWeight: '500',
                          background: isDraft
                            ? 'rgba(245, 158, 11, 0.12)'
                            : isInProgress
                            ? 'rgba(59, 130, 246, 0.12)'
                            : isCompleted
                            ? 'rgba(16, 185, 129, 0.12)'
                            : 'rgba(239, 68, 68, 0.12)',
                          color: isDraft
                            ? '#f59e0b'
                            : isInProgress
                            ? '#60a5fa'
                            : isCompleted
                            ? '#34d399'
                            : '#f87171',
                          border: `1px solid ${
                            isDraft
                              ? 'rgba(245, 158, 11, 0.3)'
                              : isInProgress
                              ? 'rgba(59, 130, 246, 0.3)'
                              : isCompleted
                              ? 'rgba(16, 185, 129, 0.3)'
                              : 'rgba(239, 68, 68, 0.3)'
                          }`,
                        }}
                      >
                        {isDraft && <AlertTriangle size={13} />}
                        {isInProgress && <Wrench size={13} />}
                        {isCompleted && <CheckCircle2 size={13} />}
                        <span>{wo.status}</span>
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', verticalAlign: 'top', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="button button--small"
                          onClick={() => setSelectedWo(wo)}
                          title="Tinjau LOTO & Persetujuan"
                        >
                          <HardHat size={14} />
                          <span>Detail & LOTO</span>
                        </button>
                        <button
                          type="button"
                          className="button button--small"
                          onClick={() => handleCopyBriefing(wo)}
                          title="Salin Format Briefing Lapangan"
                        >
                          <FileText size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* MODAL: LOTO & Work Order Approval */}
      {selectedWo && (
        <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999, padding: '16px' }}>
          <div className="modal-card" style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', width: '100%', maxWidth: '680px', maxHeight: '90vh', overflowY: 'auto', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #334155', paddingBottom: '16px', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <HardHat size={20} style={{ color: '#f59e0b' }} />
                  <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#f8fafc' }}>
                    Verifikasi LOTO & Pengesahan WO
                  </h3>
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
                  No. Dokumen: <strong>FORM.JRG.F.05.006 (Rev 01)</strong> | {selectedWo.wo_number}
                </div>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setSelectedWo(null)}
                aria-label="Tutup"
              >
                <X size={18} />
              </button>
            </div>

            {/* Equipment & Task Info Card */}
            <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', marginBottom: '20px', borderLeft: '4px solid #38bdf8' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.88rem' }}>
                <div>
                  <span style={{ color: '#94a3b8' }}>Peralatan:</span>{' '}
                  <strong style={{ color: '#f8fafc' }}>{selectedWo.equipment}</strong>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Prioritas:</span>{' '}
                  <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>{selectedWo.priority}</span>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Domain CBM:</span>{' '}
                  <span style={{ color: '#38bdf8' }}>{selectedWo.domain || 'Multi-Agent'}</span>
                </div>
                <div>
                  <span style={{ color: '#94a3b8' }}>Target Selesai:</span>{' '}
                  <span style={{ color: '#f1f5f9' }}>{selectedWo.target_completion_date || '-'}</span>
                </div>
              </div>
              <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <strong style={{ color: '#f8fafc', fontSize: '0.95rem' }}>{selectedWo.title}</strong>
                <p style={{ margin: '4px 0 0', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.4' }}>
                  {selectedWo.reason || 'Pemeriksaan lanjutan hasil diagnosa CBM.'}
                </p>
              </div>
            </div>

            {/* LOTO Safety Verification Section */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <ShieldCheck size={18} style={{ color: '#10b981' }} />
                <h4 style={{ margin: 0, fontSize: '0.98rem', color: '#f1f5f9' }}>
                  Prosedur Isolasi Energi & Keselamatan (LOTO Checklist)
                </h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', background: 'rgba(0,0,0,0.2)', padding: '14px', borderRadius: '8px', border: '1px solid #334155' }}>
                {LOTO_ITEMS.map((item) => (
                  <label
                    key={item.id}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                      fontSize: '0.85rem',
                      color: lotoChecked[item.id] ? '#f8fafc' : '#94a3b8',
                      cursor: 'pointer',
                      userSelect: 'none',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(lotoChecked[item.id])}
                      onChange={(e) =>
                        setLotoChecked((prev) => ({ ...prev, [item.id]: e.target.checked }))
                      }
                      style={{ marginTop: '3px' }}
                    />
                    <span>{item.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Approver Name Input */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                Nama Supervisor / Approver Resmi:
              </label>
              <input
                type="text"
                className="input"
                style={{ width: '100%' }}
                value={approverName}
                onChange={(e) => setApproverName(e.target.value)}
                placeholder="Contoh: Budi Santoso (Supervisor Pemeliharaan Mesin)"
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'flex-end', borderTop: '1px solid #334155', paddingTop: '16px' }}>
              <button
                type="button"
                className="button"
                onClick={() => setSelectedWo(null)}
                disabled={actionLoading}
              >
                Batal
              </button>
              <button
                type="button"
                className="button"
                style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid rgba(239,68,68,0.4)' }}
                onClick={() => handleApprovalAction('Reject')}
                disabled={actionLoading}
              >
                Tolak WO
              </button>
              <button
                type="button"
                className="button"
                style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16,185,129,0.4)' }}
                onClick={() => handleApprovalAction('Complete')}
                disabled={actionLoading}
              >
                Tandai Pekerjaan Selesai
              </button>
              <button
                type="button"
                className="button button--primary"
                onClick={() => handleApprovalAction('Approve')}
                disabled={actionLoading}
              >
                <CheckCircle2 size={16} />
                <span>{actionLoading ? 'Memproses...' : 'Setujui & Terbitkan Izin LOTO'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Create New Work Order */}
      {isCreateOpen && (
        <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999, padding: '16px' }}>
          <div className="modal-card" style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', width: '100%', maxWidth: '640px', maxHeight: '90vh', overflowY: 'auto', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #334155', paddingBottom: '14px', marginBottom: '20px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#f8fafc' }}>
                  Terbitkan Work Order CBM Baru
                </h3>
                <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
                  Form Standar TE IMS PLTU Jeranjang FORM.JRG.F.05.006 (Rev 01)
                </p>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setIsCreateOpen(false)}
                aria-label="Tutup"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Peralatan / KKS *:
                  </label>
                  <input
                    type="text"
                    className="input"
                    required
                    style={{ width: '100%' }}
                    placeholder="Contoh: BFP 1A atau CWP 1B"
                    value={newForm.equipment}
                    onChange={(e) => setNewForm({ ...newForm, equipment: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Domain / Spesialisasi:
                  </label>
                  <select
                    className="input"
                    style={{ width: '100%' }}
                    value={newForm.domain}
                    onChange={(e) => setNewForm({ ...newForm, domain: e.target.value })}
                  >
                    <option value="Vibrasi">Vibrasi (ISO 10816-3)</option>
                    <option value="MCSA">MCSA / Kelistrikan Motor</option>
                    <option value="DGA">DGA Trafo (IEEE C57.104)</option>
                    <option value="Tribologi">Tribologi / Pelumasan</option>
                    <option value="Thermal">Thermal Thermography</option>
                    <option value="Partial Discharge">Partial Discharge</option>
                    <option value="General">General Maintenance</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                  Judul Pekerjaan Pemeliharaan *:
                </label>
                <input
                  type="text"
                  className="input"
                  required
                  style={{ width: '100%' }}
                  placeholder="Contoh: Investigasi Spektrum 2X & Laser Alignment Re-check"
                  value={newForm.title}
                  onChange={(e) => setNewForm({ ...newForm, title: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Tingkat Prioritas:
                  </label>
                  <select
                    className="input"
                    style={{ width: '100%' }}
                    value={newForm.priority}
                    onChange={(e) => setNewForm({ ...newForm, priority: e.target.value })}
                  >
                    <option value="P1 - Critical">P1 - Critical (24 Jam)</option>
                    <option value="P2 - High">P2 - High (3 Hari)</option>
                    <option value="P3 - Medium">P3 - Medium (7 Hari)</option>
                    <option value="P4 - Low">P4 - Low (Jadwal Rutin)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Target Selesai:
                  </label>
                  <input
                    type="date"
                    className="input"
                    style={{ width: '100%' }}
                    value={newForm.target_completion_date}
                    onChange={(e) => setNewForm({ ...newForm, target_completion_date: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                  Alasan Teknis / Temuan Diagnosa AI:
                </label>
                <textarea
                  className="input"
                  rows={3}
                  style={{ width: '100%', resize: 'vertical' }}
                  placeholder="Jelaskan alasan penerbitan WO berdasarkan temuan sensor / anomali CBM..."
                  value={newForm.reason}
                  onChange={(e) => setNewForm({ ...newForm, reason: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Alat Kerja (Tools, pisahkan koma):
                  </label>
                  <input
                    type="text"
                    className="input"
                    style={{ width: '100%' }}
                    placeholder="Vibration Analyzer, Dial Indicator, dll"
                    value={newForm.required_tools}
                    onChange={(e) => setNewForm({ ...newForm, required_tools: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                    Suku Cadang / Material (pisahkan koma):
                  </label>
                  <input
                    type="text"
                    className="input"
                    style={{ width: '100%' }}
                    placeholder="Grease Shell Gadus, Shim pack, dll"
                    value={newForm.required_parts}
                    onChange={(e) => setNewForm({ ...newForm, required_parts: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>
                  Alokasi Tim Personel:
                </label>
                <input
                  type="text"
                  className="input"
                  style={{ width: '100%' }}
                  placeholder="Contoh: 1 Spesialis Vibrasi + 2 Teknisi Mekanik"
                  value={newForm.required_manpower}
                  onChange={(e) => setNewForm({ ...newForm, required_manpower: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px', borderTop: '1px solid #334155', paddingTop: '16px' }}>
                <button
                  type="button"
                  className="button"
                  onClick={() => setIsCreateOpen(false)}
                  disabled={actionLoading}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="button button--primary"
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Menerbitkan...' : 'Terbitkan Work Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
