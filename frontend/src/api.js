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
export async function apiFetch(target, options = {}) {
  let headers = new Headers(options.headers || {});
  if (API_KEY && targetsApiBackend(target) && !headers.has('X-API-Key')) {
    headers.set('X-API-Key', API_KEY);
  }

  return fetch(target, { ...options, headers });
}

/**
 * Extracts normalized error message and correlation ID from backend response envelopes.
 */
export async function parseApiError(response) {
  const correlationId = response.headers?.get('X-Correlation-ID') || response.headers?.get('X-Request-ID') || null;
  let message = `Request gagal dengan status ${response.status}`;
  try {
    const data = await response.json();
    if (data?.error?.message) {
      message = data.error.message;
    } else if (data?.detail) {
      message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
  } catch {
    // Non-JSON response
  }
  return { message, correlationId, status: response.status };
}
