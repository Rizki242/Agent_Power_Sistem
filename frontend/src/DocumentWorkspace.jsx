import { useEffect, useMemo, useRef, useState } from 'react'
import {
  BookOpen, CheckCircle2, File, FileJson, FileText, Library, Plus,
  RefreshCw, Search, Sparkles, Upload, X,
} from 'lucide-react'
import { getMaterials, searchMaterials, uploadMaterial } from './api.js'

const ACCEPTED_FILES = '.pdf,.md,.docx,.json,.txt'

function MaterialIcon({ filename, size = 18 }) {
  return filename?.toLowerCase().endsWith('.json') ? <FileJson size={size} /> : <FileText size={size} />
}

function UploadPanel({ onClose, onUploaded }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')
  const [level, setLevel] = useState('General')
  const [state, setState] = useState({ status: 'idle', message: '' })

  async function submit(event) {
    event.preventDefault()
    if (!file) return setState({ status: 'error', message: 'Pilih dokumen yang akan diproses.' })
    setState({ status: 'uploading', message: 'Dokumen sedang diekstrak dan diindeks.' })
    try {
      const result = await uploadMaterial({ file, title, tags, level })
      setState({ status: 'success', message: result.message })
      onUploaded(result.document)
    } catch (error) {
      setState({ status: 'error', message: error.message })
    }
  }

  return (
    <aside className="upload-panel" aria-label="Tambah dokumen">
      <div className="config-panel__header">
        <div><span>Knowledge ingestion</span><h2>Tambah dokumen</h2><p>Ekstrak isi dan simpan sebagai memori yang dapat dicari.</p></div>
        <button className="icon-button" onClick={onClose} aria-label="Tutup upload"><X /></button>
      </div>
      <form className="upload-form" onSubmit={submit}>
        <button type="button" className={`drop-zone ${file ? 'drop-zone--selected' : ''}`} onClick={() => inputRef.current?.click()}>
          <input ref={inputRef} type="file" accept={ACCEPTED_FILES} onChange={(event) => setFile(event.target.files?.[0] || null)} />
          {file ? <><CheckCircle2 size={29} /><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></> : <><Upload size={29} /><strong>Pilih dokumen</strong><span>PDF, Markdown, DOCX, JSON, atau TXT · Maks. 20 MB</span></>}
        </button>
        <label className="form-field"><span>Judul <small>Opsional</small></span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Gunakan nama file jika kosong" /></label>
        <label className="form-field"><span>Tag <small>Pisahkan dengan koma</small></span><input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="vibration, bearing, SOP" /></label>
        <label className="form-field"><span>Tingkat materi</span><select value={level} onChange={(event) => setLevel(event.target.value)}><option>General</option><option>Basic</option><option>Intermediate</option><option>Advanced</option></select></label>
        {state.message ? <div className={`upload-message upload-message--${state.status}`}>{state.status === 'success' ? <CheckCircle2 size={17} /> : <Sparkles size={17} />}<span>{state.message}</span></div> : null}
        <button className="button button--primary" disabled={state.status === 'uploading' || state.status === 'success'}>{state.status === 'uploading' ? <><RefreshCw size={17} />Memproses dokumen</> : 'Proses dan simpan'}</button>
      </form>
    </aside>
  )
}

function RetrievalResult({ result }) {
  const title = result.title || result.source || 'Hasil pengetahuan'
  const excerpt = result.content || result.text || result.chunk || result.snippet || 'Konten tersedia di indeks knowledge.'
  return <article className="retrieval-result"><div><BookOpen size={18} /><strong>{title}</strong></div><p>{excerpt}</p>{result.source ? <span>Sumber: {result.source}</span> : null}</article>
}

export default function DocumentWorkspace() {
  const [materials, setMaterials] = useState([])
  const [status, setStatus] = useState('loading')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searchStatus, setSearchStatus] = useState('idle')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [recentUpload, setRecentUpload] = useState(null)

  function loadMaterials() {
    const controller = new AbortController()
    setStatus('loading')
    getMaterials(controller.signal)
      .then((items) => { setMaterials(items); setStatus('ready') })
      .catch((error) => { if (error.name !== 'AbortError') setStatus('error') })
    return controller
  }

  useEffect(() => {
    const controller = loadMaterials()
    return () => controller.abort()
  }, [])

  async function runSearch(event) {
    event.preventDefault()
    if (!query.trim()) return
    setSearchStatus('loading')
    try {
      const matches = await searchMaterials(query.trim())
      setResults(matches)
      setSearchStatus('ready')
    } catch {
      setResults([])
      setSearchStatus('error')
    }
  }

  const formats = useMemo(() => new Set(materials.map((item) => item.filename?.split('.').pop()?.toUpperCase()).filter(Boolean)), [materials])

  return (
    <div className="page documents-page">
      <header className="page-header">
        <div><h1>Dokumen</h1><p>Ubah referensi teknis menjadi pengetahuan yang dapat ditemukan agent.</p></div>
        <button className="button button--primary" onClick={() => setUploadOpen(true)}><Plus size={18} />Tambah dokumen</button>
      </header>

      <section className="document-summary" aria-label="Ringkasan dokumen">
        <div><Library size={20} /><span>Dokumen terindeks</span><strong>{status === 'ready' ? materials.length : '—'}</strong></div>
        <div><File size={20} /><span>Format tersimpan</span><strong>{status === 'ready' ? formats.size : '—'}</strong></div>
        <div><Sparkles size={20} /><span>Retrieval</span><strong>Keyword aktif</strong></div>
      </section>

      {recentUpload ? <div className="notice notice--success"><CheckCircle2 size={18} /><strong>{recentUpload.title} siap dicari.</strong><span>{recentUpload.section_count} bagian ditambahkan ke knowledge base.</span></div> : null}
      {status === 'error' ? <div className="notice notice--error"><strong>Daftar dokumen tidak dapat dimuat.</strong><span>Periksa koneksi API lalu muat ulang.</span></div> : null}

      <div className="document-grid">
        <section className="document-library">
          <div className="section-heading"><div><h2>Knowledge library</h2><p>Dokumen JSON hasil ekstraksi yang aktif di indeks.</p></div><button className="icon-button" onClick={() => loadMaterials()} aria-label="Muat ulang dokumen"><RefreshCw size={18} /></button></div>
          <div className="document-list" role="list">
            {materials.map((material) => <article className="document-row" role="listitem" key={material.id}><div className="document-row__icon"><MaterialIcon filename={material.filename} /></div><div><strong>{material.title}</strong><span>{material.filename}</span></div><span className="document-level">{material.level || 'General'}</span><span className="indexed-state"><i />Terindeks</span></article>)}
            {status === 'loading' ? <div className="document-empty"><RefreshCw size={21} />Memuat knowledge library</div> : null}
            {status === 'ready' && !materials.length ? <div className="document-empty"><FileText size={24} /><strong>Belum ada dokumen</strong><span>Tambahkan dokumen pertama untuk membangun knowledge base.</span></div> : null}
          </div>
        </section>

        <aside className="retrieval-panel">
          <div className="section-heading"><div><h2>Uji retrieval</h2><p>Periksa apa yang ditemukan agent sebelum dipakai.</p></div></div>
          <form className="retrieval-search" onSubmit={runSearch}><div className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Contoh: batas vibrasi pompa" aria-label="Cari knowledge" /></div><button className="button button--secondary">Cari</button></form>
          <div className="retrieval-list">
            {searchStatus === 'idle' ? <div className="retrieval-empty"><Search size={25} /><strong>Uji pengetahuan agent</strong><span>Masukkan pertanyaan atau kata kunci untuk melihat sumber yang ditemukan.</span></div> : null}
            {searchStatus === 'loading' ? <div className="retrieval-empty"><RefreshCw size={22} />Mencari knowledge</div> : null}
            {searchStatus === 'ready' && results.map((result, index) => <RetrievalResult key={`${result.source || result.title}-${index}`} result={result} />)}
            {searchStatus === 'ready' && !results.length ? <div className="retrieval-empty"><Search size={22} /><strong>Tidak ada hasil relevan</strong><span>Coba istilah engineering yang lebih spesifik.</span></div> : null}
            {searchStatus === 'error' ? <div className="retrieval-empty retrieval-empty--error"><strong>Pencarian gagal</strong><span>Periksa koneksi API lalu coba lagi.</span></div> : null}
          </div>
        </aside>
      </div>
      {uploadOpen ? <><button className="panel-backdrop" onClick={() => setUploadOpen(false)} aria-label="Tutup upload" /><UploadPanel onClose={() => setUploadOpen(false)} onUploaded={(document) => { setRecentUpload(document); loadMaterials() }} /></> : null}
    </div>
  )
}
