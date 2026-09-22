import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Menu,
  Mic,
  MicOff,
  PanelLeftOpen,
  Paperclip,
  RotateCcw,
  Send,
  ShieldAlert,
  Sparkles,
  User,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import {
  createNewChatSession,
  deleteChatSession,
  generateCbmWorkOrder,
  getChatSessionMessages,
  getChatSessions,
  sendChatMessage,
} from './api.js'
import ChatHistoryPanel from './ChatHistoryPanel.jsx'
import { useToast } from './components/Toast.jsx'
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speakText,
  startSpeechRecognition,
  stopSpeaking,
} from './utils/speech.js'

const QUICK_ACTIONS = [
  { label: '⚠️ Daftar peralatan alarm/warning', prompt: 'Tampilkan daftar peralatan yang saat ini berstatus Warning atau Alarm di PLTU Jeranjang.' },
  { label: '⚡ Kondisi transformator DGA', prompt: 'Bagaimana kondisi DGA transformator utama (GT 1, GT 2, GT 3, dan UAT)?' },
  { label: '🔄 Status vibrasi & MCSA CWP 1A', prompt: 'Bagaimana status kesehatan motor dan vibrasi pompa CWP 1A?' },
  { label: '🛢️ Analisis pelumas BFP 1A', prompt: 'Bagaimana kondisi oli dan keausan tribologi pada BFP 1A?' },
  { label: '📉 Rekomendasi RUL & CBM teratas', prompt: 'Sebutkan peralatan dengan RUL kritis dan tindakan pemeliharaan yang disarankan.' },
]

import MarkdownRenderer from './components/MarkdownRenderer.jsx'
import PlanetaryGear from './components/PlanetaryGear.jsx'
import { useGearDuration, recordLatency } from './utils/connectionSpeed.js'

const LOADING_STAGES = [
  'Memeriksa Safety Guardrail & mengenali aset...',
  'Mengumpulkan bukti specialist agents (MCSA, Vibrasi, DGA, PD, Tribologi, Thermal)...',
  'Menelusuri knowledge base & standar (ISO / IEEE / NEMA / EPRI)...',
  'Menyusun diagnosis konsensus dan rekomendasi CBM...',
]

function formatChatTime(raw) {
  if (!raw) return ''
  const str = String(raw).trim()
  if (/^\d{2}[:.]\d{2}$/.test(str)) return str
  try {
    const d = new Date(str)
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
    }
  } catch {}
  const match = str.match(/T(\d{2}[:.]\d{2})/)
  if (match) return match[1]
  return str.slice(0, 5)
}

const defaultWelcomeMessage = {
  id: 'welcome',
  role: 'assistant',
  text: 'Halo! Saya **Agent Learning Sistem PLTU Jeranjang**.\n\nSaya memadukan analisa 6 spesialis (*Vibrasi, MCSA, DGA, Partial Discharge, Tribologi, Thermal*), Safety Guardrail, dan pengetahuan unit PLTU Jeranjang (3 × 25 MW).\n\nAnda dapat menanyakan kondisi mesin, tren getaran, analisis oli, gas trafo, atau mengobrol santai seputar operasional plant.',
  subagent_traces: [],
  timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
}

// Gulir pelan ke dasar feed (ease-out ~900ms) supaya pesan baru terasa "mengalir"
// alih-alih melompat. Menghormati prefers-reduced-motion dengan lompat langsung.
function animateFeedScroll(feed, target) {
  const start = feed.scrollTop
  const distance = target - start
  if (Math.abs(distance) < 2) return
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion) {
    feed.scrollTop = target
    return
  }
  const duration = Math.min(1400, Math.max(600, Math.abs(distance) * 1.2))
  const startTime = performance.now()
  if (feed._scrollRaf) cancelAnimationFrame(feed._scrollRaf)
  const step = (now) => {
    const t = Math.min(1, (now - startTime) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    feed.scrollTop = start + distance * eased
    if (t < 1) feed._scrollRaf = requestAnimationFrame(step)
    else feed._scrollRaf = null
  }
  feed._scrollRaf = requestAnimationFrame(step)
}

function scrollFeedToBottom(feed, fallbackEl) {
  if (!feed) {
    fallbackEl?.scrollIntoView({ behavior: 'smooth' })
    return
  }
  animateFeedScroll(feed, feed.scrollHeight - feed.clientHeight)
}

// Ruang yang disisakan di bawah pertanyaan saat disematkan ke atas: indikator
// "berpikir" (44px) + jarak antar-baris feed.
const PINNED_RESERVE_PX = 96

// Memoized message bubble per Vercel Best Practices (rerender-memo)
const ChatMessageBubble = React.memo(function ChatMessageBubble({
  msg,
  isSpeaking,
  isExpanded,
  isCitationsExpanded,
  onToggleTraces,
  onToggleCitations,
  onSpeak,
  onCopy,
  hasTTS,
  onCreateWo,
  onRetry,
}) {
  const isUser = msg.role === 'user'
  const traceCount = msg.subagent_traces?.length ?? 0
  const citations = msg.citations || []
  const citationCount = citations.length

  return (
    <div className={`chat-bubble-row ${isUser ? 'chat-bubble-row--user' : 'chat-bubble-row--bot'}`}>
      <div className={`chat-avatar ${isUser ? 'chat-avatar--user' : 'chat-avatar--bot'}`}>
        {isUser ? (
          <User size={24} />
        ) : (
          <PlanetaryGear size={44} className="chat-avatar-gear" title="Agent Learning Sistem" />
        )}
      </div>

      <div className={`chat-bubble ${isUser ? 'chat-bubble--user' : 'chat-bubble--bot'} ${msg.safety_blocked ? 'chat-bubble--safety' : ''} ${msg.isError ? 'chat-bubble--error' : ''}`}>
        <div className="chat-bubble__meta">
          <span className="chat-bubble__sender">{isUser ? 'Anda' : 'Agent Learning Sistem'}</span>
          {msg.ai_enhanced ? (
            <span className="badge badge--enhanced" title="Jawaban diperkaya oleh LLM">
              <Sparkles size={11} /> AI Enhanced
            </span>
          ) : null}
          {msg.safety_blocked ? (
            <span className="badge badge--safety" title="Perintah dicegat oleh Safety Guardrail">
              <ShieldAlert size={11} /> Safety Blocked
            </span>
          ) : null}
          <span className="chat-bubble__time">{formatChatTime(msg.timestamp || msg.created_at)}</span>
        </div>

        {msg.file && msg.imagePreviewUrl ? (
          <a
            className="chat-attached-image"
            href={msg.imagePreviewUrl}
            target="_blank"
            rel="noopener noreferrer"
            title={`Buka ${msg.file} ukuran penuh`}
          >
            <img src={msg.imagePreviewUrl} alt={msg.file} loading="lazy" />
          </a>
        ) : msg.file ? (
          <div className="chat-attached-file">
            <FileText size={14} />
            <span>{msg.file}</span>
          </div>
        ) : null}

        <div className="chat-bubble__content">
          <MarkdownRenderer content={msg.text} />
        </div>

        {msg.isError && msg.retryPrompt ? (
          <button
            type="button"
            className="chat-retry-button"
            onClick={() => onRetry && onRetry(msg.retryPrompt)}
            title="Kirim ulang pertanyaan terakhir"
          >
            <RotateCcw size={13} /> Coba lagi
          </button>
        ) : null}

        {/* Matched Equipment Mini Card */}
        {msg.matched_equipment ? (
          <div className="chat-equipment-card">
            <div>
              <span>Peralatan terdeteksi:</span>
              <strong>{msg.matched_equipment}</strong>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Link
                to={`/data`}
                className="chat-equipment-card__link"
                title="Buka detail aset di halaman Data"
              >
                Lihat di Data <ExternalLink size={13} />
              </Link>
              <button
                type="button"
                className="chat-equipment-card__wo-btn"
                onClick={() => onCreateWo && onCreateWo(msg)}
                title="Terbitkan Work Order CBM untuk peralatan ini"
              >
                <ClipboardList size={13} />
                <span>Terbitkan WO CBM</span>
              </button>
            </div>
          </div>
        ) : null}

        {/* Multi-Agent Traces */}
        {traceCount > 0 ? (
          <div className="chat-traces">
            <button
              type="button"
              className="chat-traces__toggle"
              onClick={() => onToggleTraces(msg.id)}
            >
              <span>Bukti 6 Specialist AI Agents ({traceCount})</span>
              {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>

            {isExpanded ? (
              <div className="chat-traces__list">
                {msg.subagent_traces.map((trace, idx) => (
                  <div key={idx} className="trace-item">
                    <div className="trace-item__header">
                      <span className="trace-item__domain">{trace.subagent?.name || 'Agent'}</span>
                      <span className={`status-tag status-tag--${(trace.status || '').toLowerCase()}`}>
                        {trace.status}
                      </span>
                    </div>
                    <p className="trace-item__finding">{trace.key_finding}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* RAG Knowledge Citations Accordion */}
        {citationCount > 0 ? (
          <div className="chat-citations">
            <button
              type="button"
              className="chat-citations__toggle"
              onClick={() => onToggleCitations(msg.id)}
              aria-expanded={isCitationsExpanded}
            >
              <div className="chat-citations__toggle-left">
                <BookOpen size={14} />
                <span>Rujukan Dokumen & Standar CBM ({citationCount})</span>
              </div>
              {isCitationsExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {isCitationsExpanded ? (
              <div className="chat-citations__list">
                {citations.map((cit, idx) => (
                  <div key={idx} className="citation-item">
                    <div className="citation-item__header">
                      <span className="citation-item__badge">{cit.source || 'Materi CBM'}</span>
                      <strong className="citation-item__title">
                        {cit.title} {cit.heading ? `— ${cit.heading}` : ''}
                      </strong>
                    </div>
                    {cit.preview ? (
                      <p className="citation-item__preview">{cit.preview}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {!isUser && !msg.isError ? (
          <div className="chat-bubble__actions">
            {hasTTS ? (
              <button
                type="button"
                className={`bubble-action-btn ${isSpeaking ? 'bubble-action-btn--active' : ''}`}
                onClick={() => onSpeak(msg.id, msg.text, msg.summary_for_speech)}
                title={isSpeaking ? 'Hentikan suara' : 'Dengarkan suara (Ringkasan audio)'}
              >
                <Volume2 size={13} />
                <span>{isSpeaking ? 'Stop Suara' : 'Dengarkan'}</span>
              </button>
            ) : null}
            <button
              type="button"
              className="bubble-action-btn"
              onClick={() => onCopy(msg.text)}
              title="Salin jawaban"
            >
              <Copy size={13} />
              <span>Salin</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
})

// Memoized quick action chips
const QuickActionList = React.memo(function QuickActionList({ onSelect, disabled }) {
  return (
    <div className="chat-quick-actions" aria-label="Pertanyaan cepat">
      {QUICK_ACTIONS.map((action, i) => (
        <button
          key={i}
          type="button"
          className="quick-action-chip"
          onClick={() => onSelect(action.prompt)}
          disabled={disabled}
        >
          {action.label}
        </button>
      ))}
    </div>
  )
})

export default function ChatWorkspace({ onOpenNav }) {
  const { user, logout } = useAuth()
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([defaultWelcomeMessage])
  const messagesRef = useRef(messages)
  messagesRef.current = messages
  // Revoke any image-attachment object URLs on unmount to avoid leaking blob
  // memory over a long-lived session (URL.createObjectURL is per-tab, not
  // per-message, so it must be cleaned up explicitly).
  useEffect(() => () => {
    messagesRef.current.forEach((m) => {
      if (m.imagePreviewUrl) URL.revokeObjectURL(m.imagePreviewUrl)
    })
  }, [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [attachedPreviewUrl, setAttachedPreviewUrl] = useState(null)
  // Build/revoke a preview object URL whenever the composer's attached file
  // changes, so an image thumbnail can be shown before sending.
  useEffect(() => {
    if (attachedFile && attachedFile.type && attachedFile.type.startsWith('image/')) {
      const url = URL.createObjectURL(attachedFile)
      setAttachedPreviewUrl(url)
      return () => URL.revokeObjectURL(url)
    }
    setAttachedPreviewUrl(null)
    return undefined
  }, [attachedFile])
  const [isListening, setIsListening] = useState(false)
  const [speakingId, setSpeakingId] = useState(null)
  const [autoTTS, setAutoTTS] = useState(() => {
    try {
      return localStorage.getItem('pple_auto_tts') === 'true'
    } catch {
      return false
    }
  })
  const [loadingStage, setLoadingStage] = useState(0)
  // Laju putaran logo gear mengikuti kecepatan koneksi + latensi request terakhir.
  const gearDuration = useGearDuration()
  const [expandedTraces, setExpandedTraces] = useState({})
  const [expandedCitations, setExpandedCitations] = useState({})
  const [speechError, setSpeechError] = useState(null)
  const [showScrollBottom, setShowScrollBottom] = useState(false)

  // LLM Full Power active provider & model state
  const [activeProvider, _setActiveProvider] = useState(() => {
    try {
      return localStorage.getItem('pple_chat_provider') || 'gemini'
    } catch {
      return 'gemini'
    }
  })
  const [activeModel, _setActiveModel] = useState(() => {
    try {
      return localStorage.getItem('pple_chat_model') || ''
    } catch {
      return ''
    }
  })

  // Resizable sidebar state per user request (flexible divider)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('pple_chat_sidebar_width')
      const num = Number.parseInt(saved, 10)
      if (!Number.isNaN(num) && num >= 180 && num <= 550) {
        return num
      }
    } catch {}
    return 270
  })
  const [isDragging, setIsDragging] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const { notify } = useToast()

  const handleCreateWoFromChat = useCallback(async (msg) => {
    if (!msg.matched_equipment) return
    try {
      const res = await generateCbmWorkOrder({
        equipment: msg.matched_equipment,
        domain: 'Multi-Agent CBM',
        severity: msg.text?.toLowerCase().includes('critical') || msg.text?.toLowerCase().includes('danger') ? 'CRITICAL' : 'WARNING',
        anomaly_desc: msg.text?.slice(0, 280) || 'Temuan anomali CBM dari Chatbot',
        created_by: 'Chatbot CBM Assistant',
      })
      notify({
        tone: 'success',
        message: `Work Order ${res.work_order?.wo_number} untuk ${msg.matched_equipment} berhasil diterbitkan.`,
        action: { label: 'Buka Work Orders', to: '/work-orders' },
      })
    } catch (err) {
      notify({ tone: 'error', message: `Gagal menerbitkan Work Order: ${err.message}` })
    }
  }, [notify])
  const startXRef = useRef(0)
  const startWidthRef = useRef(sidebarWidth)

  const messagesEndRef = useRef(null)
  const feedRef = useRef(null)
  // Saat agent sedang berpikir, pertanyaan terakhir disematkan ke atas feed
  // (gaya ChatGPT/Claude) supaya indikator reasoning selalu terlihat di bawahnya.
  const pinnedRef = useRef(false)
  const feedSpacerRef = useRef(0)
  const [feedSpacer, setFeedSpacer] = useState(0)
  const chatAbortRef = useRef(null)
  const submitRef = useRef(null)
  const fileInputRef = useRef(null)
  const textareaRef = useRef(null)
  const activeRecognizerRef = useRef(null)

  const hasSTT = isSpeechRecognitionSupported()
  const hasTTS = isSpeechSynthesisSupported()

  const handleTextareaChange = (e) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if ((input.trim() || attachedFile) && !loading) {
        handleSubmit(e)
      }
    }
  }

  // Resizer drag handlers (mouse + touch)
  const handleMouseDown = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
    startXRef.current = e.clientX
    startWidthRef.current = sidebarWidth
  }, [sidebarWidth])

  const handleTouchStart = useCallback((e) => {
    if (e.touches && e.touches[0]) {
      setIsDragging(true)
      startXRef.current = e.touches[0].clientX
      startWidthRef.current = sidebarWidth
    }
  }, [sidebarWidth])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e) => {
      const delta = e.clientX - startXRef.current
      const newWidth = Math.max(180, Math.min(550, startWidthRef.current + delta))
      setSidebarWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      try {
        localStorage.setItem('pple_chat_sidebar_width', String(sidebarWidth))
      } catch {}
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, sidebarWidth])

  useEffect(() => {
    if (!isDragging) return

    const handleTouchMove = (e) => {
      if (e.touches && e.touches[0]) {
        const delta = e.touches[0].clientX - startXRef.current
        const newWidth = Math.max(180, Math.min(550, startWidthRef.current + delta))
        setSidebarWidth(newWidth)
      }
    }

    const handleTouchEnd = () => {
      setIsDragging(false)
      try {
        localStorage.setItem('pple_chat_sidebar_width', String(sidebarWidth))
      } catch {}
    }

    window.addEventListener('touchmove', handleTouchMove, { passive: true })
    window.addEventListener('touchend', handleTouchEnd)
    return () => {
      window.removeEventListener('touchmove', handleTouchMove)
      window.removeEventListener('touchend', handleTouchEnd)
    }
  }, [isDragging, sidebarWidth])

  const handleDoubleClick = useCallback(() => {
    setSidebarWidth(270)
    try {
      localStorage.setItem('pple_chat_sidebar_width', '270')
    } catch {}
  }, [])

  const loadSessionMessages = useCallback(async (sessionId, signal) => {
    try {
      const msgs = await getChatSessionMessages(sessionId, signal)
      if (msgs && msgs.length > 0) {
        setMessages(msgs)
      } else {
        setMessages([defaultWelcomeMessage])
      }
    } catch {
      setMessages([defaultWelcomeMessage])
    }
  }, [])

  // Load chat sessions on mount. Jika belum ada sesi sama sekali, satu sesi dibuat
  // otomatis supaya percakapan pertama tetap tersimpan (tanpa ini, pesan pertama
  // terkirim dengan session_id null dan riwayatnya hilang saat halaman dimuat ulang).
  useEffect(() => {
    const controller = new AbortController()
    getChatSessions(null, controller.signal)
      .then(async (sList) => {
        if (sList && sList.length > 0) {
          setSessions(sList)
          const firstId = sList[0].session_id
          setActiveSessionId(firstId)
          loadSessionMessages(firstId, controller.signal)
          return
        }
        const res = await createNewChatSession({ title: 'Untitled', sessionType: 'chat' })
        if (controller.signal.aborted) return
        setSessions([{
          session_id: res.session_id,
          title: 'Untitled',
          session_type: 'chat',
          status: 'active',
          message_count: 0,
        }])
        setActiveSessionId(res.session_id)
      })
      .catch(() => {})
    return () => controller.abort()
  }, [loadSessionMessages])

  const handleSelectSession = useCallback((sessionId) => {
    stopSpeaking()
    setSpeakingId(null)
    setActiveSessionId(sessionId)
    loadSessionMessages(sessionId)
  }, [loadSessionMessages])

  const handleCreateNewSession = useCallback(async () => {
    stopSpeaking()
    setSpeakingId(null)
    try {
      const res = await createNewChatSession({ title: 'Untitled', sessionType: 'chat' })
      const newSession = {
        session_id: res.session_id,
        title: 'Untitled',
        session_type: 'chat',
        status: 'active',
        message_count: 0,
      }
      setSessions((prev) => [newSession, ...prev])
      setActiveSessionId(res.session_id)
      setMessages([defaultWelcomeMessage])
    } catch (err) {
      console.error('Failed creating session', err)
    }
  }, [])

  const handleDeleteSession = useCallback(async (sessionId) => {
    stopSpeaking()
    try {
      await deleteChatSession(sessionId)
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.session_id !== sessionId)
        if (activeSessionId === sessionId) {
          if (remaining.length > 0) {
            setActiveSessionId(remaining[0].session_id)
            loadSessionMessages(remaining[0].session_id)
          } else {
            handleCreateNewSession()
          }
        }
        return remaining
      })
    } catch (err) {
      console.error('Failed deleting session', err)
    }
  }, [activeSessionId, handleCreateNewSession, loadSessionMessages])

  const handleExportSession = useCallback(() => {
    const active = sessions.find((s) => s.session_id === activeSessionId)
    const title = active ? active.title : 'Obrolan CBM'
    const lines = [
      `# Laporan Percakapan CBM & Diagnosa - PLTU Jeranjang`,
      `**Sesi:** ${title}`,
      `**Waktu Ekspor:** ${new Date().toLocaleString('id-ID')}`,
      `\n---\n`,
    ]
    messages.forEach((m) => {
      const roleName = m.role === 'user' ? '👤 Engineer' : '🤖 Agent Learning Sistem'
      lines.push(`### ${roleName} (${m.timestamp || ''})\n\n${m.text}\n`)
      if (m.matched_equipment) {
        lines.push(`> **Aset Terdeteksi:** ${m.matched_equipment}\n`)
      }
      if (m.subagent_traces && m.subagent_traces.length) {
        lines.push(`**Bukti Specialist Agents:**`)
        m.subagent_traces.forEach((t) => {
          lines.push(`- **${t.subagent?.name || 'Agent'}** [${t.status}]: ${t.key_finding}`)
        })
        lines.push('')
      }
      lines.push('---\n')
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `CBM_Chat_${activeSessionId || 'export'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [activeSessionId, messages, sessions])

  const handleToggleAutoTTS = useCallback(() => {
    setAutoTTS((prev) => {
      const nextVal = !prev
      try {
        localStorage.setItem('pple_auto_tts', String(nextVal))
      } catch {}
      return nextVal
    })
  }, [])

  // Pantau posisi scroll untuk menampilkan tombol 'Pesan terbaru' saat pengguna melihat histori di atas
  const handleFeedScroll = useCallback(() => {
    const feed = feedRef.current
    if (!feed) return
    // Spacer sematan tidak dihitung sebagai "konten di bawah".
    const distanceFromBottom = feed.scrollHeight - feedSpacerRef.current - feed.scrollTop - feed.clientHeight
    setShowScrollBottom(distanceFromBottom > 160)
  }, [])

  const applyFeedSpacer = useCallback((px) => {
    feedSpacerRef.current = px
    setFeedSpacer(px)
  }, [])

  // Begitu loading dimulai: sematkan bubble pertanyaan terakhir ke tepi atas feed
  // dan sisakan ruang kosong di bawahnya agar indikator berpikir tetap terlihat.
  useEffect(() => {
    if (!loading) return undefined
    const feed = feedRef.current
    if (!feed) return undefined
    const rows = feed.querySelectorAll('.chat-bubble-row--user')
    const row = rows[rows.length - 1]
    if (!row) return undefined
    const spacer = Math.max(0, feed.clientHeight - row.offsetHeight - PINNED_RESERVE_PX)
    pinnedRef.current = true
    applyFeedSpacer(spacer)
    // Dua frame: satu agar spacer masuk layout, satu lagi agar tinggi scroll terbarui.
    let raf2 = 0
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        const feedTop = feed.getBoundingClientRect().top
        const rowTop = row.getBoundingClientRect().top
        const paddingTop = parseFloat(getComputedStyle(feed).paddingTop) || 0
        const target = feed.scrollTop + (rowTop - feedTop) - paddingTop
        animateFeedScroll(feed, Math.max(0, target))
      })
    })
    return () => {
      cancelAnimationFrame(raf1)
      cancelAnimationFrame(raf2)
    }
  }, [loading, applyFeedSpacer])

  const scrollToBottom = useCallback(() => {
    pinnedRef.current = false
    if (feedSpacerRef.current) applyFeedSpacer(0)
    requestAnimationFrame(() => scrollFeedToBottom(feedRef.current, messagesEndRef.current))
    setShowScrollBottom(false)
  }, [applyFeedSpacer])

  // Auto-scroll hanya saat pengguna memang sedang berada di dasar percakapan.
  // Tanpa ini, membaca jawaban lama akan terus tertarik ke bawah setiap ada pesan baru.
  useEffect(() => {
    const feed = feedRef.current
    if (messages.length <= 1) {
      // Sesi baru / riwayat dibersihkan: lepaskan sematan.
      pinnedRef.current = false
      if (feedSpacerRef.current) applyFeedSpacer(0)
    }
    // Selama pertanyaan disematkan di atas, jawaban muncul tepat di bawahnya;
    // jangan tarik ke dasar agar pertanyaan + reasoning tetap di posisi semula.
    if (pinnedRef.current) return undefined
    if (!feed) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      return undefined
    }
    const distanceFromBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight
    if (distanceFromBottom < 220) {
      // Tunggu satu frame agar layout pesan baru selesai dihitung sebelum mulai bergulir.
      const raf = requestAnimationFrame(() => scrollFeedToBottom(feed, messagesEndRef.current))
      return () => cancelAnimationFrame(raf)
    }
    return undefined
  }, [messages, loading, applyFeedSpacer])

  // Tahapan kerja agent ditampilkan bergantian supaya penantian LLM terasa hidup
  // dan pengguna tahu proses apa yang sedang berjalan.
  useEffect(() => {
    if (!loading) {
      setLoadingStage(0)
      return
    }
    const timer = setInterval(() => {
      setLoadingStage((prev) => (prev + 1) % LOADING_STAGES.length)
    }, 2600)
    return () => clearInterval(timer)
  }, [loading])

  useEffect(() => {
    return () => {
      stopSpeaking()
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
      }
      if (chatAbortRef.current) {
        chatAbortRef.current.abort()
      }
    }
  }, [])

  const handleSpeak = useCallback((msgId, text, summaryForSpeech = null) => {
    setSpeakingId((prevId) => {
      if (prevId === msgId) {
        stopSpeaking()
        return null
      }
      stopSpeaking()
      const textToSpeak = summaryForSpeech || text
      speakText(textToSpeak, {
        onEnd: () => setSpeakingId(null),
        onError: () => setSpeakingId(null),
      })
      return msgId
    })
  }, [])

  const handleCopy = useCallback((text) => {
    navigator.clipboard.writeText(text)
  }, [])

  const handleClearHistory = useCallback(() => {
    stopSpeaking()
    setSpeakingId(null)
    setMessages([defaultWelcomeMessage])
  }, [])

  const toggleTraces = useCallback((msgId) => {
    setExpandedTraces((prev) => ({ ...prev, [msgId]: !prev[msgId] }))
  }, [])

  const toggleCitations = useCallback((msgId) => {
    setExpandedCitations((prev) => ({ ...prev, [msgId]: !prev[msgId] }))
  }, [])

  const handleSubmit = async (e, directText = null, fromVoice = false) => {
    if (e) e.preventDefault()
    const query = (directText !== null ? directText : input).trim()
    if (!query && !attachedFile) return

    const userMessageId = `user-${Date.now()}`
    const isImageAttachment = Boolean(attachedFile && attachedFile.type && attachedFile.type.startsWith('image/'))
    const userMsg = {
      id: userMessageId,
      role: 'user',
      text: query,
      file: attachedFile ? attachedFile.name : null,
      imagePreviewUrl: isImageAttachment ? URL.createObjectURL(attachedFile) : null,
      fromVoice,
      timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    const currentFile = attachedFile
    setAttachedFile(null)
    setLoading(true)
    setSpeechError(null)

    const controller = new AbortController()
    chatAbortRef.current = controller
    const startedAt = performance.now()

    try {
      const response = await sendChatMessage({
        message: query,
        file: currentFile,
        source: fromVoice ? 'VOICE' : 'CHAT',
        sessionId: activeSessionId,
        provider: activeProvider,
        model: activeModel || undefined,
        signal: controller.signal,
      })

      // If active session was Untitled, update its title in UI state
      if (activeSessionId) {
        setSessions((prev) =>
          prev.map((s) => {
            if (s.session_id === activeSessionId && (!s.title || s.title === 'Untitled')) {
              const clean = query.slice(0, 32).trim() + (query.length > 32 ? '...' : '')
              return { ...s, title: clean }
            }
            return s
          })
        )
      }

      const botMessageId = `bot-${Date.now()}`
      const botMessage = {
        id: botMessageId,
        role: 'assistant',
        text: response.reply || 'Tidak ada balasan dari sistem.',
        summary_for_speech: response.summary_for_speech,
        matched_equipment: response.matched_equipment,
        ai_enhanced: response.ai_enhanced,
        provider: response.provider || activeProvider,
        model: response.model || activeModel,
        safety_blocked: response.safety_blocked,
        subagent_traces: response.subagent_traces || [],
        active_subagents: response.active_subagents || [],
        citations: response.citations || [],
        timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
      }

      setMessages((prev) => [...prev, botMessage])

      // Text-to-Speech logic:
      // 1. Safety Guardrail Override: always barge-in and speak immediately regardless of settings
      if (response.safety_blocked && hasTTS) {
        stopSpeaking()
        handleSpeak(botMessageId, response.reply, response.summary_for_speech)
      } else if ((fromVoice || autoTTS) && hasTTS && (response.summary_for_speech || response.reply)) {
        // 2. Context-aware: voice input auto-reads; text input honors manual autoTTS toggle
        handleSpeak(botMessageId, response.reply, response.summary_for_speech)
      }
    } catch (err) {
      const cancelled = err.name === 'AbortError'
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          isError: true,
          text: cancelled
            ? 'Permintaan dihentikan sebelum agent selesai menjawab.'
            : `Gagal berkomunikasi dengan server: ${err.message}. Pastikan backend FastAPI aktif di port 8000.`,
          retryPrompt: cancelled ? null : query,
          timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      // Request yang gagal pun ikut dicatat: koneksi lambat justru sering
      // terlihat dari permintaan yang menggantung lama sebelum menyerah.
      recordLatency(performance.now() - startedAt)
      chatAbortRef.current = null
      setLoading(false)
    }
  }

  // Identitas handleRetry dijaga stabil (lewat ref) agar React.memo pada bubble pesan
  // tidak batal dan seluruh riwayat tidak ikut render ulang setiap ada pesan baru.
  const handleRetry = useCallback((prompt) => {
    if (prompt) submitRef.current?.(null, prompt)
  }, [])

  submitRef.current = handleSubmit

  const handleToggleVoice = () => {
    if (!hasSTT) {
      setSpeechError('Browser ini (mis. Safari) belum mendukung Speech Recognition. Silakan ketik langsung atau gunakan Chrome/Edge.')
      return
    }

    if (isListening) {
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.stop()
      }
      setIsListening(false)
      return
    }

    setSpeechError(null)
    stopSpeaking()
    setSpeakingId(null)

    activeRecognizerRef.current = startSpeechRecognition({
      onStart: () => setIsListening(true),
      onEnd: () => {
        setIsListening(false)
        activeRecognizerRef.current = null
      },
      onError: (msg) => {
        setSpeechError(msg)
        setIsListening(false)
        activeRecognizerRef.current = null
      },
      onResult: (transcript, isFinal) => {
        setInput(transcript)
        if (isFinal && transcript.trim().length > 3) {
          setTimeout(() => {
            handleSubmit(null, transcript.trim(), true)
          }, 250)
        }
      },
    })
  }

  return (
    <div className={`page chat-page-layout ${isDragging ? 'chat-page-layout--dragging' : ''}`}>
      {/* Left Column: Chat and Task History Panel (Flexible Resizable) */}
      {!isCollapsed ? (
        <div
          className="chat-history-column"
          style={{ width: `${sidebarWidth}px`, flexShrink: 0 }}
        >
          <ChatHistoryPanel
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onCreateNewSession={handleCreateNewSession}
            onDeleteSession={handleDeleteSession}
            onExportSession={handleExportSession}
            onOpenNav={onOpenNav}
            onToggleCollapse={() => setIsCollapsed(true)}
            user={user}
            onLogout={logout}
            onSelectPrompt={(prompt) => handleSubmit(null, prompt)}
          />
        </div>
      ) : null}

      {/* Flexible Resizable Divider Line */}
      {!isCollapsed ? (
        <div
          className={`chat-resizer ${isDragging ? 'chat-resizer--active' : ''}`}
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
          onDoubleClick={handleDoubleClick}
          title="Geser garis untuk mengatur lebar panel (Klik ganda untuk reset 270px)"
          role="separator"
          aria-orientation="vertical"
          aria-valuenow={sidebarWidth}
          aria-valuemin={180}
          aria-valuemax={550}
        >
          <div className="chat-resizer__line" />
        </div>
      ) : null}

      {/* Right Column: Active Conversation Window */}
      <div className="chat-main-column">
        <header className="page-header chat-header">
          <div className="chat-header__main-info">
            {isCollapsed ? (
              <div className="chat-collapsed-controls">
                {onOpenNav ? (
                  <button
                    type="button"
                    className="icon-button-subtle"
                    onClick={onOpenNav}
                    title="Buka menu navigasi utama PPLE"
                    aria-label="Menu navigasi"
                  >
                    <Menu size={17} />
                  </button>
                ) : null}
                <button
                  type="button"
                  className="icon-button-subtle"
                  onClick={() => setIsCollapsed(false)}
                  title="Tampilkan panel riwayat (Obrolan dan tugas)"
                  aria-label="Buka riwayat"
                >
                  <PanelLeftOpen size={17} />
                </button>
              </div>
            ) : null}
            <div className="chat-header-session-title">
              <div className="chat-title-row">
                <h1 className="chat-title-claude" title="Sesi obrolan aktif">
                  {sessions.find((s) => s.session_id === activeSessionId)?.title || 'Percakapan baru'}
                </h1>
                <ChevronDown size={15} className="chat-title-chevron" />
                <span className="badge badge--ai"><Sparkles size={12} /> Multi-Agent CBM</span>
              </div>
            </div>
          </div>

          <div className="chat-header__controls">
            {hasTTS ? (
              <button
                type="button"
                className={`tts-toggle-button ${autoTTS ? 'tts-toggle-button--active' : ''}`}
                onClick={handleToggleAutoTTS}
                title={autoTTS ? 'Auto baca suara aktif (Klik untuk nonaktifkan)' : 'Auto baca suara nonaktif (Klik untuk aktifkan)'}
              >
                {autoTTS ? <Volume2 size={16} /> : <VolumeX size={16} />}
                <span>{autoTTS ? 'Auto-Voice ON' : 'Auto-Voice OFF'}</span>
              </button>
            ) : null}

            <button
              type="button"
              className="icon-button"
              onClick={handleExportSession}
              title="Ekspor Ringkasan Sesi (.md)"
              aria-label="Ekspor Laporan Sesi"
            >
              <Download size={16} />
            </button>

            <button
              type="button"
              className="icon-button"
              onClick={handleClearHistory}
              title="Bersihkan riwayat"
              aria-label="Bersihkan riwayat"
            >
              <RotateCcw size={17} />
            </button>
          </div>
        </header>

        {!hasSTT ? (
          <div className="notice notice--neutral" role="status">
            <span>Browser Anda belum mendukung input suara Web Speech (misal pada Safari). Anda tetap dapat berinteraksi penuh melalui teks, atau gunakan Google Chrome / Microsoft Edge untuk fitur suara hands-free.</span>
          </div>
        ) : null}

        {speechError ? (
          <div className="notice notice--error" role="alert">
            <AlertTriangle size={17} />
            <span>{speechError}</span>
            <button className="icon-button-subtle" onClick={() => setSpeechError(null)}><X size={14} /></button>
          </div>
        ) : null}

        {/* Main chat window */}
        <div className="chat-container">
          <div
            className="chat-feed"
            role="log"
            aria-live="polite"
            ref={feedRef}
            onScroll={handleFeedScroll}
          >
            {messages.map((msg) => (
              <ChatMessageBubble
                key={msg.id}
                msg={msg}
                isSpeaking={speakingId === msg.id}
                isExpanded={Boolean(expandedTraces[msg.id])}
                isCitationsExpanded={Boolean(expandedCitations[msg.id])}
                onToggleTraces={toggleTraces}
                onToggleCitations={toggleCitations}
                onSpeak={handleSpeak}
                onCopy={handleCopy}
                hasTTS={hasTTS}
                onCreateWo={handleCreateWoFromChat}
                onRetry={handleRetry}
              />
            ))}

            {loading ? (
              <div className="claude-thinking-row" role="status" aria-live="polite">
                <div className="claude-thinking-content">
                  <PlanetaryGear
                    size={44}
                    spinning
                    style={{ '--pg-dur': `${gearDuration}s` }}
                  />
                  <span className="claude-thinking-text">
                    {LOADING_STAGES[loadingStage]}
                    <span className="claude-cursor">_</span>
                  </span>
                </div>
              </div>
            ) : null}

            <div ref={messagesEndRef} style={{ flexShrink: 0, height: feedSpacer }} aria-hidden="true" />
          </div>

          {/* Floating Scroll to Bottom Button */}
          {showScrollBottom ? (
            <button
              type="button"
              className="chat-scroll-bottom-btn"
              onClick={scrollToBottom}
              title="Gulir ke pesan terbaru"
              aria-label="Kembali ke pesan terbaru"
            >
              <ChevronDown size={14} />
              <span>Pesan terbaru</span>
            </button>
          ) : null}

          {/* Quick Action Chips (Memoized) */}
          {messages.length <= 1 ? (
            <QuickActionList
              onSelect={(prompt) => handleSubmit(null, prompt)}
              disabled={loading || isListening}
            />
          ) : null}

          {/* Input area */}
          <form className="chat-input-box" onSubmit={handleSubmit}>
            {attachedFile ? (
              <div className="chat-file-preview">
                {attachedPreviewUrl ? (
                  <img className="chat-file-preview__thumb" src={attachedPreviewUrl} alt={attachedFile.name} />
                ) : (
                  <FileText size={14} />
                )}
                <span>{attachedFile.name}</span>
                <button
                  type="button"
                  className="icon-button-subtle"
                  onClick={() => setAttachedFile(null)}
                  title="Hapus file"
                >
                  <X size={13} />
                </button>
              </div>
            ) : null}

            <div className="chat-input-composer">
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setAttachedFile(e.target.files[0])
                  }
                }}
              />

              {isListening ? (
                <div className="chat-voice-wave" aria-live="polite">
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="wave-bar" />
                  <span className="voice-wave-text">Mendengarkan bahasa Indonesia...</span>
                </div>
              ) : (
                <textarea
                  ref={textareaRef}
                  rows={1}
                  className="chat-textarea"
                  placeholder="Ketik pertanyaan atau perintah CBM... (Enter untuk kirim, Shift+Enter untuk baris baru)"
                  value={input}
                  onChange={handleTextareaChange}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                />
              )}

              <div className="chat-input-toolbar">
                <div className="chat-input-toolbar__left">
                  <button
                    type="button"
                    className="chat-action-button"
                    onClick={() => fileInputRef.current?.click()}
                    title="Lampirkan dokumen/file log"
                    aria-label="Lampirkan file"
                    disabled={loading}
                  >
                    <Paperclip size={16} />
                  </button>

                  {hasSTT ? (
                    <button
                      type="button"
                      className={`chat-mic-button ${isListening ? 'chat-mic-button--listening' : ''}`}
                      onClick={handleToggleVoice}
                      title={isListening ? 'Berhenti mendengarkan' : 'Bicara dengan mikrofon'}
                      aria-label={isListening ? 'Berhenti mendengarkan' : 'Bicara dengan mikrofon'}
                      disabled={loading}
                    >
                      {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                    </button>
                  ) : null}
                </div>

                <div className="chat-input-toolbar__right">
                  <span className="chat-input-hint">↵ Kirim</span>
                  <button
                    type="submit"
                    className="chat-send-button"
                    disabled={loading || (!input.trim() && !attachedFile)}
                    title="Kirim pesan"
                    aria-label="Kirim pesan"
                  >
                    <Send size={15} />
                  </button>
                </div>
              </div>
            </div>
          </form>

          <div className="chat-disclaimer-claude">
            Agent Learning Sistem dapat membuat kekeliruan. Selalu verifikasi data sensor aktual dan ikuti SOP keselamatan plant sebelum tindakan pemeliharaan.
          </div>
        </div>
      </div>
    </div>
  )
}
