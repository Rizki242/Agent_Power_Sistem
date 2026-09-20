import { Component, Suspense, lazy, useEffect, useState } from 'react'
import {
  Activity, BarChart2, Bot, BrainCircuit, CalendarClock, ChevronRight, CircleCheck,
  ClipboardList, Database, FileText, FlaskConical, Menu, MessageSquareText, Settings, ShieldCheck, Workflow, X,
} from 'lucide-react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { getWorkspaceOverview } from './api.js'
import FloatingVoiceWidget from './FloatingVoiceWidget.jsx'

// Dynamic route-level code splitting per Vercel Best Practices (bundle-dynamic-imports)
const DataWorkspace = lazy(() => import('./DataWorkspace.jsx'))
const DocumentWorkspace = lazy(() => import('./DocumentWorkspace.jsx'))
const MemoryWorkspace = lazy(() => import('./MemoryWorkspace.jsx'))
const AutomationWorkspace = lazy(() => import('./AutomationWorkspace.jsx'))
const AgentLab = lazy(() => import('./AgentLab.jsx'))
const SettingsWorkspace = lazy(() => import('./SettingsWorkspace.jsx'))
const ChatWorkspace = lazy(() => import('./ChatWorkspace.jsx'))
const CBMDashboard = lazy(() => import('./CBMDashboard.jsx'))
const WorkOrdersWorkspace = lazy(() => import('./WorkOrdersWorkspace.jsx'))

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page" style={{ padding: '48px 24px', maxWidth: '640px', margin: '0 auto' }}>
          <div className="notice notice--error" style={{ display: 'flex', flexDirection: 'column', gap: '14px', padding: '24px', borderRadius: '12px' }}>
            <strong style={{ fontSize: '1.1rem' }}>Terjadi kendala saat memuat modul</strong>
            <span style={{ color: 'var(--muted)', fontSize: '0.9rem', lineHeight: '1.5' }}>
              {this.state.error?.message || 'Modul ini tidak dapat ditampilkan sementara.'}
            </span>
            <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
              <button
                type="button"
                className="button button--primary"
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.reload()
                }}
              >
                Muat Ulang Halaman
              </button>
              <button
                type="button"
                className="button"
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.href = '/overview'
                }}
              >
                Kembali ke Beranda
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

function PageFallback() {
  return (
    <div className="page page--loading" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '50vh' }}>
      <div className="chat-typing-indicator" aria-label="Memuat modul...">
        <span />
        <span />
        <span />
      </div>
    </div>
  )
}

const navigation = [
  { to: '/overview', label: 'Beranda', icon: Activity },
  { to: '/chat', label: 'Bot', icon: MessageSquareText },
  { to: '/cbm', label: 'Dashboard CBM', icon: BarChart2 },
  { to: '/work-orders', label: 'Work Orders', icon: ClipboardList },
  { to: '/data', label: 'Data', icon: Database },
  { to: '/documents', label: 'Dokumen', icon: FileText },
  { to: '/memory', label: 'Memori', icon: BrainCircuit },
  { to: '/automation', label: 'Otomasi', icon: Workflow },
  { to: '/agent-lab', label: 'Agent Lab', icon: FlaskConical },
]

const learningStages = [
  { title: 'Data masuk', detail: 'Telemetry dan dokumen diterima' },
  { title: 'Agent bekerja', detail: 'Tools dijalankan dalam batas aman' },
  { title: 'Hasil diverifikasi', detail: 'Rule dan bukti diperiksa' },
  { title: 'Memori diperbarui', detail: 'Pengetahuan menunggu persetujuan' },
  { title: 'Evaluasi retensi', detail: 'Kemampuan lama diuji kembali' },
]

function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar ${open ? 'sidebar--open' : ''}`} aria-label="Navigasi utama">
      <div className="brand">
        <div className="brand__mark"><BrainCircuit size={22} /></div>
        <div><strong>PPLE</strong><span>Agent workspace</span></div>
        <button className="icon-button sidebar__close" onClick={onClose} aria-label="Tutup navigasi"><X /></button>
      </div>
      <nav className="nav-list">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} onClick={onClose} className={({ isActive }) => `nav-item ${isActive ? 'nav-item--active' : ''}`}>
            <Icon size={19} /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar__footer">
        <NavLink to="/settings" className="nav-item"><Settings size={19} /><span>Pengaturan</span></NavLink>
        <div className="safety-note"><ShieldCheck size={18} /><span>Safety guardrail aktif</span></div>
      </div>
    </aside>
  )
}

function StatusPill({ state, children }) {
  return <span className={`status status--${state}`}><i />{children}</span>
}

function Overview() {
  const [overview, setOverview] = useState({ status: 'loading', agents: [], modules: [], runs: [], patterns: [] })

  useEffect(() => {
    const controller = new AbortController()
    getWorkspaceOverview(controller.signal)
      .then(({ agents, modules, runs, patterns }) => setOverview({ status: 'ready', agents, modules, runs, patterns }))
      .catch((error) => {
        if (error.name !== 'AbortError') setOverview({ status: 'error', agents: [], modules: [], runs: [], patterns: [] })
      })
    return () => controller.abort()
  }, [])

  const activeAgents = overview.agents.filter((agent) => ['ACTIVE', 'ONLINE'].includes(agent.status)).length
  const activeModules = overview.modules.filter((module) => module.status === 'ACTIVE').length
  const runningAutomations = (overview.runs || []).filter((run) => ['RUNNING', 'PENDING'].includes(run.status)).length
  const totalRuns = (overview.runs || []).length
  const patternsCount = (overview.patterns || []).length

  return (
    <div className="page">
      <header className="page-header">
        <div><h1>Ruang kerja agent</h1><p>Pantau bagaimana data berubah menjadi keputusan dan pengalaman.</p></div>
        {overview.status === 'ready' ? <StatusPill state="healthy">Sistem terhubung</StatusPill> :
          overview.status === 'error' ? <StatusPill state="critical">API tidak terhubung</StatusPill> :
          <StatusPill state="neutral">Memeriksa sistem</StatusPill>}
      </header>

      <section className="overview-strip" aria-label="Ringkasan sistem">
        <div><span>Agent aktif</span><strong>{overview.status === 'ready' ? `${activeAgents}/${overview.agents.length}` : '—'}</strong></div>
        <div><span>Modul engineering</span><strong>{overview.status === 'ready' ? `${activeModules}/${overview.modules.length}` : '—'}</strong></div>
        <div><span>Otomasi berjalan</span><strong>{overview.status === 'ready' ? (totalRuns > 0 ? `${runningAutomations} aktif (${totalRuns} total)` : '0 aktif') : '—'}</strong></div>
        <div><span>Memori terdata</span><strong>{overview.status === 'ready' ? (patternsCount > 0 ? `${patternsCount} pola siap` : '0 pola') : '—'}</strong></div>
      </section>

      {overview.status === 'error' && (
        <div className="notice notice--error"><strong>Data monitoring belum dapat dimuat.</strong><span>Jalankan FastAPI di port 8000, lalu muat ulang halaman.</span></div>
      )}

      <div className="workspace-grid">
        <section className="learning-loop">
          <div className="section-heading"><div><h2>Siklus belajar agent</h2><p>Setiap perubahan tetap dapat ditelusuri dan ditinjau manusia.</p></div><Bot size={24} /></div>
          <ol className="stage-list">
            {learningStages.map((stage, index) => (
              <li key={stage.title} className={index < 3 ? 'stage stage--active' : 'stage'}>
                <div className="stage__marker">{index < 3 ? <CircleCheck size={18} /> : index + 1}</div>
                <div><strong>{stage.title}</strong><span>{stage.detail}</span></div>
                <span className="stage__state">{index < 3 ? 'Siap' : 'Tahap berikutnya'}</span>
              </li>
            ))}
          </ol>
        </section>

        <aside className="activity-panel">
          <div className="section-heading"><div><h2>Aktivitas sistem</h2><p>Status nyata dari backend.</p></div></div>
          {overview.status === 'ready' && overview.modules.length > 0 ? (
            <ul className="activity-list">
              {overview.modules.slice(0, 6).map((module) => (
                <li key={module.module_id}>
                  <span className={`activity-dot activity-dot--${module.status.toLowerCase()}`} />
                  <div><strong>{module.module_id.replaceAll('_', ' ')}</strong><span>Modul {module.status.toLowerCase()}</span></div>
                  <ChevronRight size={16} />
                </li>
              ))}
            </ul>
          ) : <div className="empty-state"><CalendarClock size={28} /><strong>Belum ada aktivitas</strong><span>Aktivitas muncul setelah API terhubung.</span></div>}
        </aside>
      </div>
    </div>
  )
}

export default function App() {
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  const isChatMode = location.pathname === '/chat'

  return (
    <div className={`app-shell ${isChatMode ? 'app-shell--chat-mode' : ''}`}>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      {navOpen ? (
        <button
          className="sidebar-backdrop"
          onClick={() => setNavOpen(false)}
          aria-label="Tutup navigasi"
        />
      ) : null}
      <main className="main-content">
        <button className="icon-button mobile-menu" onClick={() => setNavOpen(true)} aria-label="Buka navigasi"><Menu /></button>
        <ErrorBoundary>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<Overview />} />
              <Route path="/chat" element={<ChatWorkspace onOpenNav={() => setNavOpen(true)} />} />
              <Route path="/cbm" element={<CBMDashboard />} />
              <Route path="/work-orders" element={<WorkOrdersWorkspace />} />
              <Route path="/data" element={<DataWorkspace />} />
              <Route path="/documents" element={<DocumentWorkspace />} />
              <Route path="/memory" element={<MemoryWorkspace />} />
              <Route path="/automation" element={<AutomationWorkspace />} />
              <Route path="/agent-lab" element={<AgentLab />} />
              <Route path="/settings" element={<SettingsWorkspace />} />
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
      <FloatingVoiceWidget />
    </div>
  )
}
