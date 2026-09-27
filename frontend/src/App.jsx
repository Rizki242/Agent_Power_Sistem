import { Component, Suspense, lazy, useEffect, useRef, useState } from 'react'
import {
  Activity, AlertCircle, BarChart2, Bot, BrainCircuit, CalendarClock, CheckCircle2,
  ChevronRight, ChevronUp, CircleCheck, ClipboardList, Database, FileText, FlaskConical,
  Gauge, Info, KeyRound, LogOut, Menu, MessageSquareText, Moon, Settings, ShieldCheck,
  Sun, Workflow, X, Zap,
} from 'lucide-react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { changeUserPassword, getWorkspaceOverview } from './api.js'
import FloatingVoiceWidget from './FloatingVoiceWidget.jsx'
import { ToastProvider } from './components/Toast.jsx'
import { AvatarThumb, ProfileAvatarEditor } from './components/ProfileAvatar.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import LoginPage from './LoginPage.jsx'
import { readThemePreference, resolveTheme, saveThemePreference } from './utils/theme.js'

// Dynamic route-level code splitting per Vercel Best Practices (bundle-dynamic-imports)
const DataWorkspace = lazy(() => import('./DataWorkspace.jsx'))
const DocumentWorkspace = lazy(() => import('./DocumentWorkspace.jsx'))
const MemoryWorkspace = lazy(() => import('./MemoryWorkspace.jsx'))
const AutomationWorkspace = lazy(() => import('./AutomationWorkspace.jsx'))
const AgentLab = lazy(() => import('./AgentLab.jsx'))
const SettingsWorkspace = lazy(() => import('./SettingsWorkspace.jsx'))
const ChatWorkspace = lazy(() => import('./ChatWorkspace.jsx'))
const CBMDashboard = lazy(() => import('./CBMDashboard.jsx'))
const MCSAWorkspace = lazy(() => import('./MCSAWorkspace.jsx'))
const WorkOrdersWorkspace = lazy(() => import('./WorkOrdersWorkspace.jsx'))
const FleetWorkspace = lazy(() => import('./FleetWorkspace.jsx'))

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

// Navigasi dikelompokkan per kriteria agar daftar tidak memanjang:
// pantau kondisi, tindak lanjut pekerjaan, lalu data/pengetahuan.
const NAV_GROUPS = [
  {
    id: 'utama',
    label: 'Utama',
    items: [
      { to: '/overview', label: 'Beranda', icon: Activity },
      { to: '/chat', label: 'Bot', icon: MessageSquareText },
    ],
  },
  {
    id: 'kondisi',
    label: 'Monitoring Kondisi',
    items: [
      { to: '/fleet', label: 'Keandalan Armada', icon: Gauge },
      { to: '/cbm', label: 'Dashboard CBM', icon: BarChart2 },
      { to: '/mcsa', label: 'MCSA Motor', icon: Zap },
    ],
  },
  {
    id: 'tindak-lanjut',
    label: 'Tindak Lanjut',
    items: [
      { to: '/work-orders', label: 'Work Orders', icon: ClipboardList },
      { to: '/automation', label: 'Otomasi', icon: Workflow },
    ],
  },
  {
    id: 'pengetahuan',
    label: 'Data & Pengetahuan',
    items: [
      { to: '/data', label: 'Data', icon: Database },
      { to: '/documents', label: 'Dokumen', icon: FileText },
      { to: '/memory', label: 'Memori', icon: BrainCircuit },
      { to: '/agent-lab', label: 'Agent Lab', icon: FlaskConical },
    ],
  },
]

const NAV_COLLAPSE_KEY = 'pple_nav_collapsed'

const learningStages = [
  { title: 'Data masuk', detail: 'Telemetry dan dokumen diterima' },
  { title: 'Agent bekerja', detail: 'Tools dijalankan dalam batas aman' },
  { title: 'Hasil diverifikasi', detail: 'Rule dan bukti diperiksa' },
  { title: 'Memori diperbarui', detail: 'Pengetahuan menunggu persetujuan' },
  { title: 'Evaluasi retensi', detail: 'Kemampuan lama diuji kembali' },
]

function ChangePasswordModal({ onClose }) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!oldPassword || !newPassword) {
      setErrorMsg('Kata sandi lama dan baru wajib diisi.')
      return
    }
    if (newPassword.length < 6) {
      setErrorMsg('Kata sandi baru minimal 6 karakter.')
      return
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg('Konfirmasi kata sandi baru tidak cocok.')
      return
    }

    setErrorMsg('')
    setSuccessMsg('')
    setIsSubmitting(true)
    try {
      const res = await changeUserPassword(oldPassword, newPassword)
      setSuccessMsg(res.message || 'Kata sandi berhasil diperbarui!')
      setTimeout(() => {
        onClose()
      }, 1400)
    } catch (err) {
      setErrorMsg(err.message || 'Gagal mengubah kata sandi. Periksa kata sandi lama Anda.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="password-modal-backdrop" onClick={onClose}>
      <div className="password-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="password-modal-header">
          <div className="password-modal-title">
            <KeyRound size={20} className="password-modal-icon" />
            <h3>Ganti Kata Sandi</h3>
          </div>
          <button type="button" className="icon-button password-modal-close" onClick={onClose} aria-label="Tutup">
            <X size={18} />
          </button>
        </div>

        {errorMsg && (
          <div className="login-error-alert" style={{ margin: '0 0 14px 0' }} role="alert">
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="notice notice--success" style={{ margin: '0 0 14px 0', padding: '10px 14px' }}>
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="modal-old-pass">Kata Sandi Lama</label>
            <input
              id="modal-old-pass"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="Masukkan kata sandi lama"
              required
              autoFocus
            />
          </div>

          <div className="login-field">
            <label htmlFor="modal-new-pass">Kata Sandi Baru</label>
            <input
              id="modal-new-pass"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Minimal 6 karakter"
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="modal-confirm-pass">Konfirmasi Kata Sandi Baru</label>
            <input
              id="modal-confirm-pass"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Ketik ulang kata sandi baru"
              required
            />
          </div>

          <div className="password-modal-actions">
            <button type="button" className="secondary-btn" onClick={onClose} disabled={isSubmitting}>
              Batal
            </button>
            <button type="submit" className="login-submit-btn" style={{ margin: 0, width: 'auto' }} disabled={isSubmitting}>
              {isSubmitting ? 'Menyimpan...' : 'Perbarui Kata Sandi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function UserProfileMenu({ user, onLogout }) {
  const [isOpen, setIsOpen] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const displayName = user.full_name || user.username || 'Pengguna'
  const initial = displayName.trim().charAt(0).toUpperCase() || 'U'
  const roleLabel = user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase()) : 'Staff'
  const firstName = displayName.split(' ')[0]

  return (
    <div className="sidebar-user-wrapper" ref={menuRef}>
      {isOpen && (
        <div className="profile-popover-menu" role="menu" aria-label="Menu akun pengguna">
          <div className="profile-popover-header">
            <ProfileAvatarEditor avatar={user.avatar} initial={initial} displayName={displayName} />
            <div className="profile-popover-email">{user.username}@jeranjang.pln.id</div>
            <div className="profile-popover-user">
              <strong className="profile-popover-name">{displayName}</strong>
              <span className="profile-popover-badge">{user.role || 'OPERATOR'}</span>
            </div>
            <div className="profile-popover-unit">{user.unit || 'PLTU Jeranjang (3 × 25 MW)'}</div>
          </div>

          <div className="profile-popover-divider" />

          <div className="profile-popover-list">
            <NavLink
              to="/settings"
              className="profile-popover-item"
              onClick={() => setIsOpen(false)}
              role="menuitem"
            >
              <Settings size={16} />
              <span>Pengaturan</span>
              <span className="profile-popover-hint">Sistem</span>
            </NavLink>

            <button
              type="button"
              className="profile-popover-item"
              onClick={() => {
                setIsOpen(false)
                setShowPasswordModal(true)
              }}
              role="menuitem"
            >
              <KeyRound size={16} />
              <span>Ganti Kata Sandi</span>
            </button>

            <div className="profile-popover-item profile-popover-item--static" role="menuitem">
              <ShieldCheck size={16} className="profile-popover-shield" />
              <span>Safety Guardrail</span>
              <span className="profile-popover-badge profile-popover-badge--healthy">Aktif</span>
            </div>

            <div className="profile-popover-item profile-popover-item--static" role="menuitem">
              <Info size={16} />
              <span>Sistem CBM</span>
              <span className="profile-popover-hint">v2.0.0</span>
            </div>
          </div>

          <div className="profile-popover-divider" />

          <button
            type="button"
            className="profile-popover-item profile-popover-logout"
            onClick={() => {
              setIsOpen(false)
              onLogout()
            }}
            role="menuitem"
          >
            <LogOut size={16} />
            <span>Keluar</span>
          </button>
        </div>
      )}

      <button
        type="button"
        className={`sidebar-user-pill ${isOpen ? 'sidebar-user-pill--active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={`${displayName} (${user.role || 'Pengguna'})`}
      >
        <div className="sidebar-user-avatar">
          <AvatarThumb avatar={user.avatar} initial={initial} imgClassName="sidebar-user-avatar-img" />
        </div>
        <div className="sidebar-user-details">
          <span className="sidebar-user-name">{firstName}</span>
          <span className="sidebar-user-dot">·</span>
          <span className="sidebar-user-role">{roleLabel}</span>
        </div>
        <ChevronUp size={15} className={`sidebar-user-chevron ${isOpen ? 'sidebar-user-chevron--open' : ''}`} />
      </button>

      {showPasswordModal && (
        <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />
      )}
    </div>
  )
}

function Sidebar({ open, onClose, user, onLogout }) {
  const location = useLocation()

  // Grup yang diciutkan disimpan agar pilihan pengguna bertahan antar kunjungan.
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(NAV_COLLAPSE_KEY) || '[]')
      return Array.isArray(saved) ? saved : []
    } catch {
      return []
    }
  })

  const toggleGroup = (groupId) => {
    setCollapsed((prev) => {
      const next = prev.includes(groupId) ? prev.filter((id) => id !== groupId) : [...prev, groupId]
      try {
        localStorage.setItem(NAV_COLLAPSE_KEY, JSON.stringify(next))
      } catch {}
      return next
    })
  }

  return (
    <aside className={`sidebar ${open ? 'sidebar--open' : ''}`} aria-label="Navigasi utama">
      <div className="brand">
        <div className="brand__mark"><BrainCircuit size={22} /></div>
        <div><strong>PPLE</strong><span>Agent workspace</span></div>
        <ThemeToggle />
        <button className="icon-button sidebar__close" onClick={onClose} aria-label="Tutup navigasi"><X /></button>
      </div>
      <nav className="nav-list">
        {NAV_GROUPS.map((group) => {
          // Grup yang memuat halaman aktif selalu terbuka supaya posisi pengguna terlihat.
          const hasActive = group.items.some((item) => location.pathname === item.to)
          const isOpen = hasActive || !collapsed.includes(group.id)
          return (
            <div key={group.id} className="nav-group">
              <button
                type="button"
                className="nav-group__header"
                onClick={() => toggleGroup(group.id)}
                aria-expanded={isOpen}
                aria-controls={`nav-group-${group.id}`}
              >
                <span>{group.label}</span>
                <ChevronRight size={14} className={isOpen ? 'nav-group__chevron nav-group__chevron--open' : 'nav-group__chevron'} />
              </button>
              {isOpen ? (
                <div className="nav-group__items" id={`nav-group-${group.id}`}>
                  {group.items.map(({ to, label, icon: Icon }) => (
                    <NavLink key={to} to={to} onClick={onClose} className={({ isActive }) => `nav-item ${isActive ? 'nav-item--active' : ''}`}>
                      <Icon size={19} /><span>{label}</span>
                    </NavLink>
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </nav>
      <div className="sidebar__footer">
        {user ? (
          <UserProfileMenu user={user} onLogout={onLogout} />
        ) : null}
        <div className="safety-note"><ShieldCheck size={18} /><span>Safety guardrail aktif</span></div>
      </div>
    </aside>
  )
}

/**
 * Pengalih cepat Terang/Gelap. Preferensi "ikut sistem" tetap dihormati:
 * menekan tombol memilih lawan dari tema yang sedang tampil.
 */
function ThemeToggle() {
  const [theme, setTheme] = useState(() => resolveTheme(readThemePreference()))

  useEffect(() => {
    const sync = () => setTheme(resolveTheme(readThemePreference()))
    window.addEventListener('focus', sync)
    return () => window.removeEventListener('focus', sync)
  }, [])

  const isDark = theme === 'dark'
  return (
    <button
      type="button"
      className="icon-button sidebar__theme"
      onClick={() => setTheme(saveThemePreference(isDark ? 'light' : 'dark'))}
      title={isDark ? 'Beralih ke tema terang' : 'Beralih ke tema gelap (Control Room)'}
      aria-label={isDark ? 'Beralih ke tema terang' : 'Beralih ke tema gelap'}
      aria-pressed={isDark}
    >
      {isDark ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  )
}

function StatusPill({ state, children }) {
  return <span className={`status status--${state}`}><i />{children}</span>
}

function Overview() {
  const [overview, setOverview] = useState({ status: 'loading', agents: [], modules: [], runs: [], patterns: [], failed: 0 })

  useEffect(() => {
    const controller = new AbortController()
    getWorkspaceOverview(controller.signal)
      .then(({ agents, modules, runs, patterns, failed, total }) => {
        // Semua sumber gagal berarti backend tidak terjangkau, bukan "terhubung".
        const status = failed >= total ? 'error' : failed > 0 ? 'partial' : 'ready'
        setOverview({ status, agents, modules, runs, patterns, failed })
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setOverview({ status: 'error', agents: [], modules: [], runs: [], patterns: [], failed: 4 })
      })
    return () => controller.abort()
  }, [])

  const hasData = overview.status === 'ready' || overview.status === 'partial'
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
          overview.status === 'partial' ? <StatusPill state="attention">Sebagian data tidak tersedia</StatusPill> :
          overview.status === 'error' ? <StatusPill state="critical">API tidak terhubung</StatusPill> :
          <StatusPill state="neutral">Memeriksa sistem</StatusPill>}
      </header>

      <section className="overview-strip" aria-label="Ringkasan sistem">
        <div><span>Agent aktif</span><strong>{hasData ? `${activeAgents}/${overview.agents.length}` : '—'}</strong></div>
        <div><span>Modul engineering</span><strong>{hasData ? `${activeModules}/${overview.modules.length}` : '—'}</strong></div>
        <div><span>Otomasi berjalan</span><strong>{hasData ? (totalRuns > 0 ? `${runningAutomations} aktif (${totalRuns} total)` : '0 aktif') : '—'}</strong></div>
        <div><span>Memori terdata</span><strong>{hasData ? (patternsCount > 0 ? `${patternsCount} pola siap` : '0 pola') : '—'}</strong></div>
      </section>

      {overview.status === 'error' && (
        <div className="notice notice--error"><strong>Data monitoring belum dapat dimuat.</strong><span>Jalankan FastAPI di port 8000, lalu muat ulang halaman.</span></div>
      )}

      {overview.status === 'partial' && (
        <div className="notice notice--warning">
          <strong>Sebagian data tidak tersedia.</strong>
          <span>{overview.failed} dari 4 sumber monitoring gagal dijawab backend; angka di atas hanya mencakup sumber yang berhasil.</span>
        </div>
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
          {hasData && overview.modules.length > 0 ? (
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

function AppShell() {
  const { user, isAuthenticated, isLoading, logout } = useAuth()
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  const isChatMode = location.pathname === '/chat'

  if (isLoading) {
    return (
      <div className="login-loading-screen">
        <div className="chat-typing-indicator" aria-label="Memeriksa sesi pengguna...">
          <span />
          <span />
          <span />
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return (
    <div className={`app-shell ${isChatMode ? 'app-shell--chat-mode' : ''}`}>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} user={user} onLogout={logout} />
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
              <Route path="/fleet" element={<FleetWorkspace />} />
              <Route path="/cbm" element={<CBMDashboard />} />
              <Route path="/mcsa" element={<MCSAWorkspace />} />
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

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppShell />
      </ToastProvider>
    </AuthProvider>
  )
}

