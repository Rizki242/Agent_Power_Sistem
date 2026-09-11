import { useEffect, useMemo, useState } from 'react'
import {
  Check, ChevronRight, CircleAlert, Database, Filter, RefreshCw, Search,
  Server, SlidersHorizontal, X,
} from 'lucide-react'
import { getDataWorkspace, getEquipmentModules, setEquipmentModule } from './api.js'

const EMPTY_DATA = { assets: [], modules: [] }

function normalizeStatus(status) {
  const value = String(status || '').toLowerCase()
  if (['normal', 'healthy', 'active', 'online'].includes(value)) return 'healthy'
  if (['alarm', 'warning', 'watch'].includes(value)) return 'attention'
  if (['critical', 'high', 'error'].includes(value)) return 'critical'
  return 'neutral'
}

function DataStatus({ status }) {
  const label = status || 'Tidak tersedia'
  return <span className={`data-status data-status--${normalizeStatus(status)}`}><i />{label}</span>
}

function SourceRail({ assets, modules }) {
  const counts = assets.reduce((result, asset) => {
    result[asset.domain] = (result[asset.domain] || 0) + 1
    return result
  }, {})

  return (
    <section className="source-rail" aria-label="Sumber data terhubung">
      <div className="source-rail__intro"><Server size={21} /><div><strong>Sumber terhubung</strong><span>Registry equipment per domain</span></div></div>
      {modules.map((module) => (
        <div className="source-item" key={module.module_id}>
          <span className={`source-item__line source-item__line--${module.status.toLowerCase()}`} />
          <div><strong>{module.module_id.replaceAll('_', ' ')}</strong><span>{counts[module.module_id] || 0} equipment</span></div>
          <DataStatus status={module.status} />
        </div>
      ))}
    </section>
  )
}

function ConfigurationPanel({ asset, onClose }) {
  const [state, setState] = useState({ status: 'loading', modules: [], message: '' })

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading', modules: [], message: '' })
    getEquipmentModules(asset.id, controller.signal)
      .then((result) => setState({ status: 'ready', modules: result.modules ?? [], message: '' }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ status: 'error', modules: [], message: 'Konfigurasi modul tidak dapat dimuat.' })
      })
    return () => controller.abort()
  }, [asset.id])

  async function toggleModule(module) {
    setState((current) => ({ ...current, status: 'saving', message: '' }))
    try {
      await setEquipmentModule(asset.id, module.module_id, !module.enabled)
      setState((current) => ({
        status: 'ready',
        message: 'Konfigurasi tersimpan dan dicatat dalam audit log.',
        modules: current.modules.map((item) => item.module_id === module.module_id ? { ...item, enabled: !item.enabled } : item),
      }))
    } catch {
      setState((current) => ({ ...current, status: 'error', message: 'Perubahan gagal disimpan. Periksa koneksi API.' }))
    }
  }

  return (
    <aside className="config-panel" aria-label={`Konfigurasi ${asset.name}`}>
      <div className="config-panel__header">
        <div><span>Konfigurasi equipment</span><h2>{asset.name || asset.id}</h2><code>{asset.id}</code></div>
        <button className="icon-button" onClick={onClose} aria-label="Tutup konfigurasi"><X /></button>
      </div>
      <dl className="asset-facts">
        <div><dt>Unit</dt><dd>{asset.unit}</dd></div>
        <div><dt>Domain sumber</dt><dd>{asset.domain}</dd></div>
        <div><dt>Kelas</dt><dd>{asset.equipment_class || 'Belum diklasifikasi'}</dd></div>
      </dl>
      <div className="config-section">
        <div><h3>Modul analisis</h3><p>Tentukan agent engineering yang boleh memproses equipment ini.</p></div>
        {state.status === 'loading' ? <div className="inline-loading"><RefreshCw size={17} />Memuat konfigurasi</div> :
          <div className="module-switches">
            {state.modules.map((module) => (
              <label key={module.module_id} className="module-switch">
                <span><strong>{module.name}</strong><small>{module.module_id}</small></span>
                <input type="checkbox" checked={module.enabled} disabled={state.status === 'saving'} onChange={() => toggleModule(module)} />
                <i aria-hidden="true"><Check size={13} /></i>
              </label>
            ))}
          </div>}
      </div>
      {state.message && <div className={`config-message config-message--${state.status}`}><CircleAlert size={16} />{state.message}</div>}
      <div className="config-guard"><strong>Perubahan terkendali</strong><span>Konfigurasi dicatat oleh backend dan baru berlaku pada analisis berikutnya.</span></div>
    </aside>
  )
}

export default function DataWorkspace() {
  const [data, setData] = useState(EMPTY_DATA)
  const [status, setStatus] = useState('loading')
  const [query, setQuery] = useState('')
  const [domain, setDomain] = useState('all')
  const [unit, setUnit] = useState('all')
  const [selectedAsset, setSelectedAsset] = useState(null)

  function loadData() {
    const controller = new AbortController()
    setStatus('loading')
    getDataWorkspace(controller.signal)
      .then((result) => { setData(result); setStatus('ready') })
      .catch((error) => { if (error.name !== 'AbortError') setStatus('error') })
    return controller
  }

  useEffect(() => {
    const controller = loadData()
    return () => controller.abort()
  }, [])

  const domains = useMemo(() => [...new Set(data.assets.map((asset) => asset.domain))].sort(), [data.assets])
  const units = useMemo(() => [...new Set(data.assets.map((asset) => asset.unit))].sort(), [data.assets])
  const filteredAssets = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return data.assets.filter((asset) => {
      const matchesQuery = !needle || [asset.id, asset.name, asset.equipment_class].some((value) => String(value || '').toLowerCase().includes(needle))
      return matchesQuery && (domain === 'all' || asset.domain === domain) && (unit === 'all' || asset.unit === unit)
    })
  }, [data.assets, domain, query, unit])
  const activeSources = data.modules.filter((module) => module.status === 'ACTIVE').length
  const knownStatuses = data.assets.filter((asset) => asset.status).length

  return (
    <div className="page data-page">
      <header className="page-header">
        <div><h1>Data</h1><p>Pantau registry, sumber, dan konfigurasi pemrosesan data agent.</p></div>
        <button className="button button--secondary" onClick={() => loadData()} disabled={status === 'loading'}><RefreshCw size={17} />Muat ulang</button>
      </header>

      <section className="data-summary" aria-label="Ringkasan data">
        <div><Database size={19} /><span>Equipment terdaftar</span><strong>{status === 'ready' ? data.assets.length : '—'}</strong></div>
        <div><Server size={19} /><span>Sumber aktif</span><strong>{status === 'ready' ? `${activeSources}/${data.modules.length}` : '—'}</strong></div>
        <div><CircleAlert size={19} /><span>Memiliki status sumber</span><strong>{status === 'ready' ? `${knownStatuses}/${data.assets.length}` : '—'}</strong></div>
      </section>

      {status === 'error' ? <div className="notice notice--error"><strong>Registry data tidak dapat dimuat.</strong><span>Periksa FastAPI lalu coba muat ulang.</span></div> : null}
      {status === 'ready' ? <SourceRail assets={data.assets} modules={data.modules} /> : null}

      <section className="data-table-panel">
        <div className="data-toolbar">
          <div className="search-field"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari ID, nama, atau kelas equipment" aria-label="Cari equipment" /></div>
          <div className="filter-field"><Filter size={16} /><select value={domain} onChange={(event) => setDomain(event.target.value)} aria-label="Filter domain"><option value="all">Semua domain</option>{domains.map((item) => <option key={item}>{item}</option>)}</select></div>
          <div className="filter-field"><SlidersHorizontal size={16} /><select value={unit} onChange={(event) => setUnit(event.target.value)} aria-label="Filter unit"><option value="all">Semua unit</option>{units.map((item) => <option key={item}>{item}</option>)}</select></div>
        </div>
        <div className="table-caption"><strong>Registry equipment</strong><span>{filteredAssets.length} dari {data.assets.length} ditampilkan</span></div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead><tr><th>Equipment</th><th>Unit</th><th>Domain</th><th>Status sumber</th><th><span className="sr-only">Aksi</span></th></tr></thead>
            <tbody>
              {filteredAssets.map((asset) => (
                <tr key={`${asset.domain}-${asset.id}`}>
                  <td><button className="asset-link" onClick={() => setSelectedAsset(asset)}><strong>{asset.name || asset.id}</strong><code>{asset.id}</code></button></td>
                  <td>{asset.unit}</td><td><span className="domain-chip">{asset.domain}</span></td><td><DataStatus status={asset.status} /></td>
                  <td><button className="row-action" onClick={() => setSelectedAsset(asset)} aria-label={`Konfigurasi ${asset.name || asset.id}`}><ChevronRight size={18} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {status === 'loading' ? <div className="table-state"><RefreshCw size={20} />Memuat registry data</div> : null}
          {status === 'ready' && !filteredAssets.length ? <div className="table-state"><Search size={20} />Tidak ada equipment yang cocok dengan filter.</div> : null}
        </div>
      </section>
      {selectedAsset ? <><button className="panel-backdrop" onClick={() => setSelectedAsset(null)} aria-label="Tutup konfigurasi" /><ConfigurationPanel asset={selectedAsset} onClose={() => setSelectedAsset(null)} /></> : null}
    </div>
  )
}
