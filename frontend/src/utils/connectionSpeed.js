/**
 * Estimasi kecepatan koneksi untuk mengatur laju animasi logo gear di chat.
 *
 * Dua sumber sinyal digabung, keduanya murni sisi frontend:
 *
 * 1. `navigator.connection.downlink` (Network Information API) - hanya tersedia
 *    di Chrome/Edge/Opera. Dipakai sebagai perkiraan awal supaya putaran sudah
 *    masuk akal sebelum ada satu pun request chat yang selesai.
 * 2. Latensi nyata request `/agent/chat` yang sudah selesai, dirata-rata secara
 *    eksponensial (EWMA). Ini sinyal yang sebenarnya dipercaya karena mengukur
 *    jalur ujung-ke-ujung (jaringan + waktu berpikir LLM), dan tersedia di semua
 *    browser termasuk Firefox/Safari yang tidak punya Network Information API.
 *
 * Hasilnya satu angka: durasi satu putaran penuh dalam detik. Makin kecil =
 * makin cepat berputar. Nilai ini dipasang sebagai custom property CSS
 * `--pg-dur`, jadi perubahan kecepatan tidak perlu render ulang SVG.
 */

import { useEffect, useState } from 'react'

/** Durasi satu putaran (detik) saat koneksi paling kencang. */
export const MIN_DURATION = 0.55
/** Durasi saat koneksi paling lambat atau offline. */
export const MAX_DURATION = 4.2
/** Dipakai sebelum ada sinyal apa pun. */
export const DEFAULT_DURATION = 1.8

// Batas pemetaan. Di luar rentang ini hasilnya dijepit ke MIN/MAX.
const DOWNLINK_FAST = 10 // Mbps
const DOWNLINK_SLOW = 0.4
const LATENCY_FAST = 700 // ms
const LATENCY_SLOW = 9000

// Bobot EWMA: sampel baru diberi porsi 0.4 sehingga perubahan kondisi jaringan
// terasa dalam 2-3 request, bukan seketika. Satu request yang sangat lama tetap
// bisa mendorong nilai ke MAX_DURATION - itu memang disengaja, request 30 detik
// adalah tanda koneksi lambat - dan butuh sekitar 4 sampel cepat untuk pulih.
const EWMA_ALPHA = 0.4

let latencyEwma = null
const listeners = new Set()

function notify() {
  listeners.forEach((fn) => {
    try {
      fn()
    } catch {
      // Satu listener yang gagal tidak boleh menghentikan listener lain.
    }
  })
}

/**
 * Catat durasi satu request chat yang sudah selesai (dalam milidetik).
 * Dipanggil baik saat request sukses maupun gagal - koneksi yang lambat sering
 * justru terlihat dari request yang gagal setelah lama menggantung.
 */
export function recordLatency(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return
  latencyEwma = latencyEwma === null ? ms : EWMA_ALPHA * ms + (1 - EWMA_ALPHA) * latencyEwma
  notify()
}

/** Buang sampel latensi yang terkumpul (dipakai di test). */
export function resetLatency() {
  latencyEwma = null
  notify()
}

export function getLatencyEwma() {
  return latencyEwma
}

/** Pemetaan logaritmik nilai `v` dari [fast, slow] ke [MIN_DURATION, MAX_DURATION]. */
function mapLog(v, fast, slow) {
  const lo = Math.log(Math.min(fast, slow))
  const hi = Math.log(Math.max(fast, slow))
  const t = (Math.log(v) - lo) / (hi - lo)
  const clamped = Math.min(1, Math.max(0, t))
  // `fast` bisa berada di ujung bawah (latensi) atau ujung atas (downlink),
  // jadi arah interpolasi ditentukan oleh posisi `fast` itu sendiri.
  const ratio = fast < slow ? clamped : 1 - clamped
  return MIN_DURATION + ratio * (MAX_DURATION - MIN_DURATION)
}

function connectionInfo() {
  if (typeof navigator === 'undefined') return null
  return navigator.connection || navigator.mozConnection || navigator.webkitConnection || null
}

/** Perkiraan durasi dari Network Information API, atau null bila tak tersedia. */
function durationFromDownlink() {
  const conn = connectionInfo()
  if (!conn) return null
  if (conn.saveData) return MAX_DURATION
  const downlink = Number(conn.downlink)
  if (Number.isFinite(downlink) && downlink > 0) {
    return mapLog(downlink, DOWNLINK_FAST, DOWNLINK_SLOW)
  }
  // Sebagian browser hanya mengisi effectiveType.
  switch (conn.effectiveType) {
    case '4g':
      return MIN_DURATION + 0.25 * (MAX_DURATION - MIN_DURATION)
    case '3g':
      return MIN_DURATION + 0.6 * (MAX_DURATION - MIN_DURATION)
    case '2g':
    case 'slow-2g':
      return MAX_DURATION
    default:
      return null
  }
}

/** Perkiraan durasi dari latensi request chat yang sudah terukur. */
function durationFromLatency() {
  if (latencyEwma === null) return null
  return mapLog(latencyEwma, LATENCY_FAST, LATENCY_SLOW)
}

/**
 * Durasi putaran saat ini (detik). Latensi terukur diberi bobot lebih besar
 * daripada downlink karena ia mengukur jalur yang benar-benar dipakai.
 */
export function currentGearDuration() {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return MAX_DURATION

  const fromLatency = durationFromLatency()
  const fromDownlink = durationFromDownlink()

  if (fromLatency !== null && fromDownlink !== null) return 0.7 * fromLatency + 0.3 * fromDownlink
  if (fromLatency !== null) return fromLatency
  if (fromDownlink !== null) return fromDownlink
  return DEFAULT_DURATION
}

/**
 * Durasi putaran yang ikut berubah saat jaringan berganti atau sampel latensi
 * baru masuk. Nilai dibulatkan ke 2 desimal supaya perubahan mikro tidak
 * memicu render ulang terus-menerus.
 */
export function useGearDuration() {
  const [duration, setDuration] = useState(() => Number(currentGearDuration().toFixed(2)))

  useEffect(() => {
    const sync = () => setDuration(Number(currentGearDuration().toFixed(2)))

    listeners.add(sync)
    const conn = connectionInfo()
    conn?.addEventListener?.('change', sync)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)

    sync()

    return () => {
      listeners.delete(sync)
      conn?.removeEventListener?.('change', sync)
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [])

  return duration
}
