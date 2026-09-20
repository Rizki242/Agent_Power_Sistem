import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  BookOpen,
  Bot,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Copy,
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
import {
  createNewChatSession,
  deleteChatSession,
  generateCbmWorkOrder,
  getChatSessionMessages,
  getChatSessions,
  sendChatMessage,
} from './api.js'
import ChatHistoryPanel from './ChatHistoryPanel.jsx'
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
  text: 'Halo! Saya **Agent CBM Learning PLTU Jeranjang** (PPLE Agent).\n\nSaya memadukan analisa 6 spesialis (*Vibrasi, MCSA, DGA, Partial Discharge, Tribologi, Thermal*), Safety Guardrail, dan pengetahuan unit PLTU Jeranjang (3 × 25 MW).\n\nAnda dapat menanyakan kondisi mesin, tren getaran, analisis oli, gas trafo, atau mengobrol santai seputar operasional plant.',
  subagent_traces: [],
  timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
}

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
}) {
  const isUser = msg.role === 'user'
  const traceCount = msg.subagent_traces?.length ?? 0
  const citations = msg.citations || []
  const citationCount = citations.length

  return (
    <div className={`chat-bubble-row ${isUser ? 'chat-bubble-row--user' : 'chat-bubble-row--bot'}`}>
      <div className={`chat-avatar ${isUser ? 'chat-avatar--user' : 'chat-avatar--bot'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className={`chat-bubble ${isUser ? 'chat-bubble--user' : 'chat-bubble--bot'} ${msg.safety_blocked ? 'chat-bubble--safety' : ''} ${msg.isError ? 'chat-bubble--error' : ''}`}>
        <div className="chat-bubble__meta">
          <span className="chat-bubble__sender">{isUser ? 'Anda' : 'PPLE Agent'}</span>
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

        {msg.file ? (
          <div className="chat-attached-file">
            <FileText size={14} />
            <span>{msg.file}</span>
          </div>
        ) : null}

        <div className="chat-bubble__content">
          <MarkdownRenderer content={msg.text} />
        </div>

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
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([defaultWelcomeMessage])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [isListening, setIsListening] = useState(false)
  const [speakingId, setSpeakingId] = useState(null)
  const [autoTTS, setAutoTTS] = useState(() => {
    try {
      return localStorage.getItem('pple_auto_tts') === 'true'
    } catch {
      return false
    }
  })
  const [expandedTraces, setExpandedTraces] = useState({})
  const [expandedCitations, setExpandedCitations] = useState({})
  const [speechError, setSpeechError] = useState(null)

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
  const [woNotification, setWoNotification] = useState(null)

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
      setWoNotification({
        woNumber: res.work_order?.wo_number,
        equipment: msg.matched_equipment,
        title: res.work_order?.title,
      })
    } catch (err) {
      alert(`Gagal menerbitkan Work Order: ${err.message}`)
    }
  }, [])
  const startXRef = useRef(0)
  const startWidthRef = useRef(sidebarWidth)

  const messagesEndRef = useRef(null)
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

  // Load chat sessions on mount
  useEffect(() => {
    const controller = new AbortController()
    getChatSessions(null, controller.signal)
      .then((sList) => {
        if (sList && sList.length > 0) {
          setSessions(sList)
          const firstId = sList[0].session_id
          setActiveSessionId(firstId)
          loadSessionMessages(firstId, controller.signal)
        }
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
      const roleName = m.role === 'user' ? '👤 Engineer' : '🤖 PPLE CBM Agent'
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  useEffect(() => {
    return () => {
      stopSpeaking()
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
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
    const userMsg = {
      id: userMessageId,
      role: 'user',
      text: query,
      file: attachedFile ? attachedFile.name : null,
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

    try {
      const response = await sendChatMessage({
        message: query,
        file: currentFile,
        source: fromVoice ? 'VOICE' : 'CHAT',
        sessionId: activeSessionId,
        provider: activeProvider,
        model: activeModel || undefined,
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
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          isError: true,
          text: `Gagal berkomunikasi dengan server: ${err.message}. Pastikan backend FastAPI aktif di port 8000.`,
          timestamp: new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

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
            userName="Rizki"
            userRole="Engineer"
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
            <div>
              <div className="chat-title-row">
                <h1>Power Learning</h1>
                <span className="badge badge--ai"><Sparkles size={13} /> Multi-Agent CBM</span>
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

        {woNotification ? (
          <div
            className="notice notice--success"
            style={{
              margin: '0 20px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ClipboardList size={18} style={{ color: '#10b981' }} />
              <span>
                Work Order <strong>{woNotification.woNumber}</strong> untuk{' '}
                <strong>{woNotification.equipment}</strong> berhasil diterbitkan!
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Link to="/work-orders" className="button button--small button--primary" style={{ textDecoration: 'none' }}>
                Buka di Work Orders <ExternalLink size={13} />
              </Link>
              <button
                type="button"
                className="icon-button-subtle"
                onClick={() => setWoNotification(null)}
                aria-label="Tutup notifikasi"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        ) : null}

        {/* Main chat window */}
        <div className="chat-container">
          <div className="chat-feed" role="log" aria-live="polite">
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
              />
            ))}

            {loading ? (
              <div className="chat-bubble-row chat-bubble-row--bot">
                <div className="chat-avatar chat-avatar--bot">
                  <Bot size={18} />
                </div>
                <div className="chat-bubble chat-bubble--bot chat-bubble--loading">
                  <div className="chat-typing-indicator">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span className="chat-typing-text">Menghubungi specialist agents & memeriksa safety...</span>
                </div>
              </div>
            ) : null}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Chips (Memoized) */}
          <QuickActionList
            onSelect={(prompt) => handleSubmit(null, prompt)}
            disabled={loading || isListening}
          />

          {/* Input area */}
          <form className="chat-input-box" onSubmit={handleSubmit}>
            {attachedFile ? (
              <div className="chat-file-preview">
                <FileText size={14} />
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
        </div>
      </div>
    </div>
  )
}
