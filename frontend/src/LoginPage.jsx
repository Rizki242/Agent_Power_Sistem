import React, { useState } from 'react'
import {
  ShieldCheck,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  Zap,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from './context/AuthContext.jsx'

const PRESET_ACCOUNTS = [
  {
    roleName: 'Manager Keandalan (Admin)',
    username: 'admin',
    password: 'admin2026',
    roleTag: 'ADMIN',
    desc: 'Akses penuh ke seluruh modul, audit trail, dan konfigurasi AI/sistem.',
  },
  {
    roleName: 'Engineer CBM / Vibrasi',
    username: 'engineer',
    password: 'cbm2026',
    roleTag: 'ENGINEER',
    desc: 'Diagnosa multi-modal, analisis spektrum, persetujuan Work Order.',
  },
  {
    roleName: 'Operator Lapangan',
    username: 'operator',
    password: 'operator2026',
    roleTag: 'OPERATOR',
    desc: 'Pencatatan walkdown, monitoring real-time, dan status armada pembangkit.',
  },
]

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setErrorMsg('Silakan masukkan username dan kata sandi.')
      return
    }

    setErrorMsg('')
    setIsSubmitting(true)
    try {
      await login(username.trim(), password)
    } catch (err) {
      const msg = err?.message || ''
      if (!msg || msg === 'Failed to fetch' || msg.includes('fetch') || msg.includes('NetworkError')) {
        setErrorMsg('Tidak dapat terhubung ke server backend FastAPI (port 8000). Pastikan server backend sudah aktif (jalankan run_api.bat).')
      } else {
        setErrorMsg(msg)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSelectPreset = (preset) => {
    setUsername(preset.username)
    setPassword(preset.password)
    setErrorMsg('')
  }

  return (
    <div className="login-page">
      <div className="login-container">
        {/* Left / Branding Header */}
        <div className="login-header">
          <div className="login-badge">
            <ShieldCheck size={18} className="text-accent" />
            <span>Security Gateway • PLTU Jeranjang</span>
          </div>
          <h1 className="login-title">
            <Zap size={28} className="login-title-icon" />
            Agent Learning Sistem
          </h1>
          <p className="login-subtitle">
            Predictive Maintenance & Multi-Modal CBM Intelligence Platform (3 × 25 MW)
          </p>
        </div>

        {/* Form Card */}
        <div className="login-card">
          <div className="login-card-header">
            <h2>Masuk ke Sistem</h2>
            <p>Gunakan kredensial akun terdaftar untuk mengakses instrumen pemantauan.</p>
          </div>

          {errorMsg && (
            <div className="login-error-alert" role="alert">
              <AlertCircle size={18} className="login-error-icon" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="login-field">
              <label htmlFor="login-username">Username Personel</label>
              <div className="login-input-wrapper">
                <User size={18} className="login-field-icon" />
                <input
                  id="login-username"
                  type="text"
                  placeholder="Contoh: admin / engineer"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="username"
                  autoFocus
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Kata Sandi</label>
              <div className="login-input-wrapper">
                <Lock size={18} className="login-field-icon" />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Masukkan kata sandi"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="login-submit-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="login-spinner" />
                  <span>Memverifikasi Sesi...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={18} />
                  <span>Masuk ke Dashboard</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="login-presets-section">
            <div className="login-presets-divider">
              <span>Akun Demonstrasi CBM Lapangan</span>
            </div>
            <div className="login-presets-list">
              {PRESET_ACCOUNTS.map((preset) => (
                <button
                  key={preset.username}
                  type="button"
                  className={`login-preset-card ${username === preset.username ? 'login-preset-card--active' : ''}`}
                  onClick={() => handleSelectPreset(preset)}
                >
                  <div className="login-preset-header">
                    <strong>{preset.roleName}</strong>
                    <span className="login-preset-tag">{preset.roleTag}</span>
                  </div>
                  <div className="login-preset-desc">{preset.desc}</div>
                  <div className="login-preset-action">
                    {username === preset.username ? (
                      <span className="login-preset-selected">
                        <CheckCircle2 size={14} /> Terpilih
                      </span>
                    ) : (
                      <span>Klik untuk mengisi</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="login-footer">
          <p>
            Terenkripsi PBKDF2-HMAC-SHA256 • Sesi Terproteksi Sesuai Standar Operasi PLTU Jeranjang
          </p>
        </div>
      </div>
    </div>
  )
}

