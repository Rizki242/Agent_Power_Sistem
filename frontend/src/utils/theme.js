/**
 * Pengendali tema tampilan (Terang / Gelap "Control Room" / Ikut Sistem).
 *
 * Preferensi disimpan pada kunci localStorage yang sama dengan halaman Pengaturan
 * (`pple_user_prefs.theme`), lalu diterapkan sebagai atribut `data-theme` pada
 * elemen <html>. Seluruh warna komponen dibaca dari token CSS di styles.css,
 * sehingga pergantian tema tidak memerlukan render ulang React.
 */

const PREFS_KEY = 'pple_user_prefs'
export const THEME_VALUES = ['light', 'dark', 'system']
const DEFAULT_THEME = 'system'

function darkMediaQuery() {
  if (typeof window === 'undefined' || !window.matchMedia) return null
  return window.matchMedia('(prefers-color-scheme: dark)')
}

/** Baca preferensi tema tersimpan; 'system' bila belum diatur atau tidak terbaca. */
export function readThemePreference() {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (THEME_VALUES.includes(parsed?.theme)) return parsed.theme
    }
  } catch {
    // localStorage bisa diblokir (mode privat) - jatuh ke default.
  }
  return DEFAULT_THEME
}

/** Terjemahkan preferensi menjadi tema efektif yang benar-benar dipakai. */
export function resolveTheme(preference) {
  if (preference === 'light' || preference === 'dark') return preference
  const query = darkMediaQuery()
  return query && query.matches ? 'dark' : 'light'
}

/** Terapkan preferensi ke DOM. Mengembalikan tema efektif yang dipasang. */
export function applyTheme(preference) {
  const effective = resolveTheme(preference)
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = effective
  }
  return effective
}

/**
 * Pasang tema saat aplikasi dimuat dan ikuti perubahan tema OS selama
 * preferensi masih 'system'. Mengembalikan fungsi pembersih.
 */
export function initTheme() {
  applyTheme(readThemePreference())

  const query = darkMediaQuery()
  if (!query) return () => {}

  const onSystemChange = () => {
    if (readThemePreference() === 'system') applyTheme('system')
  }

  // Safari lama hanya mendukung addListener/removeListener.
  if (query.addEventListener) {
    query.addEventListener('change', onSystemChange)
    return () => query.removeEventListener('change', onSystemChange)
  }
  query.addListener(onSystemChange)
  return () => query.removeListener(onSystemChange)
}

/** Simpan preferensi tema ke prefs pengguna sekaligus menerapkannya. */
export function saveThemePreference(preference) {
  const value = THEME_VALUES.includes(preference) ? preference : DEFAULT_THEME
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    const prefs = raw ? JSON.parse(raw) : {}
    localStorage.setItem(PREFS_KEY, JSON.stringify({ ...prefs, theme: value }))
  } catch {
    // Penyimpanan gagal bukan alasan untuk tidak mengganti tampilan sesi ini.
  }
  return applyTheme(value)
}
