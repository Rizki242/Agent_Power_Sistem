/**
 * Web Speech API Utilities for PPLE Agent (Indonesian - id-ID)
 * Provides client-side Speech-to-Text (STT) and Text-to-Speech (TTS)
 * with zero external dependencies and zero cloud cost.
 */

const SpeechRecognition = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition || null)
  : null

export function isSpeechRecognitionSupported() {
  return Boolean(SpeechRecognition)
}

export function isSpeechSynthesisSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

/**
 * Creates and starts a SpeechRecognition instance.
 * @param {Object} options
 * @param {function(string, boolean): void} options.onResult - (transcript, isFinal)
 * @param {function(string): void} options.onError - (errorMessage)
 * @param {function(): void} options.onStart - Called when mic starts listening
 * @param {function(): void} options.onEnd - Called when mic stops listening
 * @returns {{ stop: function(): void, abort: function(): void }}
 */
export function startSpeechRecognition({ onResult, onError, onStart, onEnd }) {
  if (!SpeechRecognition) {
    if (onError) onError('Browser tidak mendukung Speech Recognition (Gunakan Chrome atau Edge).')
    return { stop: () => {}, abort: () => {} }
  }

  const recognition = new SpeechRecognition()
  recognition.lang = 'id-ID'
  recognition.continuous = false
  recognition.interimResults = true
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    if (onStart) onStart()
  }

  recognition.onresult = (event) => {
    let interimTranscript = ''
    let finalTranscript = ''

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const item = event.results[i]
      if (item.isFinal) {
        finalTranscript += item[0].transcript
      } else {
        interimTranscript += item[0].transcript
      }
    }

    const currentText = finalTranscript || interimTranscript
    if (onResult && currentText) {
      onResult(currentText.trim(), Boolean(finalTranscript))
    }
  }

  recognition.onerror = (event) => {
    let msg = 'Terjadi kesalahan pengenalan suara.'
    if (event.error === 'not-allowed') {
      msg = 'Izin akses mikrofon ditolak oleh browser.'
    } else if (event.error === 'no-speech') {
      msg = 'Tidak ada suara yang terdeteksi.'
    } else if (event.error === 'network') {
      msg = 'Koneksi jaringan pengenalan suara terganggu.'
    }
    if (onError) onError(msg)
  }

  recognition.onend = () => {
    if (onEnd) onEnd()
  }

  try {
    recognition.start()
  } catch (err) {
    if (onError) onError(err.message || 'Gagal memulai perekaman.')
  }

  return {
    stop: () => {
      try { recognition.stop() } catch {}
    },
    abort: () => {
      try { recognition.abort() } catch {}
    },
  }
}

/**
 * Strips markdown symbols, KaTeX math blocks, and expands technical power plant abbreviations.
 */
export function cleanTextForSpeech(text) {
  if (!text) return ''
  return text
    // Replace LaTeX math and special symbols
    .replace(/\\(?:Delta|delta)\s*T/g, 'Delta T')
    .replace(/\\pm/g, 'plus minus')
    .replace(/\\(?:times|cdot)/g, 'kali')
    .replace(/\\(?:le|leq)/g, 'kurang dari sama dengan')
    .replace(/\\(?:ge|geq)/g, 'lebih dari sama dengan')
    .replace(/\\(?:mu|micro)/g, 'mikro')
    .replace(/\\\s*%/g, 'persen')
    .replace(/\\[a-zA-Z]+/g, ' ')
    .replace(/[$()[\]]{1,2}(.*?)[$()[\]]{1,2}/g, '$1')
    .replace(/```[\s\S]*?```/g, '') // remove code blocks
    .replace(/`([^`]+)`/g, '$1') // inline code backticks
    .replace(/[*_#~]/g, '') // markdown symbols
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // link to text
    .replace(/\|[^|\r\n]+\|/g, ' ') // table row parts
    .replace(/^[•\-*]\s+/gm, '') // list bullets
    // Expand power plant engineering acronyms for natural Indonesian speech
    .replace(/\bmm\/s\b/gi, 'milimeter per detik')
    .replace(/\bdegC\b|°C/gi, 'derajat Celcius')
    .replace(/\bTDCG\b/gi, 'T D C G total gas terlarut')
    .replace(/\bTHD\b/gi, 'T H D distorsi harmonik')
    .replace(/\bkV\b/gi, 'kilo Volt')
    .replace(/\bMW\b/gi, 'Mega Watt')
    .replace(/\bkW\b/gi, 'kilo Watt')
    .replace(/\bpC\b/gi, 'piko Coulomb')
    .replace(/\bRUL\b/gi, 'sisa umur operasi')
    .replace(/\bDGA\b/gi, 'D G A')
    .replace(/\bMCSA\b/gi, 'M C S A')
    .replace(/\bBFP\b/gi, 'B F P Boiler Feed Pump')
    .replace(/\bCWP\b/gi, 'C W P Circulating Water Pump')
    .replace(/\bID Fan\b/gi, 'I D Fan')
    .replace(/\bFD Fan\b/gi, 'F D Fan')
    .replace(/\bPA Fan\b/gi, 'P A Fan')
    .replace(/\bPLTU\b/gi, 'P L T U')
    .replace(/\bWO\b/gi, 'Work Order')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Retrieves persisted voice settings from localStorage.
 */
export function getVoicePreferences() {
  if (typeof window === 'undefined') return { speakingRate: 0.98, pitch: 1.0, volume: 1.0, selectedVoice: '', autoTTS: false }
  try {
    const raw = localStorage.getItem('pple_voice_settings')
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        speakingRate: typeof parsed.speakingRate === 'number' ? parsed.speakingRate : 0.98,
        pitch: typeof parsed.pitch === 'number' ? parsed.pitch : 1.0,
        volume: typeof parsed.volume === 'number' ? parsed.volume : 1.0,
        selectedVoice: parsed.selectedVoice || '',
        autoTTS: Boolean(parsed.autoTTS),
        bargeIn: parsed.bargeIn !== false,
      }
    }
  } catch {}
  return { speakingRate: 0.98, pitch: 1.0, volume: 1.0, selectedVoice: '', autoTTS: false, bargeIn: true }
}

/**
 * Resolves the browser's voice list, waiting for the async 'voiceschanged'
 * event when the list isn't populated yet (common on first call in Chrome/Edge).
 * @returns {Promise<SpeechSynthesisVoice[]>}
 */
export function loadVoices() {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      resolve([])
      return
    }
    const existing = window.speechSynthesis.getVoices()
    if (existing && existing.length > 0) {
      resolve(existing)
      return
    }

    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      window.speechSynthesis.removeEventListener('voiceschanged', finish)
      resolve(window.speechSynthesis.getVoices())
    }

    window.speechSynthesis.addEventListener('voiceschanged', finish)
    setTimeout(finish, 500)
  })
}

/**
 * Scores an Indonesian voice by how natural it's likely to sound.
 */
function scoreVoice(voice) {
  const name = (voice.name || '').toLowerCase()
  let score = 0
  if (voice.lang === 'id-ID') score += 10
  if (/natural|neural|online|wavenet|google/.test(name)) score += 5
  if (/desktop|espeak|compact/.test(name)) score -= 5
  return score
}

/**
 * Picks the best-sounding available Indonesian voice, or null if none exist.
 */
export function pickBestVoice(voices, preferredName = '') {
  const idVoices = (voices || []).filter((v) => v.lang && v.lang.toLowerCase().startsWith('id'))
  if (idVoices.length === 0) return null

  if (preferredName) {
    const matched = idVoices.find((v) => v.name === preferredName)
    if (matched) return matched
  }
  return idVoices.sort((a, b) => scoreVoice(b) - scoreVoice(a))[0]
}

/**
 * Checks whether speech synthesis is currently active.
 */
export function isSpeaking() {
  return typeof window !== 'undefined' && Boolean(window.speechSynthesis && window.speechSynthesis.speaking)
}

/**
 * Reads aloud text using browser SpeechSynthesis.
 * @param {string} text
 * @param {Object} options
 * @param {function(): void} [options.onStart]
 * @param {function(): void} [options.onEnd]
 * @param {function(string): void} [options.onError]
 * @param {number} [options.rate]
 * @param {number} [options.pitch]
 * @param {number} [options.volume]
 * @param {string} [options.voice]
 * @returns {Promise<SpeechSynthesisUtterance | null>}
 */
export async function speakText(text, { onStart, onEnd, onError, rate, pitch, volume, voice } = {}) {
  if (!isSpeechSynthesisSupported()) {
    if (onError) onError('Browser tidak mendukung Speech Synthesis.')
    return null
  }

  // Cancel any ongoing utterance first
  window.speechSynthesis.cancel()

  const clean = cleanTextForSpeech(text)
  if (!clean) return null

  const prefs = getVoicePreferences()
  const utterance = new SpeechSynthesisUtterance(clean)
  utterance.lang = 'id-ID'
  utterance.rate = typeof rate === 'number' ? rate : prefs.speakingRate
  utterance.pitch = typeof pitch === 'number' ? pitch : prefs.pitch
  utterance.volume = typeof volume === 'number' ? volume : prefs.volume

  const voices = await loadVoices()
  const chosenVoice = pickBestVoice(voices, voice || prefs.selectedVoice)
  if (chosenVoice) {
    utterance.voice = chosenVoice
  }

  utterance.onstart = () => {
    if (onStart) onStart()
  }

  utterance.onend = () => {
    if (onEnd) onEnd()
  }

  utterance.onerror = (e) => {
    if (e.error !== 'canceled' && onError) {
      onError(e.error || 'Gagal menyuarakan teks.')
    }
  }

  window.speechSynthesis.speak(utterance)
  return utterance
}

export function stopSpeaking() {
  if (isSpeechSynthesisSupported()) {
    window.speechSynthesis.cancel()
  }
}

