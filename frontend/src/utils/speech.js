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
 * Strips markdown symbols, code fences, and bullet hashes for natural speech reading.
 */
function cleanTextForSpeech(text) {
  if (!text) return ''
  return text
    .replace(/```[\s\S]*?```/g, 'blok kode teknis') // replace code blocks
    .replace(/`([^`]+)`/g, '$1') // remove inline code backticks
    .replace(/[*_#~]/g, '') // remove markdown symbols
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // link to text
    .replace(/\|[^|\r\n]+\|/g, ' ') // table row parts
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Reads aloud text using browser SpeechSynthesis.
 * @param {string} text
 * @param {Object} options
 * @param {function(): void} [options.onStart]
 * @param {function(): void} [options.onEnd]
 * @param {function(string): void} [options.onError]
 * @returns {SpeechSynthesisUtterance | null}
 */
export function speakText(text, { onStart, onEnd, onError } = {}) {
  if (!isSpeechSynthesisSupported()) {
    if (onError) onError('Browser tidak mendukung Speech Synthesis.')
    return null
  }

  // Cancel any ongoing utterance first
  window.speechSynthesis.cancel()

  const clean = cleanTextForSpeech(text)
  if (!clean) return null

  const utterance = new SpeechSynthesisUtterance(clean)
  utterance.lang = 'id-ID'
  utterance.rate = 1.05
  utterance.pitch = 1.0

  // Attempt to select an Indonesian voice if available
  const voices = window.speechSynthesis.getVoices()
  const idVoice = voices.find((v) => v.lang && (v.lang.startsWith('id') || v.lang.includes('ID')))
  if (idVoice) {
    utterance.voice = idVoice
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
