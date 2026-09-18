import React, { useEffect, useMemo, useState } from 'react'
import {
  Circle,
  Download,
  Menu,
  PanelLeftClose,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
} from 'lucide-react'
import { Link } from 'react-router-dom'

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
      {/* Left Indicator Icon: solid blue dot for tasks; small outline circle for normal chats */}
      <div className="chat-history-item__icon">
        {isTask ? (
          <span className="dot-solid-blue" aria-label="Tugas terjadwal" />
        ) : (
          <Circle size={9} strokeWidth={1.7} className="circle-outline-gray" />
        )}
      </div>

      {/* Session Title */}
      <span className={`chat-history-item__title ${isUntitled ? 'chat-history-item__title--untitled' : ''}`}>
        {isUntitled ? 'Untitled' : session.title}
      </span>

      {/* Right Badge / Delete on hover */}
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
  userName = 'Rizki',
  userRole = 'Engineer',
}) {
  const [filterType, setFilterType] = useState('ALL') // 'ALL' | 'CHAT' | 'TASK'
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Close filter menu when clicking outside (client-event-listeners, js-early-exit)
  useEffect(() => {
    if (!showFilterMenu) return
    const handleDocClick = () => setShowFilterMenu(false)
    window.addEventListener('click', handleDocClick)
    return () => window.removeEventListener('click', handleDocClick)
  }, [showFilterMenu])

  // Memoize filtered list to prevent re-filtering on unrelated renders (rerender-derived-state-no-effect)
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

  return (
    <aside className="chat-history-sidebar" aria-label="Riwayat obrolan dan tugas">
      {/* Top Header */}
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
          <h2>Obrolan dan tugas</h2>
        </div>
        <div className="chat-history-header__right">
          <button
            type="button"
            className="icon-button-subtle"
            onClick={(e) => {
              e.stopPropagation()
              setShowFilterMenu(!showFilterMenu)
            }}
            title="Saring jenis obrolan atau tugas"
            aria-label="Filter"
          >
            <SlidersHorizontal size={15} />
          </button>
          <button
            type="button"
            className="icon-button-subtle"
            onClick={onCreateNewSession}
            title="Mulai obrolan baru"
            aria-label="Obrolan Baru"
          >
            <Plus size={17} />
          </button>
          {onToggleCollapse ? (
            <button
              type="button"
              className="icon-button-subtle"
              onClick={onToggleCollapse}
              title="Sembunyikan panel riwayat"
              aria-label="Sembunyikan panel"
            >
              <PanelLeftClose size={15} />
            </button>
          ) : null}
        </div>

        {/* Filter dropdown */}
        {showFilterMenu ? (
          <div
            className="history-filter-menu"
            onClick={(e) => e.stopPropagation()}
            role="menu"
          >
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

      {/* Quick Search bar */}
      {searchOpen ? (
        <div className="history-search-bar">
          <Search size={14} className="history-search-icon" />
          <input
            type="text"
            className="history-search-input"
            placeholder="Cari obrolan / aset..."
            value={searchQuery}
            autoFocus
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button
            type="button"
            className="icon-button-subtle"
            onClick={() => { setSearchQuery(''); setSearchOpen(false) }}
          >
            <X size={13} />
          </button>
        </div>
      ) : null}

      {/* List of Sessions */}
      <div className="chat-history-list" role="list">
        {filteredSessions.length === 0 ? (
          <div className="history-empty-note">
            <span>Tidak ada sesi yang cocok</span>
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

      {/* Sticky Footer */}
      <div className="chat-history-footer">
        <div className="history-user-info">
          <div className="history-user-avatar">
            <span>{(userName || 'U')[0].toUpperCase()}</span>
          </div>
          <div className="history-user-meta">
            <span className="history-user-name">{userName}</span>
            <span className="history-user-role">· {userRole}</span>
          </div>
        </div>

        <div className="history-footer-actions">
          <button
            type="button"
            className="icon-button-subtle"
            onClick={onExportSession}
            title="Ekspor ringkasan percakapan"
            aria-label="Ekspor percakapan"
          >
            <Download size={16} />
          </button>
          <button
            type="button"
            className="icon-button-subtle"
            onClick={() => setSearchOpen(!searchOpen)}
            title="Cari riwayat"
            aria-label="Cari riwayat"
          >
            <Search size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
