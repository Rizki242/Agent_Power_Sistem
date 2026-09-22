import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  BarChart2,
  BrainCircuit,
  ChevronUp,
  Circle,
  ClipboardList,
  Download,
  LogOut,
  Menu,
  PanelLeftClose,
  Pin,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  Workflow,
  X,
  Zap,
} from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'

// Memoized session row component per Vercel Best Practices (rerender-memo)
const ChatHistoryItem = React.memo(function ChatHistoryItem({
  session,
  isSelected,
  onSelectSession,
  onDeleteSession,
}) {
  const isTask = session.session_type === 'task'
  const isUntitled = !session.title || session.title.trim().toLowerCase() === 'untitled'
  const isPendingReview = session.status === 'pending_review'

  return (
    <div
      role="listitem"
      className={`chat-history-item ${isSelected ? 'chat-history-item--active' : ''} ${isTask ? 'chat-history-item--task' : ''}`}
      onClick={() => onSelectSession(session.session_id)}
      title={session.title || 'Untitled'}
    >
      {/* Left Indicator Icon */}
      <div className="chat-history-item__icon">
        {isTask ? (
          <span className="dot-solid-blue" aria-label="Tugas terjadwal" />
        ) : (
          <Circle size={8} strokeWidth={1.8} className="circle-outline-gray" />
        )}
      </div>

      {/* Session Title */}
      <span className={`chat-history-item__title ${isUntitled ? 'chat-history-item__title--untitled' : ''}`}>
        {isUntitled ? 'Percakapan baru' : session.title}
      </span>

      {/* Right Actions */}
      <div className="chat-history-item__actions" onClick={(e) => e.stopPropagation()}>
        {isPendingReview ? (
          <Link
            to="/memory"
            className="history-review-chip"
            title="Menunggu review di Memori"
          >
            Review
          </Link>
        ) : null}
        {onDeleteSession ? (
          <button
            type="button"
            className="history-delete-btn"
            onClick={() => onDeleteSession(session.session_id)}
            title="Hapus sesi ini"
            aria-label="Hapus sesi"
          >
            <Trash2 size={13} />
          </button>
        ) : null}
      </div>
    </div>
  )
})

export default function ChatHistoryPanel({
  sessions = [],
  activeSessionId,
  onSelectSession,
  onCreateNewSession,
  onDeleteSession,
  onExportSession,
  onOpenNav,
  onToggleCollapse,
  user,
  onLogout,
  onSelectPrompt,
}) {
  const [filterType, setFilterType] = useState('ALL') // 'ALL' | 'CHAT' | 'TASK'
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const profileRef = useRef(null)

  // Close menus when clicking outside
  useEffect(() => {
    if (!showFilterMenu && !isProfileOpen) return
    const handleDocClick = (e) => {
      if (showFilterMenu) setShowFilterMenu(false)
      if (isProfileOpen && profileRef.current && !profileRef.current.contains(e.target)) {
        setIsProfileOpen(false)
      }
    }
    window.addEventListener('click', handleDocClick)
    return () => window.removeEventListener('click', handleDocClick)
  }, [showFilterMenu, isProfileOpen])

  // Memoize filtered list
  const filteredSessions = useMemo(() => {
    return sessions.filter((session) => {
      if (filterType === 'CHAT' && session.session_type !== 'chat') return false
      if (filterType === 'TASK' && session.session_type !== 'task') return false

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const title = (session.title || '').toLowerCase()
        return title.includes(q)
      }
      return true
    })
  }, [sessions, filterType, searchQuery])

  // User meta
  const displayName = user?.full_name || user?.username || 'Rizki'
  const roleLabel = user?.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase()) : 'Engineer'
  const initial = displayName.trim().charAt(0).toUpperCase() || 'R'
  const firstName = displayName.split(' ')[0]

  return (
    <aside className="chat-history-sidebar chat-history-sidebar--claude" aria-label="Riwayat obrolan dan navigasi CBM">
      {/* 1. Header: Brand + Collapse button */}
      <div className="chat-history-header">
        <div className="chat-history-header__left">
          {onOpenNav ? (
            <button
              type="button"
              className="icon-button-subtle history-menu-btn"
              onClick={onOpenNav}
              title="Buka menu navigasi utama PPLE"
              aria-label="Menu navigasi"
            >
              <Menu size={16} />
            </button>
          ) : null}
          <div className="chat-brand-row">
            <div className="chat-brand-badge">
              <BrainCircuit size={17} />
            </div>
            <span className="chat-brand-title">Agent Learning Sistem</span>
          </div>
        </div>
        <div className="chat-history-header__right">
          {onToggleCollapse ? (
            <button
              type="button"
              className="icon-button-subtle"
              onClick={onToggleCollapse}
              title="Sembunyikan panel riwayat"
              aria-label="Sembunyikan panel"
            >
              <PanelLeftClose size={16} />
            </button>
          ) : null}
        </div>
      </div>

      {/* 2. Search Input */}
      <div className="chat-sidebar-search-box">
        <Search size={14} className="chat-sidebar-search-icon" />
        <input
          type="text"
          className="chat-sidebar-search-input"
          placeholder="Cari obrolan..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery ? (
          <button
            type="button"
            className="chat-sidebar-search-clear"
            onClick={() => setSearchQuery('')}
            aria-label="Hapus pencarian"
          >
            <X size={13} />
          </button>
        ) : null}
      </div>

      {/* 3. Prominent New Chat Button (Claude Style) */}
      <button
        type="button"
        className="chat-new-button-claude"
        onClick={onCreateNewSession}
      >
        <Plus size={16} />
        <span>Chat Baru</span>
      </button>

      {/* 4. Quick Navigation Links (Proyek, Artifacts, Terjadwal style) */}
      <div className="chat-quick-nav-group">
        <NavLink to="/cbm" className="chat-quick-nav-item" title="Buka Dashboard CBM">
          <BarChart2 size={16} className="text-action" />
          <span>Dashboard CBM</span>
        </NavLink>
        <NavLink to="/mcsa" className="chat-quick-nav-item" title="Buka Analisis MCSA & Motor">
          <Zap size={16} className="text-warning" />
          <span>MCSA Motor</span>
        </NavLink>
        <NavLink to="/work-orders" className="chat-quick-nav-item" title="Buka Work Orders">
          <ClipboardList size={16} />
          <span>Work Orders</span>
        </NavLink>
        <NavLink to="/automation" className="chat-quick-nav-item" title="Buka Otomasi & Siklus Belajar">
          <Workflow size={16} />
          <span>Otomasi & Siklus</span>
          <span className="dot-live-indicator" />
        </NavLink>
      </div>

      {/* Scrollable middle area */}
      <div className="chat-sidebar-scroll-area">
        {/* 5. Pinned Section (Disematkan) */}
        <div className="chat-sidebar-section">
          <div className="chat-sidebar-section-title">
            <span>Disematkan</span>
          </div>
          <div className="chat-pinned-list">
            <button
              type="button"
              className="chat-pinned-item"
              onClick={() => onSelectPrompt && onSelectPrompt('Bagaimana kondisi DGA transformator utama (GT 1, GT 2, GT 3, dan UAT)?')}
            >
              <Pin size={13} className="chat-pinned-icon" />
              <span>Trafo Generator (GT 1-3) & UAT</span>
            </button>
            <button
              type="button"
              className="chat-pinned-item"
              onClick={() => onSelectPrompt && onSelectPrompt('Bagaimana status vibrasi dan pelumas BFP 1A & 1B?')}
            >
              <Pin size={13} className="chat-pinned-icon" />
              <span>Boiler Feed Pump (BFP 1A/B)</span>
            </button>
          </div>
        </div>

        {/* 6. Recent History Section (Terbaru) */}
        <div className="chat-sidebar-section">
          <div className="chat-sidebar-section-title">
            <span>Terbaru</span>
            <button
              type="button"
              className="icon-button-subtle chat-sidebar-filter-btn"
              onClick={(e) => {
                e.stopPropagation()
                setShowFilterMenu(!showFilterMenu)
              }}
              title="Filter riwayat obrolan"
              aria-label="Filter"
            >
              <SlidersHorizontal size={13} />
            </button>

            {showFilterMenu ? (
              <div className="history-filter-menu" onClick={(e) => e.stopPropagation()} role="menu">
                <button
                  type="button"
                  className={`filter-item ${filterType === 'ALL' ? 'filter-item--active' : ''}`}
                  onClick={() => { setFilterType('ALL'); setShowFilterMenu(false) }}
                >
                  Semua aktivitas
                </button>
                <button
                  type="button"
                  className={`filter-item ${filterType === 'CHAT' ? 'filter-item--active' : ''}`}
                  onClick={() => { setFilterType('CHAT'); setShowFilterMenu(false) }}
                >
                  Hanya Obrolan
                </button>
                <button
                  type="button"
                  className={`filter-item ${filterType === 'TASK' ? 'filter-item--active' : ''}`}
                  onClick={() => { setFilterType('TASK'); setShowFilterMenu(false) }}
                >
                  Tugas & Otomasi
                </button>
              </div>
            ) : null}
          </div>

          <div className="chat-history-list" role="list">
            {filteredSessions.length === 0 ? (
              <div className="history-empty-note">
                <span>{searchQuery ? 'Tidak ada yang cocok' : 'Belum ada obrolan'}</span>
              </div>
            ) : (
              filteredSessions.map((session) => (
                <ChatHistoryItem
                  key={session.session_id}
                  session={session}
                  isSelected={session.session_id === activeSessionId}
                  onSelectSession={onSelectSession}
                  onDeleteSession={onDeleteSession}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* 7. Sticky Claude-Style User Profile Footer with Popover */}
      <div className="chat-history-footer" ref={profileRef}>
        {isProfileOpen && (
          <div className="profile-popover-menu" role="menu" aria-label="Menu akun pengguna">
            <div className="profile-popover-header">
              <div className="profile-popover-email">{user?.username || 'user'}@jeranjang.pln.id</div>
              <div className="profile-popover-user">
                <strong className="profile-popover-name">{displayName}</strong>
                <span className="profile-popover-badge">{user?.role || 'ENGINEER'}</span>
              </div>
              <div className="profile-popover-unit">{user?.unit || 'PLTU Jeranjang (3 × 25 MW)'}</div>
            </div>

            <div className="profile-popover-divider" />

            <div className="profile-popover-list">
              <NavLink
                to="/settings"
                className="profile-popover-item"
                onClick={() => setIsProfileOpen(false)}
                role="menuitem"
              >
                <Settings size={30} />
                <span>Pengaturan Sistem</span>
                <span className="profile-popover-hint">AI & LLM</span>
              </NavLink>

              <div className="profile-popover-item profile-popover-item--static" role="menuitem">
                <ShieldCheck size={30} className="profile-popover-shield" />
                <span>Safety Guardrail</span>
                <span className="profile-popover-badge profile-popover-badge--healthy">Aktif</span>
              </div>

              {onExportSession ? (
                <button
                  type="button"
                  className="profile-popover-item"
                  onClick={() => {
                    setIsProfileOpen(false)
                    onExportSession()
                  }}
                  role="menuitem"
                >
                  <Download size={16} />
                  <span>Ekspor Percakapan</span>
                </button>
              ) : null}
            </div>

            <div className="profile-popover-divider" />

            {onLogout ? (
              <button
                type="button"
                className="profile-popover-item profile-popover-logout"
                onClick={() => {
                  setIsProfileOpen(false)
                  onLogout()
                }}
                role="menuitem"
              >
                <LogOut size={16} />
                <span>Keluar</span>
              </button>
            ) : null}
          </div>
        )}

        <button
          type="button"
          className={`sidebar-user-pill ${isProfileOpen ? 'sidebar-user-pill--active' : ''}`}
          onClick={() => setIsProfileOpen(!isProfileOpen)}
          aria-expanded={isProfileOpen}
          aria-haspopup="true"
        >
          <div className="sidebar-user-avatar">
            {initial}
          </div>
          <div className="sidebar-user-details">
            <span className="sidebar-user-name">{firstName}</span>
            <span className="sidebar-user-dot">·</span>
            <span className="sidebar-user-role">{roleLabel}</span>
          </div>
          <ChevronUp size={15} className={`sidebar-user-chevron ${isProfileOpen ? 'sidebar-user-chevron--open' : ''}`} />
        </button>
      </div>
    </aside>
  )
}
