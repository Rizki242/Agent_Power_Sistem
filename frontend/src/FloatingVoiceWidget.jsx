import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  ExternalLink,
  Headphones,
  Mic,
  MicOff,
  Radio,
  Sparkles,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { sendChatMessage } from './api.js'
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speakText,
  startSpeechRecognition,
  stopSpeaking,
} from './utils/speech.js'

const FIELD_INSPECTION_PRESETS = [
  { label: 'BFP 1A & 1B', query: 'Status dan vibrasi BFP 1A dan 1B' },
  { label: 'Trafo Unit 1 (DGA)', query: 'Status gas DGA transformator Unit 1' },
  { label: 'CWP & Pompa', query: 'Kondisi getaran pompa CWP Unit 1' },
  { label: 'Peralatan Alarm', query: 'Daftar semua peralatan status alarm atau warning saat ini' },
  { label: 'Rekomendasi CBM', query: 'Rekomendasi tindakan CBM prioritas hari ini' },
]

export default function FloatingVoiceWidget() {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [reply, setReply] = useState(null)
  const [loading, setLoading] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState(null)
  const [handsFree, setHandsFree] = useState(false)
  const [countdown, setCountdown] = useState(0)

  const activeRecognizerRef = useRef(null)
  const handsFreeRef = useRef(false)
  const countdownTimerRef = useRef(null)
  const hasSTT = isSpeechRecognitionSupported()
  const hasTTS = isSpeechSynthesisSupported()

  const isChatRoute = location.pathname === '/chat'

  useEffect(() => {
    handsFreeRef.current = handsFree
  }, [handsFree])

  useEffect(() => {
    return () => {
      stopSpeaking()
      if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
      }
    }
  }, [])

  useEffect(() => {
    if (isChatRoute) {
      stopSpeaking()
      if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
      }
      setIsOpen(false)
      setIsListening(false)
      setSpeaking(false)
      setHandsFree(false)
    }
  }, [isChatRoute])

  const handleOpen = () => {
    setIsOpen(true)
    setError(null)
  }

  const handleClose = () => {
    setIsOpen(false)
    stopSpeaking()
    setSpeaking(false)
    setHandsFree(false)
    if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
    if (activeRecognizerRef.current) {
      activeRecognizerRef.current.abort()
    }
    setIsListening(false)
  }

  const startListeningSession = () => {
    if (!hasSTT) {
      setError('Browser ini belum mendukung voice recognition langsung. Gunakan Chrome/Edge.')
      return
    }

    setError(null)
    stopSpeaking()
    setSpeaking(false)
    if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
    setCountdown(0)

    if (activeRecognizerRef.current) {
      try { activeRecognizerRef.current.abort() } catch {}
    }

    activeRecognizerRef.current = startSpeechRecognition({
      onStart: () => setIsListening(true),
      onEnd: () => {
        setIsListening(false)
        activeRecognizerRef.current = null
      },
      onError: (err) => {
        setError(err)
        setIsListening(false)
        activeRecognizerRef.current = null
        if (handsFreeRef.current) {
          // If error was silence, retry after a pause in hands-free mode
          scheduleNextListeningCycle(2000)
        }
      },
      onResult: (text, isFinal) => {
        setTranscript(text)
        if (isFinal && text.trim().length > 3) {
          executeAsk(text.trim())
        }
      },
    })
  }

  const handleToggleListening = () => {
    if (isListening) {
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.stop()
      }
      setIsListening(false)
      return
    }
    startListeningSession()
  }

  const scheduleNextListeningCycle = (delayMs = 1200) => {
    if (!handsFreeRef.current) return
    setCountdown(Math.ceil(delayMs / 1000))
    if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
    countdownTimerRef.current = setTimeout(() => {
      setCountdown(0)
      if (handsFreeRef.current) {
        startListeningSession()
      }
    }, delayMs)
  }

  const executeAsk = async (queryText) => {
    if (!queryText) return
    setLoading(true)
    setError(null)
    setReply(null)
    stopSpeaking()
    setSpeaking(false)
    if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
    setCountdown(0)

    try {
      const res = await sendChatMessage({ message: queryText, source: 'VOICE' })
      setReply(res)

      // Use concise, phonetic speech summary for natural Indonesian TTS
      const textToSpeak = res.summary_for_speech || res.reply
      if (hasTTS && textToSpeak) {
        setSpeaking(true)
        speakText(textToSpeak, {
          onEnd: () => {
            setSpeaking(false)
            if (handsFreeRef.current) {
              scheduleNextListeningCycle(1400)
            }
          },
          onError: () => {
            setSpeaking(false)
            if (handsFreeRef.current) {
              scheduleNextListeningCycle(1800)
            }
          },
        })
      } else if (handsFreeRef.current) {
        scheduleNextListeningCycle(1500)
      }
    } catch (err) {
      setError(err.message || 'Gagal terhubung ke backend')
      if (handsFreeRef.current) {
        scheduleNextListeningCycle(3000)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStopSpeaking = () => {
    stopSpeaking()
    setSpeaking(false)
  }

  const handleReplaySpeech = () => {
    if (!reply) return
    stopSpeaking()
    setSpeaking(true)
    const textToSpeak = reply.summary_for_speech || reply.reply
    speakText(textToSpeak, {
      onEnd: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    })
  }

  const toggleHandsFree = () => {
    const nextVal = !handsFree
    setHandsFree(nextVal)
    handsFreeRef.current = nextVal
    if (!nextVal) {
      if (countdownTimerRef.current) clearTimeout(countdownTimerRef.current)
      setCountdown(0)
    } else if (!isListening && !speaking && !loading) {
      startListeningSession()
    }
  }

  // Hide the floating widget on the full /chat page to avoid visual redundancy
  if (isChatRoute) {
    return null
  }

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen ? (
        <button
          type="button"
          className="floating-voice-btn"
          onClick={handleOpen}
          title="Buka Asisten Suara CBM Lapangan"
          aria-label="Buka Asisten Suara CBM Lapangan"
        >
          <div className="floating-voice-btn__pulse" />
          <Mic size={22} />
          <span className="floating-voice-btn__label">Tanya Suara</span>
        </button>
      ) : null}

      {/* Floating Dialog / Drawer */}
      {isOpen ? (
        <div className="floating-voice-card" role="dialog" aria-label="Asisten Suara CBM">
          <div className="floating-voice-header">
            <div className="floating-voice-header__title">
              <Bot size={19} />
              <div>
                <strong>Voice Assistant CBM</strong>
                <span className="floating-voice-header__sub">PLTU Jeranjang (3 × 25 MW)</span>
              </div>
            </div>
            <div className="floating-voice-header__actions">
              <button
                type="button"
                className={`icon-button-subtle ${handsFree ? 'handsfree-active-btn' : ''}`}
                onClick={toggleHandsFree}
                title={handsFree ? 'Matikan Mode Hands-Free' : 'Aktifkan Mode Hands-Free Inspeksi'}
              >
                <Headphones size={16} />
              </button>
              <Link
                to="/chat"
                className="icon-button-subtle"
                onClick={handleClose}
                title="Buka Halaman Chat Lengkap"
              >
                <ExternalLink size={15} />
              </Link>
              <button
                type="button"
                className="icon-button-subtle"
                onClick={handleClose}
                aria-label="Tutup"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Hands-free mode banner */}
          {handsFree ? (
            <div className="handsfree-banner">
              <Radio size={14} className="handsfree-pulse-icon" />
              <span>
                <strong>Mode Hands-Free Lapangan Aktif</strong> — Otomatis mendengarkan kembali setelah asisten selesai berbicara.
              </span>
            </div>
          ) : null}

          <div className="floating-voice-body">
            {error ? (
              <div className="floating-voice-error">
                <span>{error}</span>
              </div>
            ) : null}

            {!reply && !loading && !isListening && countdown === 0 ? (
              <div className="floating-voice-intro">
                <p>Ucapkan nama peralatan atau pilih shortcut inspeksi lapangan:</p>
                <div className="floating-voice-examples">
                  {FIELD_INSPECTION_PRESETS.map((item, idx) => (
                    <button key={idx} type="button" onClick={() => executeAsk(item.query)}>
                      "{item.label}"
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {countdown > 0 ? (
              <div className="floating-voice-countdown">
                <div className="countdown-ring">
                  <span>{countdown}s</span>
                </div>
                <p>Bersiap mendengarkan pertanyaan berikutnya...</p>
              </div>
            ) : null}

            {isListening ? (
              <div className="floating-voice-listening">
                <div className="voice-rings">
                  <span className="ring" />
                  <span className="ring" />
                </div>
                <div className="floating-wave-bars">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <span className="listening-label">Mendengarkan bahasa Indonesia...</span>
                <p className="listening-text">{transcript || 'Katakan instruksi atau nama mesin...'}</p>
              </div>
            ) : null}

            {loading ? (
              <div className="floating-voice-loading">
                <Sparkles size={20} className="spin-slow" />
                <span>Menganalisis data CBM lintas 6 specialist agent...</span>
              </div>
            ) : null}

            {reply && !loading ? (
              <div className="floating-voice-response">
                <div className="floating-voice-response__meta">
                  <div className="floating-voice-response__meta-left">
                    <span>Jawaban Asisten CBM:</span>
                  </div>
                  <div className="floating-voice-response__meta-right">
                    {speaking ? (
                      <button
                        type="button"
                        className="speech-btn speech-btn--speaking"
                        onClick={handleStopSpeaking}
                        title="Hentikan pembacaan suara"
                      >
                        <VolumeX size={13} />
                        <span>Hentikan Suara</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="speech-btn"
                        onClick={handleReplaySpeech}
                        title="Putar ulang suara ringkasan CBM"
                      >
                        <Volume2 size={13} />
                        <span>Putar Ulang</span>
                      </button>
                    )}
                  </div>
                </div>

                {speaking ? (
                  <div className="voice-speaking-indicator">
                    <div className="mini-wave-bars">
                      <span /><span /><span /><span />
                    </div>
                    <span>Menyuarakan rekomendasi teknis...</span>
                  </div>
                ) : null}

                <p className="floating-voice-response__text">
                  {reply.reply}
                </p>

                {reply.matched_equipment ? (
                  <div className="floating-voice-equipment">
                    <span>Aset Terdeteksi: <strong>{reply.matched_equipment}</strong></span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="floating-voice-footer">
            <div className="floating-voice-footer__ctrls">
              <button
                type="button"
                className={`voice-mic-main ${isListening ? 'voice-mic-main--active' : ''}`}
                onClick={handleToggleListening}
                title={isListening ? 'Berhenti mendengar' : 'Mulai bicara'}
              >
                {isListening ? <MicOff size={22} /> : <Mic size={22} />}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

