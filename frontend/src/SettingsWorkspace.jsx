import { useCallback, useEffect, useState } from 'react'
import { Bot, Check, CircleAlert, Cloud, Database, Download, HardDrive, KeyRound, LockKeyhole, RefreshCw, Save, Server, Settings, ShieldCheck, TimerReset } from 'lucide-react'
import { getSettingsOverview, saveAISettings } from './api.js'

const PROVIDER_NAMES = { gemini: 'Google Gemini', groq: 'Groq', opencode: 'OpenAI compatible', ollama: 'Ollama lokal' }

function SystemRow({ icon: Icon, title, detail, state, stateLabel }) {
  return <div className="system-check-row"><span className="system-check-row__icon"><Icon size={18} /></span><div><strong>{title}</strong><span>{detail}</span></div><span className={`system-state system-state--${state}`}><i />{stateLabel}</span></div>
}

export default function SettingsWorkspace() {
  const [data, setData] = useState(null)
  const [form, setForm] = useState({ ai_enabled: false, ai_provider: 'gemini', model: '' })
  const [state, setState] = useState({ status: 'loading', saving: false, message: '' })

  const load = useCallback((signal) => {
    setState((current) => ({ ...current, status: 'loading' }))
    return getSettingsOverview(signal).then((result) => {
      setData(result)
      const provider = result.active_provider
      setForm({ ai_enabled: result.ai_enabled, ai_provider: provider, model: result.providers[provider]?.model || '' })
      setState({ status: 'ready', saving: false, message: '' })
    }).catch((error) => {
      if (error.name !== 'AbortError') setState({ status: 'error', saving: false, message: 'Health check gagal. Pastikan FastAPI berjalan di port 8000.' })
    })
  }, [])

  useEffect(() => { const controller = new AbortController(); load(controller.signal); return () => controller.abort() }, [load])


  function chooseProvider(provider) {
    setForm((current) => ({ ...current, ai_provider: provider, model: data.providers[provider]?.model || data.providers[provider]?.models?.[0] || '' }))
  }

  async function save(event) {
    event.preventDefault()
    setState((current) => ({ ...current, saving: true, message: '' }))
    try {
      const payload = { ...form }
      if (form.ai_provider === 'ollama') payload.ollama_host = 'http://localhost:11434'
      const result = await saveAISettings(payload)
      setState({ status: 'ready', saving: false, message: result.message })
      await load()
    } catch (error) {
      setState({ status: 'ready', saving: false, message: `Konfigurasi gagal disimpan: ${error.message}` })
    }
  }

  function exportSafeConfig() {
    if (!data) return
    const safe = { ai_enabled: form.ai_enabled, ai_provider: form.ai_provider, model: form.model, system: data.system, version: data.version, exported_at: new Date().toISOString() }
    const url = URL.createObjectURL(new Blob([JSON.stringify(safe, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = 'pple-settings-safe.json'; link.click(); URL.revokeObjectURL(url)
  }

  const provider = data?.providers?.[form.ai_provider]
  const system = data?.system
  return <div className="page settings-page">
    <header className="page-header"><div><h1>Settings & System Control</h1><p>Kelola koneksi dan preferensi runtime tanpa mengubah aturan engineering.</p></div><button className="button button--secondary" onClick={exportSafeConfig} disabled={!data}><Download size={17} />Export aman</button></header>

    <section className="control-header"><div><span className="control-header__mark"><Settings size={24} /></span><div><span>Control plane</span><h2>{state.status === 'ready' ? 'Sistem siap digunakan' : state.status === 'error' ? 'Perlu pemeriksaan' : 'Memeriksa komponen'}</h2></div></div><button className="icon-button" onClick={() => load()} aria-label="Jalankan health check"><RefreshCw size={19} /></button></section>
    {state.message ? <div className={`notice ${state.message.includes('gagal') ? 'notice--error' : 'notice--success'}`}>{state.message.includes('gagal') ? <CircleAlert size={17} /> : <Check size={17} />}<span>{state.message}</span></div> : null}

    <div className="settings-layout">
      <section className="provider-control"><div className="section-heading"><div><h2>Lapisan AI</h2><p>AI memperkaya narasi; keputusan kondisi tetap berasal dari rule lokal.</p></div><Bot size={22} /></div>
        {data ? <form onSubmit={save}>
          <label className="settings-master-switch"><span><strong>Aktifkan bantuan AI</strong><small>Fallback rule-based tetap berjalan saat provider gagal.</small></span><input type="checkbox" checked={form.ai_enabled} onChange={(event) => setForm({ ...form, ai_enabled: event.target.checked })} /><i /></label>
          <fieldset className="provider-picker"><legend>Provider</legend>{Object.entries(data.providers).map(([id, item]) => <button type="button" key={id} className={form.ai_provider === id ? 'provider-option provider-option--active' : 'provider-option'} onClick={() => chooseProvider(id)}><span>{id === 'ollama' ? <HardDrive size={18} /> : <Cloud size={18} />}</span><div><strong>{PROVIDER_NAMES[id]}</strong><small>{item.configured ? 'Credential terdeteksi' : id === 'ollama' ? 'Runtime lokal' : 'Key belum tersedia'}</small></div>{item.configured ? <Check size={16} /> : <KeyRound size={16} />}</button>)}</fieldset>
          <label className="form-field"><span>Model aktif</span><select value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })}>{provider?.models.map((model) => <option key={model} value={model}>{model}</option>)}</select></label>
          <div className="secret-guidance"><LockKeyhole size={18} /><div><strong>Secret tidak dikelola dari browser</strong><span>Simpan API key melalui environment atau <code>.streamlit/secrets.toml</code>. UI hanya menampilkan apakah credential terdeteksi.</span></div></div>
          <button className="button button--primary" disabled={state.saving || !form.model}><Save size={17} />{state.saving ? 'Menyimpan...' : 'Simpan preferensi'}</button>
        </form> : <div className="automation-empty"><Server size={26} /><strong>Konfigurasi belum tersedia</strong><span>Jalankan health check setelah backend aktif.</span></div>}
      </section>

      <aside className="system-control"><div className="section-heading"><div><h2>Status komponen</h2><p>Diperiksa {data ? new Date(data.generated_at).toLocaleString('id-ID') : '—'}.</p></div></div>
        {system ? <div className="system-check-list">
          <SystemRow icon={Server} title="FastAPI" detail={`Backend v${data.version}`} state="healthy" stateLabel="Online" />
          <SystemRow icon={Database} title="Penyimpanan data" detail={`${system.data_store === 'CUSTOM' ? 'Direktori kustom' : 'Direktori bawaan'} · ${system.max_backups} backup`} state="healthy" stateLabel="Siap" />
          <SystemRow icon={HardDrive} title="Knowledge base" detail={`${system.knowledge_documents} dokumen JSON`} state={system.knowledge_documents ? 'healthy' : 'watch'} stateLabel={system.knowledge_documents ? 'Terindeks' : 'Kosong'} />
          <SystemRow icon={TimerReset} title="Scheduler" detail={`${system.automation_workflows} workflow tersimpan`} state="neutral" stateLabel="Configured" />
          <SystemRow icon={ShieldCheck} title="API protection" detail={system.api_auth_enabled ? 'X-API-Key diwajibkan' : 'Hanya aman untuk localhost'} state={system.api_auth_enabled ? 'healthy' : 'watch'} stateLabel={system.api_auth_enabled ? 'Aktif' : 'Terbuka'} />
        </div> : null}
        <div className="engineering-lock"><ShieldCheck size={21} /><div><strong>Engineering core dikunci</strong><span>Threshold, severity mapping, dan safety guardrail tidak dapat diubah dari halaman ini.</span></div></div>
      </aside>
    </div>
  </div>
}
