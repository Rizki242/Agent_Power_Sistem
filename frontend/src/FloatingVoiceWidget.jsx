import { useEffect, useRef, useState } from 'react'
import { Bot, ExternalLink, Mic, MicOff, Sparkles, Volume2, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { sendChatMessage } from './api.js'
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speakText,
  startSpeechRecognition,
  stopSpeaking,
} from './utils/speech.js'

export default function FloatingVoiceWidget() {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [reply, setReply] = useState(null)
  const [loading, setLoading] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState(null)

  const activeRecognizerRef = useRef(null)
  const hasSTT = isSpeechRecognitionSupported()
  const hasTTS = isSpeechSynthesisSupported()

  const isChatRoute = location.pathname === '/chat'

  useEffect(() => {
    return () => {
      stopSpeaking()
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
      }
    }
  }, [])

  useEffect(() => {
    if (isChatRoute) {
      stopSpeaking()
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.abort()
      }
      setIsOpen(false)
      setIsListening(false)
      setSpeaking(false)
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
    if (activeRecognizerRef.current) {
      activeRecognizerRef.current.abort()
    }
    setIsListening(false)
  }

  const handleToggleListening = () => {
    if (!hasSTT) {
      setError('Browser ini (mis. Safari) belum mendukung voice recognition langsung. Gunakan Chrome/Edge atau buka halaman Chat untuk teks.')
      return
    }

    if (isListening) {
      if (activeRecognizerRef.current) {
        activeRecognizerRef.current.stop()
      }
      setIsListening(false)
      return
    }

    setError(null)
    stopSpeaking()
    setSpeaking(false)

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
      },
      onResult: (text, isFinal) => {
        setTranscript(text)
        if (isFinal && text.trim().length > 3) {
          executeAsk(text.trim())
        }
      },
    })
  }

  const executeAsk = async (queryText) => {
    if (!queryText) return
    setLoading(true)
    setError(null)
    setReply(null)
    stopSpeaking()
    setSpeaking(false)

    try {
      const res = await sendChatMessage({ message: queryText, source: 'VOICE' })
      setReply(res)

      // Use concise, phonetic speech summary for natural Indonesian TTS
      const textToSpeak = res.summary_for_speech || res.reply
      if (hasTTS && textToSpeak) {
        setSpeaking(true)
        speakText(textToSpeak, {
          onEnd: () => setSpeaking(false),
          onError: () => setSpeaking(false),
        })
      }
    } catch (err) {
      setError(err.message || 'Gagal terhubung ke backend')
    } finally {
      setLoading(false)
    }
  }

  const handleStopSpeaking = () => {
    stopSpeaking()
    setSpeaking(false)
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
          title="Buka Asisten Suara CBM"
          aria-label="Buka Asisten Suara CBM"
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
              <strong>Voice Assistant CBM</strong>
            </div>
            <div className="floating-voice-header__actions">
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

          <div className="floating-voice-body">
            {error ? (
              <div className="floating-voice-error">
                <span>{error}</span>
              </div>
            ) : null}

            {!reply && !loading && !isListening ? (
              <div className="floating-voice-intro">
                <p>Klik tombol mikrofon untuk bertanya kondisi mesin atau peralatan PLTU Jeranjang.</p>
                <div className="floating-voice-examples">
                  <button type="button" onClick={() => executeAsk('Status CWP 1A')}>
                    "Status CWP 1A"
                  </button>
                  <button type="button" onClick={() => executeAsk('Daftar peralatan alarm')}>
                    "Daftar peralatan alarm"
                  </button>
                  <button type="button" onClick={() => executeAsk('Kondisi trafo GT 1')}>
                    "Kondisi trafo GT 1"
                  </button>
                </div>
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
                <span className="listening-label">Mendengarkan...</span>
                <p className="listening-text">{transcript || 'Katakan pertanyaan Anda...'}</p>
              </div>
            ) : null}

            {loading ? (
              <div className="floating-voice-loading">
                <Sparkles size={20} className="spin-slow" />
                <span>Menganalisis data CBM lintas 6 agent...</span>
              </div>
            ) : null}

            {reply && !loading ? (
              <div className="floating-voice-response">
                <div className="floating-voice-response__meta">
                  <span>Jawaban Agent:</span>
                  {speaking ? (
                    <button
                      type="button"
                      className="speech-btn speech-btn--speaking"
                      onClick={handleStopSpeaking}
                      title="Hentikan pembacaan suara"
                    >
                      <Volume2 size={13} />
                      <span>Berbicara...</span>
                    </button>
                  ) : null}
                </div>
                <p className="floating-voice-response__text">
                  {reply.reply}
                </p>
                {reply.matched_equipment ? (
                  <div className="floating-voice-equipment">
                    <span>Aset: <strong>{reply.matched_equipment}</strong></span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="floating-voice-footer">
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
      ) : null}
    </>
  )
}
