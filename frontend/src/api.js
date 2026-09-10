const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '');

// Diisi hanya bila backend menyalakan PPLE_API_KEY. Kosong = server terbuka
// (mode lokal), jadi tidak ada header tambahan yang dikirim.
const API_KEY = (import.meta.env.VITE_API_KEY || '').trim();

export function apiUrl(path) {
  const cleanPath = String(path || '').startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

function targetsApiBackend(target) {
  const value = String(target || '');
  return value.startsWith('/') || value.startsWith(API_BASE_URL);
}

/**
 * fetch() untuk backend PPLE: menambahkan header X-API-Key bila
 * VITE_API_KEY diisi. Menerima path ('/api/health') maupun URL penuh hasil
 * apiUrl(), supaya pemanggil lama cukup berganti nama fungsi.
 */
export function apiFetch(target, options = {}) {
  if (!API_KEY || !targetsApiBackend(target)) {
    return fetch(target, options);
  }

  const headers = new Headers(options.headers || {});
  if (!headers.has('X-API-Key')) {
    headers.set('X-API-Key', API_KEY);
  }

  return fetch(target, { ...options, headers });
}
