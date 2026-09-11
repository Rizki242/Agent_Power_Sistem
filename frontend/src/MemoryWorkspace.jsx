import { useEffect, useMemo, useState } from 'react'
import {
  Archive, Beaker, BookOpen, BrainCircuit, CheckCircle2, ChevronRight,
  FileText, Fingerprint, History, RefreshCw, Search, ShieldCheck, X,
} from 'lucide-react'
import { getMemoryWorkspace } from './api.js'

const EMPTY_MEMORY = { knowledge: [], experiences: [], instructions: [], cycles: [], harnessStatus: 'UNKNOWN' }
const memoryTypes = [
  { id: 'knowledge', label: 'Pengetahuan', icon: BookOpen, description: 'Dokumen dan referensi yang diambil saat dibutuhkan.' },
  { id: 'experiences', label: 'Pengalaman', icon: History, description: 'Kasus terverifikasi dan pelajaran hasil diagnosis.' },
  { id: 'instructions', label: 'Instruksi', icon: ShieldCheck, description: 'Constraint yang membentuk cara agent bekerja.' },
  { id: 'parametric', label: 'Parametrik', icon: Beaker, description: 'Knowledge pack seperti LoRA untuk eksperimen terkontrol.' },
]

function MemoryTypeRail({ selected, onSelect, data }) {
  const counts = { knowledge: data.knowledge.length, experiences: data.experiences.length, instructions: data.instructions.length, parametric: 0 }
  return <div className="memory-type-rail" role="tablist" aria-label="Jenis memori">{memoryTypes.map(({ id, label, icon: Icon, description }) => <button key={id} role="tab" aria-selected={selected === id} className={`memory-type ${selected === id ? 'memory-type--active' : ''}`} onClick={() => onSelect(id)}><Icon size={20} /><span><strong>{label}</strong><small>{description}</small></span><b>{counts[id]}</b></button>)}</div>
}

function ExperienceRow({ item, onSelect }) {
  return <button className="memory-row" onClick={() => onSelect(item)}><span className="memory-row__icon memory-row__icon--experience"><History size={18} /></span><span className="memory-row__body"><strong>{item.title}</strong><small>{item.equipment} · {item.category?.replaceAll('_', ' ')}</small></span><span className="verified-label"><CheckCircle2 size={14} />Terverifikasi</span><ChevronRight size={17} /></button>
}

function KnowledgeRow({ item, onSelect }) {
  return <button className="memory-row" onClick={() => onSelect(item)}><span className="memory-row__icon"><FileText size={18} /></span><span className="memory-row__body"><strong>{item.title}</strong><small>{item.filename}</small></span><span className="memory-scope">{item.level || 'General'}</span><ChevronRight size={17} /></button>
}

function InstructionRow({ item, onSelect }) {
  return <button className="memory-row" onClick={() => onSelect(item)}><span className="memory-row__icon memory-row__icon--instruction"><ShieldCheck size={18} /></span><span className="memory-row__body"><strong>{item.name}</strong><small>{item.description}</small></span><span className="memory-scope">{item.type}</span><ChevronRight size={17} /></button>
}

function MemoryDetail({ type, item, onClose }) {
  const isExperience = type === 'experiences'
  const isInstruction = type === 'instructions'
  return <aside className="memory-detail" aria-label="Detail memori"><div className="config-panel__header"><div><span>{isExperience ? 'Verified experience' : isInstruction ? 'Behavioral instruction' : 'Knowledge document'}</span><h2>{item.title || item.name}</h2><code>{item.id || item.filename || item.type}</code></div><button className="icon-button" onClick={onClose} aria-label="Tutup detail memori"><X /></button></div>
    <div className="provenance-block"><div className="provenance-title"><Fingerprint size={18} /><div><strong>Provenance</strong><span>Asal dan validitas memori</span></div></div><dl>
      <div><dt>Sumber</dt><dd>{isExperience ? item.author : isInstruction ? 'EnvHarness aktif' : item.filename}</dd></div>
      <div><dt>Status</dt><dd>{isExperience ? 'Terverifikasi' : isInstruction ? 'Aktif' : 'Terindeks'}</dd></div>
      <div><dt>Scope</dt><dd>{isExperience ? item.equipment : isInstruction ? item.type : item.level || 'General'}</dd></div>
      <div><dt>Tanggal</dt><dd>{item.verified_at || 'Tidak tersedia'}</dd></div>
    </dl></div>
    {isExperience ? <div className="memory-detail__content"><section><h3>Gejala</h3><ul>{(item.symptoms || []).map((symptom) => <li key={symptom}>{symptom}</li>)}</ul></section><section><h3>Root cause terverifikasi</h3><p>{item.verified_root_cause}</p></section><section><h3>Pelajaran yang disimpan</h3><p>{item.lesson_learned}</p></section><section><h3>Tindakan sebelumnya</h3><p>{item.corrective_action_taken}</p></section></div> : <div className="memory-detail__content"><section><h3>{isInstruction ? 'Aturan perilaku' : 'Metadata dokumen'}</h3><p>{isInstruction ? item.description : 'Isi dokumen diambil melalui retrieval ketika relevan dengan pertanyaan agent.'}</p></section></div>}
    <div className="memory-safety"><Archive size={17} /><span>Memori ini bersifat read-only pada workspace. Perubahan membutuhkan workflow review tersendiri.</span></div>
  </aside>
}

function ParametricMemory() {
  return <div className="parametric-empty"><div className="parametric-graphic"><BrainCircuit size={34} /><span>RAG</span><i /><span>LoRA</span></div><h2>Knowledge pack belum diaktifkan</h2><p>LoRA diposisikan sebagai memori pelengkap, bukan pengganti knowledge retrieval. Aktivasi memerlukan dataset terkurasi, capacity test, routing test, dan evaluasi retensi.</p><div className="readiness-list"><span><CheckCircle2 size={16} />Knowledge retrieval aktif</span><span><CheckCircle2 size={16} />Verified experience tersedia</span><span className="readiness-list__pending"><Beaker size={16} />Benchmark LoRA belum tersedia</span></div></div>
}

export default function MemoryWorkspace() {
  const [data, setData] = useState(EMPTY_MEMORY)
  const [status, setStatus] = useState('loading')
  const [type, setType] = useState('experiences')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)

  function loadMemory() {
    const controller = new AbortController()
    setStatus('loading')
    getMemoryWorkspace(controller.signal).then((result) => { setData(result); setStatus('ready') }).catch((error) => { if (error.name !== 'AbortError') setStatus('error') })
    return controller
  }

  useEffect(() => { const controller = loadMemory(); return () => controller.abort() }, [])

  const currentItems = type === 'parametric' ? [] : data[type]
  const filteredItems = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return currentItems
    return currentItems.filter((item) => JSON.stringify(item).toLowerCase().includes(needle))
  }, [currentItems, query])
  const latestCycle = data.cycles.at(-1)

  return <div className="page memory-page"><header className="page-header"><div><h1>Memori</h1><p>Telusuri apa yang diketahui, dialami, dan dipatuhi oleh agent.</p></div><button className="button button--secondary" onClick={() => loadMemory()} disabled={status === 'loading'}><RefreshCw size={17} />Muat ulang</button></header>
    <section className="memory-summary"><div><BookOpen size={19} /><span>Knowledge</span><strong>{status === 'ready' ? data.knowledge.length : '—'}</strong></div><div><History size={19} /><span>Pengalaman terverifikasi</span><strong>{status === 'ready' ? data.experiences.length : '—'}</strong></div><div><ShieldCheck size={19} /><span>Instruction constraint</span><strong>{status === 'ready' ? data.instructions.length : '—'}</strong></div><div><Beaker size={19} /><span>Knowledge pack</span><strong>Eksperimental</strong></div></section>
    {status === 'error' ? <div className="notice notice--error"><strong>Memory store tidak dapat dimuat.</strong><span>Periksa koneksi API lalu coba lagi.</span></div> : null}
    <MemoryTypeRail selected={type} onSelect={(next) => { setType(next); setSelected(null); setQuery('') }} data={data} />
    <section className="memory-workbench">
      <div className="memory-workbench__header"><div><h2>{memoryTypes.find((item) => item.id === type)?.label}</h2><p>{type === 'experiences' && latestCycle ? `Siklus harness terakhir: ${new Date(latestCycle.timestamp).toLocaleDateString('id-ID')}` : memoryTypes.find((item) => item.id === type)?.description}</p></div>{type !== 'parametric' ? <div className="search-field memory-search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari di memori ini" aria-label="Cari memori" /></div> : null}</div>
      {type === 'parametric' ? <ParametricMemory /> : <div className="memory-list" role="list">{filteredItems.map((item) => type === 'experiences' ? <ExperienceRow key={item.id} item={item} onSelect={setSelected} /> : type === 'instructions' ? <InstructionRow key={item.name} item={item} onSelect={setSelected} /> : <KnowledgeRow key={item.id} item={item} onSelect={setSelected} />)}{status === 'loading' ? <div className="memory-empty"><RefreshCw size={21} />Memuat memory store</div> : null}{status === 'ready' && !filteredItems.length ? <div className="memory-empty"><Search size={22} />Tidak ada memori yang cocok.</div> : null}</div>}
    </section>
    {selected ? <><button className="panel-backdrop" onClick={() => setSelected(null)} aria-label="Tutup panel detail memori" /><MemoryDetail type={type} item={selected} onClose={() => setSelected(null)} /></> : null}
  </div>
}
