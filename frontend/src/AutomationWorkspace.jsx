import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clock3,
  Download,
  FileSpreadsheet,
  FileText,
  Layers,
  Play,
  Plus,
  Presentation,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Workflow,
  X,
  Zap,
} from 'lucide-react'
import {
  approveAutomationRun,
  createAutomationWorkflow,
  getAutomatedReportsSummary,
  getAutomationWorkspace,
  getMeetingPptxDownloadUrl,
  getMonthlyModuleReportDownloadUrl,
  getMonthlyReportDownloadUrl,
  getWeeklyReportDownloadUrl,
  retryAutomationRun,
  runAutomation,
  setAutomationEnabled,
} from './api.js'

const EMPTY = { workflows: [], runs: [] }
const actionNames = {
  learning_cycle: 'Siklus pembelajaran agent',
  knowledge_health_check: 'Pemeriksaan knowledge index',
}

const CBM_MODULES_INFO = [
  { id: 'MCSA', name: 'MCSA (Motor Current Signature)', desc: 'Rotor bar sideband, deviasi arus/tegangan, THD motor 6.3 kV dan 380V.', color: '#10b981', day: 'Senin' },
  { id: 'VIBRASI', name: 'Vibrasi Mekanikal', desc: 'Spektrum 1X/2X, unbalance, misalignment, bearing fault, ISO 10816-3.', color: '#38bdf8', day: 'Selasa' },
  { id: 'DGA', name: 'DGA (Gas Terlarut Trafo)', desc: 'Dissolved Gas Analysis, Duval Triangle 1, Rogers Ratios, IEEE C57.104.', color: '#ec4899', day: 'Rabu' },
  { id: 'PD', name: 'Partial Discharge (PD)', desc: 'Inspeksi peluahan sebagian isolasi stator generator & switchgear (IEC 60270).', color: '#a855f7', day: 'Kamis' },
  { id: 'TRIBOLOGY', name: 'Tribologi & Pelumas', desc: 'Viskositas ASTM D445, TAN, kadar air Karl Fischer, partikel aus ISO 4406.', color: '#f59e0b', day: 'Jumat' },
  { id: 'THERMAL', name: 'Thermal IRT (Suhu & Hotspot)', desc: 'Pemetaan termografi inframerah & evaluasi matriks Delta-T (ISO 18434-1).', color: '#ef4444', day: 'Sabtu' },
]

function RunStatus({ status }) {
  return (
    <span className={`run-status run-status--${status.toLowerCase()}`}>
      <i />
      {status.replaceAll('_', ' ')}
    </span>
  )
}

function WorkflowBuilder({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    action: 'knowledge_health_check',
    interval_minutes: 60,
    approval_required: true,
  })
  const [state, setState] = useState({ status: 'idle', message: '' })

  async function submit(event) {
    event.preventDefault()
    setState({ status: 'saving', message: '' })
    try {
      const result = await createAutomationWorkflow({
        ...form,
        interval_minutes: Number(form.interval_minutes),
      })
      onCreated(result.workflow)
    } catch (error) {
      setState({ status: 'error', message: error.message })
    }
  }

  return (
    <aside className="automation-builder" aria-label="Buat workflow">
      <div className="config-panel__header">
        <div>
          <span>Workflow builder</span>
          <h2>Buat otomasi</h2>
          <p>Susun trigger dan aksi dengan approval yang eksplisit.</p>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Tutup workflow builder">
          <X />
        </button>
      </div>
      <div className="workflow-preview">
        <span><CalendarClock size={17} />Trigger</span>
        <ChevronRight />
        <span><Zap size={17} />Action</span>
        <ChevronRight />
        <span><ShieldCheck size={17} />Approval</span>
        <ChevronRight />
        <span><Check size={17} />Result</span>
      </div>
      <form className="upload-form" onSubmit={submit}>
        <label className="form-field">
          <span>Nama workflow</span>
          <input
            required
            minLength={3}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Contoh: Audit knowledge mingguan"
          />
        </label>
        <label className="form-field">
          <span>Action</span>
          <select
            value={form.action}
            onChange={(e) => setForm({ ...form, action: e.target.value })}
          >
            <option value="knowledge_health_check">Pemeriksaan knowledge index</option>
            <option value="learning_cycle">Siklus pembelajaran agent</option>
          </select>
        </label>
        <label className="form-field">
          <span>Interval</span>
          <select
            value={form.interval_minutes}
            onChange={(e) => setForm({ ...form, interval_minutes: e.target.value })}
          >
            <option value="30">Setiap 30 menit</option>
            <option value="60">Setiap jam</option>
            <option value="1440">Setiap hari</option>
            <option value="10080">Setiap minggu</option>
          </select>
        </label>
        <label className="approval-choice">
          <input
            type="checkbox"
            checked={form.approval_required}
            onChange={(e) => setForm({ ...form, approval_required: e.target.checked })}
          />
          <span>
            <strong>Wajib approval manusia</strong>
            <small>Run berhenti sebelum action sampai engineer menyetujui.</small>
          </span>
        </label>
        {state.message ? (
          <div className="upload-message upload-message--error">
            <CircleAlert size={17} />{state.message}
          </div>
        ) : null}
        <button className="button button--primary" disabled={state.status === 'saving'}>
          {state.status === 'saving' ? 'Menyimpan...' : 'Simpan workflow'}
        </button>
      </form>
    </aside>
  )
}

export default function AutomationWorkspace() {
  const [activeTab, setActiveTab] = useState('reports') // 'reports' | 'workflows'
  const [data, setData] = useState(EMPTY)
  const [reportSummary, setReportSummary] = useState(null)
  const [status, setStatus] = useState('loading')
  const [builder, setBuilder] = useState(false)
  const [message, setMessage] = useState('')

  function loadWorkflows() {
    const controller = new AbortController()
    getAutomationWorkspace(controller.signal)
      .then((result) => {
        setData(result)
      })
      .catch(() => {})
    return controller
  }

  function loadReportSummary() {
    const controller = new AbortController()
    getAutomatedReportsSummary(controller.signal)
      .then((result) => {
        setReportSummary(result)
        setStatus('ready')
      })
      .catch(() => {
        setStatus('error')
      })
    return controller
  }

  useEffect(() => {
    const c1 = loadWorkflows()
    const c2 = loadReportSummary()
    return () => {
      c1.abort()
      c2.abort()
    }
  }, [])

  async function toggle(item) {
    await setAutomationEnabled(item.id, !item.enabled)
    loadWorkflows()
  }

  async function run(item) {
    try {
      const result = await runAutomation(item.id)
      setMessage(
        result.run.status === 'WAITING_APPROVAL'
          ? 'Run dibuat dan menunggu approval engineer.'
          : 'Workflow selesai dijalankan.'
      )
      loadWorkflows()
    } catch {
      setMessage('Workflow gagal dimulai.')
    }
  }

  async function approve(runItem) {
    const name = window.prompt('Nama engineer yang menyetujui')
    if (!name?.trim()) return
    await approveAutomationRun(runItem.id, name.trim())
    loadWorkflows()
  }

  async function retry(runItem) {
    await retryAutomationRun(runItem.id)
    loadWorkflows()
  }

  const pending = data.runs.filter((item) => item.status === 'WAITING_APPROVAL').length

  return (
    <div className="page automation-page">
      <header className="page-header">
        <div>
          <h1>Otomasi & Laporan Keandalan</h1>
          <p>Jadwal otomatisasi laporan mingguan, bulanan seluruh modul CBM, dan siklus pembelajaran agent.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`button ${activeTab === 'reports' ? 'button--primary' : 'button--ghost'}`}
            onClick={() => setActiveTab('reports')}
          >
            <Presentation size={18} />
            Otomasi Laporan & Meeting PPTX
          </button>
          <button
            className={`button ${activeTab === 'workflows' ? 'button--primary' : 'button--ghost'}`}
            onClick={() => setActiveTab('workflows')}
          >
            <Workflow size={18} />
            Workflow & Scheduler
          </button>
          {activeTab === 'workflows' ? (
            <button className="button button--primary" onClick={() => setBuilder(true)}>
              <Plus size={18} />
              Buat otomasi
            </button>
          ) : null}
        </div>
      </header>

      {message ? (
        <div className="notice notice--success">
          <Check size={17} />{message}
        </div>
      ) : null}

      {activeTab === 'reports' ? (
        <div className="automated-reports-view">
          {/* Status Kesiapan 6 Modul CBM September 2026 */}
          <section className="cbm-status-banner card-panel">
            <div className="cbm-status-banner__header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Layers className="text-accent" size={24} />
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
                    Matriks Kesiapan 6 Modul CBM — {reportSummary?.current_sample_month || 'September 2026'}
                  </h2>
                  <small style={{ color: 'var(--muted)' }}>
                    {reportSummary?.plant || 'PLTU Jeranjang (3 × 25 MW)'} | Periode Pelaporan Aktif
                  </small>
                </div>
              </div>
              <a
                href={getMeetingPptxDownloadUrl(2026, 9)}
                className="button button--primary"
                download
              >
                <Presentation size={17} />
                Unduh Slide Deck Meeting PPTX
              </a>
            </div>

            <div className="module-badges-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px', marginTop: '16px' }}>
              {reportSummary?.modules_status_september_2026?.map((mod) => (
                <div
                  key={mod.domain}
                  className={`module-status-chip ${mod.has_data ? 'module-status-chip--active' : 'module-status-chip--standby'}`}
                  style={{
                    padding: '14px 16px',
                    borderRadius: '8px',
                    border: mod.has_data ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)',
                    background: mod.has_data ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '1.05rem', color: 'var(--ink)' }}>
                      {mod.domain}
                    </strong>
                    {mod.has_data ? (
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--healthy)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={14} /> AKTIF DIUJI
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--attention)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={14} /> STANDBY
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
                    {mod.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Data: <strong>{mod.reading_count}</strong> uji</span>
                    <span>Equipment: <strong>{mod.equipment_count}</strong> unit</span>
                  </div>
                  {!mod.has_data ? (
                    <div style={{ marginTop: '6px', fontSize: '0.75rem', color: 'var(--attention)', background: 'rgba(245, 158, 11, 0.15)', padding: '4px 8px', borderRadius: '4px' }}>
                      ⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          {/* Section 1: Contoh Laporan Mingguan Per Modul (6 Modul Penuh) */}
          <section style={{ marginTop: '28px' }}>
            <div className="section-heading">
              <div>
                <h2>1. Otomatisasi Contoh Laporan Mingguan (Weekly Reports — 6 Modul CBM)</h2>
                <p>Jadwal rutin mingguan per modul teknis (MCSA, Vibrasi Mekanikal, DGA, PD, Tribologi, dan Thermal).</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginTop: '12px' }}>
              {CBM_MODULES_INFO.map((mod) => (
                <div
                  key={`weekly-${mod.id}`}
                  className="report-card"
                  style={{
                    padding: '20px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Activity size={20} style={{ color: mod.color }} />
                        <h3 style={{ margin: 0, fontSize: '1.05rem' }}>{mod.name}</h3>
                      </div>
                      <span style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', color: 'var(--muted)' }}>
                        Setiap {mod.day}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginBottom: '12px' }}>
                      {mod.desc}
                    </p>
                    <div style={{ fontSize: '0.78rem', marginBottom: '16px', color: 'var(--muted)' }}>
                      <span>Periode: <strong>Minggu ke-3 (15 - 21 September 2026)</strong></span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                    <a
                      href={getWeeklyReportDownloadUrl(mod.id, 'docx', 3)}
                      className="button button--small button--ghost"
                      download
                    >
                      <FileText size={15} /> Unduh DOCX
                    </a>
                    <a
                      href={getWeeklyReportDownloadUrl(mod.id, 'pptx', 3)}
                      className="button button--small button--ghost"
                      download
                    >
                      <Presentation size={15} /> Unduh PPTX
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 2: Contoh Laporan Bulanan Per Modul (6 Modul Penuh) */}
          <section style={{ marginTop: '28px' }}>
            <div className="section-heading">
              <div>
                <h2>2. Otomatisasi Laporan Bulanan Per Modul (Monthly Module Reports — 6 Modul CBM)</h2>
                <p>Ringkasan evaluasi bulanan spesifik per masing-masing modul teknis untuk periode September 2026.</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginTop: '12px' }}>
              {CBM_MODULES_INFO.map((mod) => (
                <div
                  key={`monthly-mod-${mod.id}`}
                  className="report-card"
                  style={{
                    padding: '20px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Layers size={20} style={{ color: mod.color }} />
                        <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Bulanan: {mod.name}</h3>
                      </div>
                      <span style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', color: 'var(--muted)' }}>
                        Akhir Bulan
                      </span>
                    </div>
                    <p style={{ fontSize: '0.83rem', color: 'var(--muted)', marginBottom: '12px' }}>
                      Evaluasi bulanan {mod.name}: verifikasi tren parameter dan rekomendasi pemeliharaan prediktif.
                    </p>
                    <div style={{ fontSize: '0.78rem', marginBottom: '16px', color: 'var(--muted)' }}>
                      <span>Periode: <strong>01 - 30 September 2026</strong></span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                    <a
                      href={getMonthlyModuleReportDownloadUrl(mod.id, 'docx', 2026, 9)}
                      className="button button--small button--ghost"
                      download
                    >
                      <FileText size={15} /> Unduh DOCX
                    </a>
                    <a
                      href={getMonthlyModuleReportDownloadUrl(mod.id, 'pptx', 2026, 9)}
                      className="button button--small button--ghost"
                      download
                    >
                      <Presentation size={15} /> Unduh PPTX
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 3: Laporan Bulanan Terpadu & Asset Management September 2026 */}
          <section style={{ marginTop: '28px' }}>
            <div className="section-heading">
              <div>
                <h2>3. Laporan Bulanan Terpadu Seluruh Modul / Asset Management CBM PLTU Jeranjang</h2>
                <p>Konsolidasi 6 modul CBM periode September 2026 (dengan penanda visual modul standby).</p>
              </div>
            </div>

            <div
              style={{
                padding: '24px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%)',
                marginTop: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ background: 'var(--action)', color: 'var(--on-accent)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                    EDISI LENGKAP 360°
                  </span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>September 2026</span>
                </div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: '1.25rem' }}>
                  Laporan Asset Management & Condition-Based Maintenance PLTU Jeranjang
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)', maxWidth: '640px' }}>
                  Memuat data lengkap dari modul aktif (MCSA, Vibrasi, DGA, Thermal) dan penanda tegas{' '}
                  <code style={{ color: 'var(--attention)' }}>⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY]</code> untuk modul tanpa pengujian di bulan September 2026.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <a
                  href={getMonthlyReportDownloadUrl('docx', 2026, 9)}
                  className="button button--primary"
                  download
                >
                  <Download size={16} /> Unduh Word (.docx)
                </a>
                <a
                  href={getMonthlyReportDownloadUrl('pptx', 2026, 9)}
                  className="button button--ghost"
                  download
                >
                  <Presentation size={16} /> Unduh Slide (.pptx)
                </a>
                <a
                  href={getMonthlyReportDownloadUrl('csv', 2026, 9)}
                  className="button button--ghost"
                  download
                >
                  <FileSpreadsheet size={16} /> Unduh Data (.csv)
                </a>
              </div>
            </div>
          </section>

          {/* Section 3: Meeting PPTX Showcase */}
          <section style={{ marginTop: '28px', marginBottom: '40px' }}>
            <div className="section-heading">
              <div>
                <h2>3. Slide Deck Meeting Koordinasi Keandalan CBM</h2>
                <p>Presentasi eksekutif siap pakai untuk rapat bulanan keandalan pembangkit.</p>
              </div>
            </div>

            <div
              style={{
                padding: '24px',
                borderRadius: '8px',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                background: 'rgba(59, 130, 246, 0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ background: 'var(--action)', color: 'var(--on-accent)', padding: '16px', borderRadius: '12px' }}>
                  <Presentation size={32} />
                </div>
                <div>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '1.15rem' }}>
                    Slide Deck Meeting Keandalan CBM PLTU Jeranjang — September 2026
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.85rem', color: 'var(--muted)' }}>
                    <li>Slide 1: Cover Eksekutif Rapat Keandalan Pembangkit</li>
                    <li>Slide 2: Matriks Kesiapan 6 Modul CBM (Tabel Modul, Status, Jml Pengujian)</li>
                    <li>Slide 3-8: Evaluasi per Modul (dengan tanda visual khusus untuk modul Standby)</li>
                    <li>Slide 9: Keputusan Tindak Lanjut & Rekomendasi Work Order CBM</li>
                  </ul>
                </div>
              </div>
              <a
                href={getMeetingPptxDownloadUrl(2026, 9)}
                className="button button--primary"
                style={{ padding: '12px 20px', fontSize: '0.95rem' }}
                download
              >
                <Download size={18} /> Unduh Meeting PPTX Sekarang
              </a>
            </div>
          </section>
        </div>
      ) : (
        <div className="workflows-view">
          <section className="automation-summary">
            <div>
              <Workflow size={19} />
              <span>Workflow</span>
              <strong>{status === 'ready' ? data.workflows.length : '—'}</strong>
            </div>
            <div>
              <Play size={19} />
              <span>Run tercatat</span>
              <strong>{status === 'ready' ? data.runs.length : '—'}</strong>
            </div>
            <div>
              <ShieldCheck size={19} />
              <span>Menunggu approval</span>
              <strong>{status === 'ready' ? pending : '—'}</strong>
            </div>
            <div>
              <Clock3 size={19} />
              <span>Scheduler</span>
              <strong>Daemon lokal</strong>
            </div>
          </section>

          <div className="scheduler-note">
            <CircleAlert size={17} />
            <span>
              Jadwal disimpan, tetapi eksekusi periodik memerlukan daemon lokal <code>src/agent_cron.py</code>.
              Tombol Jalankan tetap tersedia dari workspace.
            </span>
          </div>

          <div className="automation-grid">
            <section className="workflow-list-panel">
              <div className="section-heading">
                <div>
                  <h2>Workflow</h2>
                  <p>Trigger → action → approval → result</p>
                </div>
                <button className="icon-button" onClick={() => loadWorkflows()} aria-label="Muat ulang otomasi">
                  <RefreshCw size={18} />
                </button>
              </div>
              <div className="workflow-list">
                {data.workflows.map((item) => (
                  <article className="workflow-row" key={item.id}>
                    <div className="workflow-row__top">
                      <div className="workflow-symbol">
                        <Workflow size={18} />
                      </div>
                      <div>
                        <strong>{item.name}</strong>
                        <span>{actionNames[item.action]}</span>
                      </div>
                      <label className="mini-switch">
                        <input
                          type="checkbox"
                          checked={item.enabled}
                          onChange={() => toggle(item)}
                          aria-label={`Aktifkan ${item.name}`}
                        />
                        <i />
                      </label>
                    </div>
                    <div className="workflow-path">
                      <span><CalendarClock size={14} />{item.interval_minutes} menit</span>
                      <ChevronRight />
                      <span>
                        {item.approval_required ? <ShieldCheck size={14} /> : <Zap size={14} />}
                        {item.approval_required ? 'Approval' : 'Otomatis'}
                      </span>
                      <button onClick={() => run(item)} disabled={!item.enabled}>
                        <Play size={14} />Jalankan
                      </button>
                    </div>
                  </article>
                ))}
                {status === 'ready' && !data.workflows.length ? (
                  <div className="automation-empty">
                    <Workflow size={27} />
                    <strong>Belum ada workflow</strong>
                    <span>Buat otomasi pertama untuk menghubungkan jadwal, action, dan approval.</span>
                  </div>
                ) : null}
              </div>
            </section>

            <aside className="run-history">
              <div className="section-heading">
                <div>
                  <h2>Riwayat run</h2>
                  <p>Eksekusi terbaru dan statusnya.</p>
                </div>
              </div>
              <div>
                {data.runs.map((item) => (
                  <article className="run-row" key={item.id}>
                    <div>
                      <strong>{item.workflow_name}</strong>
                      <code>{item.id}</code>
                    </div>
                    <RunStatus status={item.status} />
                    <span>{new Date(item.created_at).toLocaleString('id-ID')}</span>
                    {item.status === 'WAITING_APPROVAL' ? (
                      <button className="text-action" onClick={() => approve(item)}>
                        Setujui
                      </button>
                    ) : item.status === 'FAILED' ? (
                      <button className="text-action" onClick={() => retry(item)}>
                        <RotateCcw size={13} />Ulangi
                      </button>
                    ) : null}
                  </article>
                ))}
                {status === 'ready' && !data.runs.length ? (
                  <div className="automation-empty automation-empty--small">
                    <Clock3 size={24} />
                    <span>Belum ada run.</span>
                  </div>
                ) : null}
              </div>
            </aside>
          </div>
        </div>
      )}

      {builder ? (
        <>
          <button
            className="panel-backdrop"
            onClick={() => setBuilder(false)}
            aria-label="Tutup panel workflow"
          />
          <WorkflowBuilder
            onClose={() => setBuilder(false)}
            onCreated={() => {
              setBuilder(false)
              loadWorkflows()
            }}
          />
        </>
      ) : null}
    </div>
  )
}
