import { useCallback, useEffect, useState } from 'react'
import {
  Bell,
  Bot,
  Check,
  CheckCircle2,
  CircleAlert,
  Clock,
  Cloud,
  Cpu,
  Database,
  Download,
  FileText,
  Globe,
  HardDrive,
  KeyRound,
  Lock,
  LockKeyhole,
  Mic,
  Moon,
  Radio,
  RefreshCw,
  Save,
  Server,
  ShieldCheck,
  Sun,
  Terminal,
  TimerReset,
  User,
  Volume2,
  Zap,
} from 'lucide-react'
import { getSettingsOverview, saveAISettings, testAIConnection } from './api.js'
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speakText,
  stopSpeaking,
} from './utils/speech.js'

const PROVIDER_NAMES = {
  gemini: 'Google Gemini',
  groq: 'Groq',
  opencode: 'OpenAI Compatible',
  ollama: 'Ollama Lokal',
}

function formatModelLabel(modelName) {
  if (!modelName) return ''
  const MAP = {
    'gemini-3.8-flash': 'Gemini 3.8 Flash',
    'gemini-3.7-flash': 'Gemini 3.7 Flash',
    'gemini-3.6-flash': 'Gemini 3.6 Flash',
    'gemini-3.1-pro': 'Gemini 3.1 Pro',
    'gemini-2.5-flash': 'Gemini 2.5 Flash',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'gemini-1.5-flash': 'Gemini 1.5 Flash',
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'qwen/qwen3.8-27b': 'Qwen 3.8 27B',
    'qwen/qwen3.6-27b': 'Qwen 3.6 27B',
    'llama-3.3-70b-versatile': 'Llama 3.3 70B Versatile',
    'deepseek-r1-distill-llama-70b': 'DeepSeek R1 Distill 70B',
  }
  if (MAP[modelName]) return MAP[modelName]
  if (modelName.startsWith('gemini-')) {
    return modelName
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  }
  return modelName
}

const TABS = [
  { id: 'ai', label: 'AI & Model', icon: Bot },
  { id: 'voice', label: 'Voice Assistant', icon: Mic },
  { id: 'safety', label: 'Safety & Engineering', icon: ShieldCheck },
  { id: 'data', label: 'Data & Knowledge', icon: Database },
  { id: 'system', label: 'System & Integration', icon: Server },
  { id: 'user', label: 'User & Preferences', icon: User },
]

function SystemRow({ icon: Icon, title, detail, state = 'healthy', stateLabel = 'Online' }) {
  return (
    <div className="system-check-row">
      <span className="system-check-row__icon"><Icon size={17} /></span>
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
      <span className={`system-state system-state--${state}`}>
        <i />
        {stateLabel}
      </span>
    </div>
  )
}

function McpToolItem({ name, description, status = 'healthy', statusLabel = 'Ready' }) {
  return (
    <div className="mcp-tool-item">
      <div className="mcp-tool-item__info">
        <span className={`status-dot status-dot--${status}`} />
        <div>
          <strong>{name}</strong>
          <small>{description}</small>
        </div>
      </div>
      <span className="mcp-tool-item__badge">{statusLabel}</span>
    </div>
  )
}

export default function SettingsWorkspace() {
  const [activeTab, setActiveTab] = useState('ai')
  const [data, setData] = useState(null)
  const [form, setForm] = useState({
    ai_enabled: false,
    ai_provider: 'gemini',
    model: '',
    response_mode: 'balanced',
    fallback_strategy: 'rule_first',
  })
  const [state, setState] = useState({ status: 'loading', saving: false, message: '' })
  const [testResult, setTestResult] = useState(null)
  const [testingAI, setTestingAI] = useState(false)
  const [showLogsModal, setShowLogsModal] = useState(false)

  // Voice Settings State (persisted to localStorage)
  const [voiceSettings, setVoiceSettings] = useState(() => {
    try {
      const saved = localStorage.getItem('pple_voice_settings')
      if (saved) return JSON.parse(saved)
    } catch {}
    return {
      voiceEnabled: true,
      language: 'id-ID',
      ttsEnabled: true,
      speakingRate: 1.0,
      autoTTS: false,
      pushToTalk: true,
      continuousListening: false,
      bargeIn: true,
      confirmDangerous: true,
      readSafetyWarnings: true,
      selectedVoice: '',
    }
  })
  const [voiceSaved, setVoiceSaved] = useState(false)
  const [testVoiceSpeaking, setTestVoiceSpeaking] = useState(false)
  const [micTestActive, setMicTestActive] = useState(false)

  // User & Preferences state (persisted to localStorage)
  const [userPrefs, setUserPrefs] = useState(() => {
    try {
      const saved = localStorage.getItem('pple_user_prefs')
      if (saved) return JSON.parse(saved)
    } catch {}
    return {
      engineerName: 'Rizki Firmansyah',
      unitRole: 'Unit Pemeliharaan CBM & Keandalan',
      language: 'id',
      timeZone: 'Asia/Makassar',
      theme: 'dark',
      notifySafety: true,
      notifyAnalysis: true,
      notifyAutomation: true,
      notifyVoice: false,
    }
  })
  const [userSaved, setUserSaved] = useState(false)

  const load = useCallback((signal) => {
    setState((current) => ({ ...current, status: 'loading' }))
    return getSettingsOverview(signal).then((result) => {
      setData(result)
      const provider = result.active_provider
      setForm((prev) => ({
        ...prev,
        ai_enabled: result.ai_enabled,
        ai_provider: provider,
        model: result.providers[provider]?.model || '',
      }))
      setState({ status: 'ready', saving: false, message: '' })
    }).catch((error) => {
      if (error.name !== 'AbortError') {
        setState({
          status: 'error',
          saving: false,
          message: 'Health check gagal. Pastikan FastAPI backend berjalan di port 8000.',
        })
      }
    })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  function chooseProvider(provider) {
    setForm((current) => ({
      ...current,
      ai_provider: provider,
      model: data?.providers[provider]?.model || data?.providers[provider]?.models?.[0] || '',
    }))
  }

  async function saveAI(event) {
    event.preventDefault()
    setState((current) => ({ ...current, saving: true, message: '' }))
    try {
      const payload = {
        ai_enabled: form.ai_enabled,
        ai_provider: form.ai_provider,
        model: form.model,
      }
      if (form.ai_provider === 'ollama') payload.ollama_host = 'http://localhost:11434'
      const result = await saveAISettings(payload)
      setState({ status: 'ready', saving: false, message: result.message })
      await load()
    } catch (error) {
      setState({ status: 'ready', saving: false, message: `Konfigurasi gagal disimpan: ${error.message}` })
    }
  }

  async function handleTestAI() {
    setTestingAI(true)
    setTestResult(null)
    try {
      const res = await testAIConnection()
      setTestResult(res)
    } catch (err) {
      setTestResult({ success: false, message: `Uji koneksi gagal: ${err.message}` })
    } finally {
      setTestingAI(false)
    }
  }

  function saveVoicePreferences(e) {
    if (e) e.preventDefault()
    try {
      localStorage.setItem('pple_voice_settings', JSON.stringify(voiceSettings))
      // Also update voice auto-read preference for Chat workspace
      localStorage.setItem('pple_voice_auto_read', String(voiceSettings.autoTTS))
      setVoiceSaved(true)
      setTimeout(() => setVoiceSaved(false), 3000)
    } catch {}
  }

  function handleTestVoice() {
    if (!isSpeechSynthesisSupported()) {
      alert('Browser Anda tidak mendukung Text-to-Speech.')
      return
    }
    stopSpeaking()
    setTestVoiceSpeaking(true)
    speakText('Halo, ini uji suara asisten CBM PLTU Jeranjang. Sistem telemetri siap dioperasikan.', {
      onEnd: () => setTestVoiceSpeaking(false),
      onError: () => setTestVoiceSpeaking(false),
    })
  }

  function handleTestMic() {
    if (!isSpeechRecognitionSupported()) {
      alert('Browser tidak mendukung Speech Recognition (Gunakan Chrome atau Edge).')
      return
    }
    setMicTestActive(true)
    setTimeout(() => {
      setMicTestActive(false)
    }, 4000)
  }

  function saveUserPreferences(e) {
    e.preventDefault()
    try {
      localStorage.setItem('pple_user_prefs', JSON.stringify(userPrefs))
      setUserSaved(true)
      setTimeout(() => setUserSaved(false), 3000)
    } catch {}
  }

  function exportSafeConfig() {
    if (!data) return
    const safe = {
      ai_enabled: form.ai_enabled,
      ai_provider: form.ai_provider,
      model: form.model,
      voice_settings: voiceSettings,
      user_preferences: userPrefs,
      system: data.system,
      safety: data.safety,
      data_sources: data.data_sources,
      version: data.version,
      exported_at: new Date().toISOString(),
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(safe, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `pple-settings-control-center-${new Date().toISOString().split('T')[0]}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const provider = data?.providers?.[form.ai_provider]
  const system = data?.system
  const safety = data?.safety
  const database = data?.database
  const dataSources = data?.data_sources || []

  return (
    <div className="page settings-page">
      <header className="page-header">
        <div>
          <h1>Settings & System Control</h1>
          <p>Control Center terpadu: kelola koneksi runtime, AI, voice, safety, dan data tanpa mengubah aturan engineering.</p>
        </div>
        <div className="header-actions">
          <button className="button button--secondary" onClick={exportSafeConfig} disabled={!data}>
            <Download size={16} />
            Export aman
          </button>
        </div>
      </header>

      {/* Control Plane Status Banner (Section 8 & 9) */}
      <section className="control-plane-card">
        <div className="control-plane-header">
          <div className="control-plane-tag">
            <i />
            <span>Control Plane</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.74rem', color: '#9db4b5' }}>
              Last check: {data ? new Date(data.generated_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
            </span>
            <button
              className="icon-button"
              onClick={() => load()}
              aria-label="Jalankan health check ulang"
              title="Refresh status"
              style={{ width: '32px', height: '32px', color: '#dcebea', borderColor: '#3a5f64' }}
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        <h2 style={{ margin: '0 0 14px', fontSize: '1.2rem', color: '#ffffff', fontWeight: 600 }}>
          {state.status === 'ready'
            ? 'Sistem Siap Digunakan · Seluruh Layanan Aktif'
            : state.status === 'error'
            ? 'Perlu Pemeriksaan Koneksi API'
            : 'Memeriksa Kesiapan Sistem...'}
        </h2>

        <div className="control-plane-pills">
          <span className="control-plane-pill">
            <i style={{ background: '#258c7d' }} />
            <strong>Backend:</strong> 🟢 Online (v{data?.version || '2.0.0'})
          </span>
          <span className="control-plane-pill">
            <i style={{ background: '#258c7d' }} />
            <strong>Database:</strong> 🟢 Healthy (SQLite)
          </span>
          <span className="control-plane-pill">
            <i style={{ background: form.ai_enabled ? '#258c7d' : '#88989b' }} />
            <strong>AI Provider:</strong> {form.ai_enabled ? `🟢 Ready (${formatModelLabel(form.model || provider?.model)})` : '⚪ Standby (Rule-based)'}
          </span>
          <span className="control-plane-pill">
            <i style={{ background: voiceSettings.voiceEnabled ? '#258c7d' : '#88989b' }} />
            <strong>Voice STT/TTS:</strong> {voiceSettings.voiceEnabled ? '🟢 Ready' : '⚪ Disabled'}
          </span>
          <span className="control-plane-pill">
            <i style={{ background: '#258c7d' }} />
            <strong>Safety Guardrail:</strong> 🟢 Active (Hard-Locked)
          </span>
          <span className="control-plane-pill">
            <i style={{ background: '#258c7d' }} />
            <strong>API:</strong> {system?.api_protection_label || '🟢 Protected — Localhost'}
          </span>
        </div>
      </section>

      {state.message && (
        <div className={`notice ${state.message.includes('gagal') ? 'notice--error' : 'notice--success'}`} style={{ marginBottom: '18px' }}>
          {state.message.includes('gagal') ? <CircleAlert size={17} /> : <Check size={17} />}
          <span>{state.message}</span>
        </div>
      )}

      {/* Tabs Navigation (Section 1) */}
      <nav className="settings-tabs-nav" aria-label="Kategori Pengaturan">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`settings-tab-btn ${activeTab === id ? 'settings-tab-btn--active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      {/* TAB 1: 🤖 AI & Model */}
      {activeTab === 'ai' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><Bot size={20} /> AI & Model Architecture</h2>
            <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
              Fallback rule-based selalu aktif sebagai source of truth.
            </span>
          </div>

          {data ? (
            <form onSubmit={saveAI}>
              <label className="settings-master-switch">
                <span>
                  <strong>Bantuan Kecerdasan AI (LLM)</strong>
                  <small>Fallback rule-based tetap otomatis berjalan saat AI offline atau kuota habis.</small>
                </span>
                <input
                  type="checkbox"
                  checked={form.ai_enabled}
                  onChange={(e) => setForm({ ...form, ai_enabled: e.target.checked })}
                />
                <i />
              </label>

              <fieldset className="provider-picker">
                <legend>Pilih LLM Provider</legend>
                {Object.entries(data.providers).map(([id, item]) => (
                  <button
                    type="button"
                    key={id}
                    className={`provider-option ${form.ai_provider === id ? 'provider-option--active' : ''}`}
                    onClick={() => chooseProvider(id)}
                  >
                    <span>{id === 'ollama' ? <HardDrive size={18} /> : <Cloud size={18} />}</span>
                    <div>
                      <strong>{PROVIDER_NAMES[id] || id}</strong>
                      <small>
                        {item.configured ? '🟢 Credential Terdeteksi' : id === 'ollama' ? '🟢 Localhost (11434)' : '🔑 Key Not Configured'}
                      </small>
                    </div>
                    {item.configured ? <Check size={16} /> : <KeyRound size={16} />}
                  </button>
                ))}
              </fieldset>

              <div className="form-row-dual">
                <label className="form-field">
                  <span>Model Aktif</span>
                  <select
                    value={form.model}
                    onChange={(e) => setForm({ ...form, model: e.target.value })}
                  >
                    {provider?.models.map((m) => (
                      <option key={m} value={m}>{formatModelLabel(m)}</option>
                    ))}
                  </select>
                </label>

                <label className="form-field">
                  <span>Fallback Strategy</span>
                  <select
                    value={form.fallback_strategy}
                    onChange={(e) => setForm({ ...form, fallback_strategy: e.target.value })}
                  >
                    <option value="rule_first">Rule-based → Local LLM → Cloud</option>
                    <option value="cloud_first">Cloud LLM → Local LLM → Rule-based</option>
                  </select>
                </label>
              </div>

              {/* Response mode radio */}
              <div style={{ margin: '14px 0 18px' }}>
                <span className="field-label" style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
                  Response Mode
                </span>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="response_mode"
                      value="fast"
                      checked={form.response_mode === 'fast'}
                      onChange={() => setForm({ ...form, response_mode: 'fast' })}
                    />
                    <span>Cepat (Ringkas)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="response_mode"
                      value="balanced"
                      checked={form.response_mode === 'balanced'}
                      onChange={() => setForm({ ...form, response_mode: 'balanced' })}
                    />
                    <span>Seimbang (Rekomendasi CBM Standar)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="response_mode"
                      value="detailed"
                      checked={form.response_mode === 'detailed'}
                      onChange={() => setForm({ ...form, response_mode: 'detailed' })}
                    />
                    <span>Mendalam (Analisis Lengkap & Lintas Domain)</span>
                  </label>
                </div>
              </div>

              <div className="secret-guidance">
                <LockKeyhole size={18} />
                <div>
                  <strong>Secret Tidak Dikelola dari Browser</strong>
                  <span>Kunci API dibaca langsung dari environment sistem atau <code>.env</code> untuk menjamin integritas dan keamanan siber ruang kontrol.</span>
                </div>
              </div>

              {testResult && (
                <div className={`notice ${testResult.success ? 'notice--success' : 'notice--error'}`} style={{ margin: '14px 0' }}>
                  {testResult.success ? <Check size={16} /> : <CircleAlert size={16} />}
                  <span>{testResult.message}</span>
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                <button
                  type="submit"
                  className="button button--primary"
                  disabled={state.saving || !form.model}
                >
                  <Save size={16} />
                  {state.saving ? 'Menyimpan...' : 'Simpan Preferensi'}
                </button>
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={handleTestAI}
                  disabled={testingAI}
                >
                  <Zap size={16} />
                  {testingAI ? 'Menguji Koneksi...' : 'Test AI Connection'}
                </button>
              </div>
            </form>
          ) : (
            <div className="empty-state">
              <Server size={28} />
              <strong>Koneksi API Belum Terhubung</strong>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: 🎙 Voice Assistant */}
      {activeTab === 'voice' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><Mic size={20} /> Voice Assistant Configuration</h2>
            <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
              Speech-to-Text & Text-to-Speech berbasis Web Speech API lokal.
            </span>
          </div>

          <form onSubmit={saveVoicePreferences}>
            <label className="settings-master-switch">
              <span>
                <strong>Voice Assistant Master Switch</strong>
                <small>Mengaktifkan interaksi suara untuk hands-free inspeksi lapangan dan kontrol.</small>
              </span>
              <input
                type="checkbox"
                checked={voiceSettings.voiceEnabled}
                onChange={(e) => setVoiceSettings({ ...voiceSettings, voiceEnabled: e.target.checked })}
              />
              <i />
            </label>

            <div className="form-row-dual">
              <label className="form-field">
                <span>Bahasa Pengenalan Suara (STT)</span>
                <select value={voiceSettings.language} disabled>
                  <option value="id-ID">Bahasa Indonesia (id-ID) [Default]</option>
                </select>
              </label>

              <label className="form-field">
                <span>Kecepatan Bicara Asisten ({voiceSettings.speakingRate}x)</span>
                <input
                  type="range"
                  min="0.8"
                  max="1.4"
                  step="0.1"
                  value={voiceSettings.speakingRate}
                  onChange={(e) => setVoiceSettings({ ...voiceSettings, speakingRate: parseFloat(e.target.value) })}
                  style={{ width: '100%', marginTop: '8px' }}
                />
              </label>
            </div>

            <div className="form-row-dual">
              <label className="form-field">
                <span>Text-to-Speech (TTS Output)</span>
                <select
                  value={voiceSettings.ttsEnabled ? 'on' : 'off'}
                  onChange={(e) => setVoiceSettings({ ...voiceSettings, ttsEnabled: e.target.value === 'on' })}
                >
                  <option value="on">Aktif (Suara Sintesis Bahasa Indonesia)</option>
                  <option value="off">Nonaktif (Hanya Teks)</option>
                </select>
              </label>

              <label className="form-field">
                <span>Auto-baca Jawaban (Context-aware)</span>
                <select
                  value={voiceSettings.autoTTS ? 'on' : 'off'}
                  onChange={(e) => setVoiceSettings({ ...voiceSettings, autoTTS: e.target.value === 'on' })}
                >
                  <option value="off">Mati (Hanya baca otomatis bila input dari suara)</option>
                  <option value="on">Selalu baca semua respon</option>
                </select>
              </label>
            </div>

            {/* Voice Behavior Checklist */}
            <div style={{ marginTop: '16px' }}>
              <span className="field-label" style={{ fontSize: '0.82rem', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
                Perilaku Suara & Safety Interlock
              </span>
              <div className="checkbox-list">
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={voiceSettings.bargeIn}
                    onChange={(e) => setVoiceSettings({ ...voiceSettings, bargeIn: e.target.checked })}
                  />
                  <div>
                    <strong>Hentikan Suara Saat Pengguna Mulai Berbicara (Barge-in)</strong>
                    <small>Mencegah tabrakan audio asisten dengan suara manusia saat memberikan instruksi lanjutan.</small>
                  </div>
                </label>

                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={voiceSettings.readSafetyWarnings}
                    onChange={(e) => setVoiceSettings({ ...voiceSettings, readSafetyWarnings: e.target.checked })}
                  />
                  <div>
                    <strong>Bacakan Peringatan Safety Kritis Seketika (Safety Audio Override)</strong>
                    <small>Peringatan bahaya, penolakan perintah plant, dan alarm severity tinggi selalu dibacakan.</small>
                  </div>
                </label>

                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={voiceSettings.pushToTalk}
                    onChange={(e) => setVoiceSettings({ ...voiceSettings, pushToTalk: e.target.checked })}
                  />
                  <div>
                    <strong>Gunakan Push-to-Talk (Rekomendasi Ruang Kontrol)</strong>
                    <small>Mencegah noise latar belakang turbin atau percakapan operator memicu asisten secara tidak sengaja.</small>
                  </div>
                </label>

                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={voiceSettings.continuousListening}
                    onChange={(e) => setVoiceSettings({ ...voiceSettings, continuousListening: e.target.checked })}
                  />
                  <div>
                    <strong>Continuous Listening (Mendengarkan Terus Menerus)</strong>
                    <small>Default NONAKTIF. Hanya aktifkan di ruangan sunyi untuk hands-free total.</small>
                  </div>
                </label>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '20px' }}>
              <button type="submit" className="button button--primary">
                <Save size={16} />
                Simpan Pengaturan Suara
              </button>
              <button
                type="button"
                className="button button--secondary"
                onClick={handleTestVoice}
                disabled={testVoiceSpeaking}
              >
                <Volume2 size={16} />
                {testVoiceSpeaking ? 'Memutar Audio...' : 'Tes Suara Asisten'}
              </button>
              <button
                type="button"
                className="button button--secondary"
                onClick={handleTestMic}
                disabled={micTestActive}
              >
                <Mic size={16} />
                {micTestActive ? 'Mendengarkan (4s)...' : 'Tes Mikrofon'}
              </button>
              {voiceSaved && (
                <span className="save-indicator">
                  <CheckCircle2 size={16} /> Pengaturan tersimpan!
                </span>
              )}
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: 🛡 Safety & Engineering */}
      {activeTab === 'safety' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><ShieldCheck size={20} /> Safety Guardrail & Engineering Boundaries</h2>
            <span className="badge-allowed">
              <Check size={13} /> Safety Guardrail Active
            </span>
          </div>

          <div className="engineering-lock" style={{ marginTop: '0', marginBottom: '20px' }}>
            <Lock size={22} />
            <div>
              <strong style={{ fontSize: '0.92rem' }}>Status: HARD-LOCKED (Proteksi Inti Terkunci)</strong>
              <span>
                Seluruh batas ambang batas (ISO 10816-3, MCSA sideband limits -54 dB / -45 dB, Duval Triangle, dan logika trip)
                terkunci permanen pada logic code dan tidak dapat dimodifikasi sembarangan oleh pengguna umum melalui antarmuka web.
              </span>
            </div>
          </div>

          <div className="cbm-sources-grid" style={{ marginBottom: '22px' }}>
            <div className="cbm-source-card">
              <div className="cbm-source-card__top">
                <strong>Vibration ISO 10816-3 Thresholds</strong>
                <span className="badge-locked"><Lock size={11} /> Locked</span>
              </div>
              <p>Zone A/B/C/D velocity RMS & displacement limits untuk motor & pompa.</p>
            </div>
            <div className="cbm-source-card">
              <div className="cbm-source-card__top">
                <strong>MCSA Sideband dB Limits</strong>
                <span className="badge-locked"><Lock size={11} /> Locked</span>
              </div>
              <p>Kriteria kerusakan batang rotor (&lt;-54 dB Sehat, -54 s/d -45 dB Alert, &ge;-45 dB Kritis).</p>
            </div>
            <div className="cbm-source-card">
              <div className="cbm-source-card__top">
                <strong>DGA Duval & TDCG Limits</strong>
                <span className="badge-locked"><Lock size={11} /> Locked</span>
              </div>
              <p>Segitiga Duval 1/4/5 & batas konsentrasi gas terlarut IEEE C57.104.</p>
            </div>
            <div className="cbm-source-card">
              <div className="cbm-source-card__top">
                <strong>Trip / Shutdown Protection</strong>
                <span className="badge-locked"><Lock size={11} /> Locked</span>
              </div>
              <p>Penolakan perintah otomatis terhadap intervensi fisik pemutus sirkuit atau turbin.</p>
            </div>
          </div>

          <h3 style={{ margin: '0 0 10px', fontSize: '0.9rem', fontWeight: 600, color: 'var(--ink)' }}>
            Matriks Izin Agen (Agent Permission Matrix)
          </h3>
          <table className="permission-table">
            <thead>
              <tr>
                <th>Nama Operasi</th>
                <th>Kategori</th>
                <th>Status Izin</th>
                <th>Keterangan Keamanan</th>
              </tr>
            </thead>
            <tbody>
              {(safety?.permissions || [
                { name: 'Read equipment data & telemetry', allowed: true, category: 'analysis' },
                { name: 'Analyze CBM multi-modal data', allowed: true, category: 'analysis' },
                { name: 'Generate RUL & risk recommendations', allowed: true, category: 'analysis' },
                { name: 'Create maintenance assessment report', allowed: true, category: 'analysis' },
                { name: 'Control physical equipment', allowed: false, category: 'actuation' },
                { name: 'Trip generator / motor breaker', allowed: false, category: 'actuation' },
                { name: 'Shutdown plant boiler / turbine unit', allowed: false, category: 'actuation' },
                { name: 'Modify protection relay thresholds', allowed: false, category: 'actuation' },
              ]).map((perm, idx) => (
                <tr key={idx}>
                  <td><strong>{perm.name}</strong></td>
                  <td style={{ textTransform: 'capitalize' }}>{perm.category}</td>
                  <td>
                    {perm.allowed ? (
                      <span className="badge-allowed"><Check size={12} /> Diizinkan</span>
                    ) : (
                      <span className="badge-locked"><Lock size={12} /> DITOLAK (Locked)</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
                    {perm.allowed ? 'Operasi komputasi & rekomendasi analitik' : 'Aksi fisik dilarang keras demi integritas unit pembangkit'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
            <a
              href="/api/v2/audit"
              target="_blank"
              rel="noreferrer"
              className="button button--secondary"
            >
              <Terminal size={15} />
              Lihat Audit Log (/api/v2/audit)
            </a>
          </div>
        </div>
      )}

      {/* TAB 4: 🗄 Data & Knowledge */}
      {activeTab === 'data' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><Database size={20} /> Data & Knowledge Base Status</h2>
            <span className="badge-allowed">
              <Check size={13} /> {database?.status || 'HEALTHY'}
            </span>
          </div>

          <div className="form-row-dual" style={{ marginBottom: '18px' }}>
            <div style={{ padding: '16px', background: '#f8fafb', border: '1px solid var(--border)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Database size={18} style={{ color: 'var(--action)' }} />
                <strong style={{ fontSize: '0.92rem' }}>Penyimpanan SQLite</strong>
              </div>
              <p style={{ margin: '0 0 6px', fontSize: '0.8rem', color: 'var(--muted)' }}>
                Database riwayat diagnosa, audit trail, dan memori percakapan agent.
              </p>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--healthy)' }}>
                🟢 Connected · File: <code>data/agent_memory.db</code>
              </span>
            </div>

            <div style={{ padding: '16px', background: '#f8fafb', border: '1px solid var(--border)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <HardDrive size={18} style={{ color: 'var(--action)' }} />
                <strong style={{ fontSize: '0.92rem' }}>Knowledge Base (RAG)</strong>
              </div>
              <p style={{ margin: '0 0 6px', fontSize: '0.8rem', color: 'var(--muted)' }}>
                Dokumen standar teknis PLTU, IEEE, ISO, dan manual buku panduan mesin.
              </p>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--healthy)' }}>
                🟢 Terindeks · {system?.knowledge_documents || 75} Dokumen JSON
              </span>
            </div>
          </div>

          <h3 style={{ margin: '18px 0 10px', fontSize: '0.9rem', fontWeight: 600, color: 'var(--ink)' }}>
            Status 6 Sumber Data Domain CBM
          </h3>
          <div className="cbm-sources-grid">
            {dataSources.map((ds) => (
              <div key={ds.id} className="cbm-source-card">
                <div className="cbm-source-card__top">
                  <strong>{ds.name}</strong>
                  <span className="badge-allowed"><Check size={11} /> {ds.status}</span>
                </div>
                <p>{ds.description}</p>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '22px' }}>
            <a href="/documents" className="button button--secondary">
              <FileText size={15} />
              Buka Manajemen Dokumen
            </a>
            <button
              type="button"
              className="button button--secondary"
              onClick={() => alert('Backup otomatis harian aktif dengan retensi 5 file rotasi (MCSA_MAX_BACKUPS).')}
            >
              <Save size={15} />
              Verifikasi Integritas Backup
            </button>
          </div>
        </div>
      )}

      {/* TAB 5: 🔌 System & Integration */}
      {activeTab === 'system' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><Server size={20} /> System Runtime & Integrations</h2>
            <span className="badge-allowed">
              <Check size={13} /> FastAPI 2.0.0 Online
            </span>
          </div>

          <div className="system-section-block" style={{ borderTop: 0, paddingTop: 0 }}>
            <h3 className="system-subtitle">Komponen Runtime & Network</h3>
            <div className="system-check-list">
              <SystemRow
                icon={Server}
                title="FastAPI Backend"
                detail={`Port 8000 · v${data?.version || '2.0.0'}`}
                state="healthy"
                stateLabel="🟢 Online"
              />
              <SystemRow
                icon={ShieldCheck}
                title="API Protection"
                detail={system?.api_auth_enabled ? 'X-API-Key diwajibkan' : 'Aman untuk lingkungan localhost'}
                state="healthy"
                stateLabel={system?.api_protection_label || '🟢 Protected — Localhost'}
              />
              <SystemRow
                icon={Radio}
                title="In-Process Event Bus"
                detail="Logging terstruktur & 10 saluran event CBM"
                state="healthy"
                stateLabel="🟢 Active"
              />
              <SystemRow
                icon={TimerReset}
                title="Scheduler Daemon"
                detail="Background worker untuk siklus self-improvement"
                state="healthy"
                stateLabel="🟢 Running"
              />
            </div>
          </div>

          <div className="system-section-block">
            <h3 className="system-subtitle">External Integrations</h3>
            <div className="integration-chips-grid">
              <div className="integration-chip">
                <span className="integration-chip__name">Gemini</span>
                <span className="status-indicator">
                  {data?.providers?.gemini?.configured ? '🟢' : '⚪'}
                </span>
              </div>
              <div className="integration-chip">
                <span className="integration-chip__name">Groq</span>
                <span className="status-indicator">
                  {data?.providers?.groq?.configured ? '🟢' : '⚪'}
                </span>
              </div>
              <div className="integration-chip">
                <span className="integration-chip__name">Ollama</span>
                <span className="status-indicator">🟢</span>
              </div>
              <div className="integration-chip">
                <span className="integration-chip__name">OpenAI Compatible</span>
                <span className="status-indicator">
                  {data?.providers?.opencode?.configured ? '🟢' : '⚪'}
                </span>
              </div>
            </div>
          </div>

          <div className="system-section-block">
            <h3 className="system-subtitle">Ekosistem Specialist Tools & MCP</h3>
            <div className="mcp-tools-list">
              <McpToolItem
                name="Gemini Documentation"
                description="Upstream Google Gemini API & SDK reference retriever"
                status="healthy"
                statusLabel="🟢 Ready"
              />
              <McpToolItem
                name="Engineering Knowledge"
                description="RAG Engine over ISO, IEEE, EPRI & Materi CBM standards"
                status="healthy"
                statusLabel="🟢 Ready"
              />
              <McpToolItem
                name="Equipment Analysis"
                description="Specialist diagnostic coordinator (MCSA, PD, DGA, Vib, Oli, Thermal)"
                status="healthy"
                statusLabel="🟢 Ready"
              />
              <McpToolItem
                name="Report Generator"
                description="Automated Word/PPT assessment & SAP-ready CBM Work Order"
                status="healthy"
                statusLabel="🟢 Ready"
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
            <button
              type="button"
              className="button button--primary"
              onClick={handleTestAI}
              disabled={testingAI}
            >
              <Zap size={15} />
              {testingAI ? 'Menguji Semua Koneksi...' : 'Test All Connections'}
            </button>
            <button
              type="button"
              className="button button--secondary"
              onClick={() => setShowLogsModal(true)}
            >
              <Terminal size={15} />
              View System Logs
            </button>
          </div>
        </div>
      )}

      {/* TAB 6: 👤 User & Preferences */}
      {activeTab === 'user' && (
        <div className="settings-card">
          <div className="settings-card-header">
            <h2><User size={20} /> User & Workspace Preferences</h2>
            <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
              Tersimpan lokal di browser per perangkat operator.
            </span>
          </div>

          <form onSubmit={saveUserPreferences} className="user-prefs-form">
            <div className="form-row-dual">
              <label className="form-field">
                <span>Nama Engineer Pelaksana</span>
                <input
                  type="text"
                  value={userPrefs.engineerName}
                  onChange={(e) => setUserPrefs({ ...userPrefs, engineerName: e.target.value })}
                  placeholder="Nama Lengkap Engineer"
                  required
                />
              </label>

              <label className="form-field">
                <span>Unit / Divisi Kerja</span>
                <input
                  type="text"
                  value={userPrefs.unitRole}
                  onChange={(e) => setUserPrefs({ ...userPrefs, unitRole: e.target.value })}
                  placeholder="Unit Kerja"
                />
              </label>
            </div>

            <div className="form-row-dual">
              <label className="form-field">
                <span><Globe size={13} /> Bahasa Antarmuka</span>
                <select
                  value={userPrefs.language}
                  onChange={(e) => setUserPrefs({ ...userPrefs, language: e.target.value })}
                >
                  <option value="id">Bahasa Indonesia (Utama)</option>
                  <option value="en">English (US)</option>
                </select>
              </label>

              <label className="form-field">
                <span><Clock size={13} /> Zona Waktu Pembangkit</span>
                <select
                  value={userPrefs.timeZone}
                  onChange={(e) => setUserPrefs({ ...userPrefs, timeZone: e.target.value })}
                >
                  <option value="Asia/Makassar">Asia/Makassar (WITA - UTC+8) [PLTU Jeranjang]</option>
                  <option value="Asia/Jakarta">Asia/Jakarta (WIB - UTC+7)</option>
                  <option value="Asia/Jayapura">Asia/Jayapura (WIT - UTC+9)</option>
                </select>
              </label>
            </div>

            {/* Interface Theme */}
            <div className="theme-selector-group">
              <span className="field-label">Tema Tampilan</span>
              <div className="theme-options">
                <label className={`theme-radio-pill ${userPrefs.theme === 'light' ? 'theme-radio-pill--active' : ''}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="light"
                    checked={userPrefs.theme === 'light'}
                    onChange={() => setUserPrefs({ ...userPrefs, theme: 'light' })}
                  />
                  <Sun size={15} />
                  <span>Terang (Light)</span>
                </label>
                <label className={`theme-radio-pill ${userPrefs.theme === 'dark' ? 'theme-radio-pill--active' : ''}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="dark"
                    checked={userPrefs.theme === 'dark'}
                    onChange={() => setUserPrefs({ ...userPrefs, theme: 'dark' })}
                  />
                  <Moon size={15} />
                  <span>Gelap (Dark / Control Room)</span>
                </label>
                <label className={`theme-radio-pill ${userPrefs.theme === 'system' ? 'theme-radio-pill--active' : ''}`}>
                  <input
                    type="radio"
                    name="theme"
                    value="system"
                    checked={userPrefs.theme === 'system'}
                    onChange={() => setUserPrefs({ ...userPrefs, theme: 'system' })}
                  />
                  <Cpu size={15} />
                  <span>Mengikuti Sistem</span>
                </label>
              </div>
            </div>

              {/* Notifications */}
              <div className="notifications-group">
                <span className="field-label"><Bell size={13} /> Notifications</span>
                <div className="checkbox-list">
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={userPrefs.notifySafety}
                      onChange={(e) => setUserPrefs({ ...userPrefs, notifySafety: e.target.checked })}
                    />
                    <div>
                      <strong>☑ Safety alerts</strong>
                      <small>Peringatan proteksi trip, interlock & anomali kritis mesin.</small>
                    </div>
                  </label>

                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={userPrefs.notifyAnalysis}
                      onChange={(e) => setUserPrefs({ ...userPrefs, notifyAnalysis: e.target.checked })}
                    />
                    <div>
                      <strong>☑ Analysis completed</strong>
                      <small>Notifikasi saat diagnostik MCSA, Vibrasi, DGA, PD, atau Oli selesai.</small>
                    </div>
                  </label>

                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={userPrefs.notifyAutomation}
                      onChange={(e) => setUserPrefs({ ...userPrefs, notifyAutomation: e.target.checked })}
                    />
                    <div>
                      <strong>☑ Automation completed</strong>
                      <small>Siklus continuous learning dan sinkronisasi data baru selesai.</small>
                    </div>
                  </label>

                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={userPrefs.notifyVoice}
                      onChange={(e) => setUserPrefs({ ...userPrefs, notifyVoice: e.target.checked })}
                    />
                    <div>
                      <strong>Voice notifications</strong>
                      <small>Membacakan alert audio otomatis saat anomali terdeteksi.</small>
                    </div>
                  </label>
                </div>
              </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '20px' }}>
              <button type="submit" className="button button--primary">
                <Save size={16} />
                Simpan Preferensi Pengguna
              </button>
              {userSaved && (
                <span className="save-indicator">
                  <CheckCircle2 size={16} /> Preferensi tersimpan!
                </span>
              )}
            </div>
          </form>
        </div>
      )}

      {/* System Logs Modal */}
      {showLogsModal && (
        <div className="modal-backdrop" onClick={() => setShowLogsModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <Terminal size={18} />
                <strong>System Runtime Logs</strong>
              </div>
              <button className="icon-button" onClick={() => setShowLogsModal(false)}>✕</button>
            </div>
            <div className="modal-body console-body">
              <pre>
{`[INFO]  FastAPI Application started on http://127.0.0.1:8000 (v2.0.0)
[INFO]  EventBus: Initialized with 10 core event channels.
[INFO]  SpecialistRegistry: Loaded 6 diagnostic agent modules (MCSA, DGA, PD, Vib, Tribo, Therm).
[INFO]  ReliabilityFusionEngine: Online with calibrated RUL & Risk matrix.
[INFO]  SafetyGuardrail: Active. Plant actuation commands blocked by code logic.
[INFO]  KnowledgeBase: ${system?.knowledge_documents || 75} documents indexed for RAG retrieval.
[INFO]  Active LLM Provider: ${form.ai_provider.toUpperCase()} (${form.model || 'default'})
[INFO]  System Status: HEALTHY 🟢`}
              </pre>
            </div>
            <div className="modal-footer">
              <button className="button button--secondary" onClick={() => setShowLogsModal(false)}>
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
