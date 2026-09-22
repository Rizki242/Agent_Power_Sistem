import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, X } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Notifikasi non-blocking untuk menggantikan window.alert().
 *
 * alert() membekukan seluruh thread UI, tidak bisa ditata mengikuti tema, dan
 * tidak dapat memuat tautan tindak lanjut. Toast di sini memakai kosakata visual
 * `.notice--*` yang sudah dipakai di aplikasi agar tidak lahir bahasa kedua.
 */

const ToastContext = createContext(null)

const AUTO_DISMISS_MS = 6000
const MAX_VISIBLE = 3

const TONE_ICON = {
  success: CheckCircle2,
  error: CircleAlert,
  warning: AlertTriangle,
  info: Info,
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef(new Map())

  const dismiss = useCallback((id) => {
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback(({ tone = 'info', message, action = null }) => {
    if (!message) return null
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    setToasts((prev) => [...prev, { id, tone, message, action }].slice(-MAX_VISIBLE))

    // Kegagalan tidak ditutup otomatis: pesan error perlu sempat dibaca dan disalin.
    if (tone !== 'error') {
      timersRef.current.set(id, setTimeout(() => dismiss(id), AUTO_DISMISS_MS))
    }
    return id
  }, [dismiss])

  useEffect(() => {
    const timers = timersRef.current
    return () => {
      timers.forEach((timer) => clearTimeout(timer))
      timers.clear()
    }
  }, [])

  const value = useMemo(() => ({ notify, dismiss }), [notify, dismiss])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => {
          const Icon = TONE_ICON[toast.tone] || Info
          return (
            <div
              key={toast.id}
              className={`toast toast--${toast.tone}`}
              role={toast.tone === 'error' ? 'alert' : 'status'}
            >
              <Icon size={17} className="toast__icon" />
              <span className="toast__message">{toast.message}</span>
              {toast.action?.to ? (
                <Link to={toast.action.to} className="toast__action" onClick={() => dismiss(toast.id)}>
                  {toast.action.label}
                </Link>
              ) : null}
              <button
                type="button"
                className="toast__close"
                onClick={() => dismiss(toast.id)}
                aria-label="Tutup notifikasi"
              >
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

/**
 * Akses notifikasi dari komponen mana pun. Aman dipanggil di luar provider
 * (mis. pada pengujian komponen terisolasi): notifikasi menjadi no-op.
 */
export function useToast() {
  const context = useContext(ToastContext)
  return context || { notify: () => null, dismiss: () => {} }
}
