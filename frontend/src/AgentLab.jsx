import { useCallback, useEffect, useState } from 'react'
import { Activity, BrainCircuit, Check, CircleAlert, FlaskConical, Gauge, History, Play, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'
import { getAgentLab, learnFromHistory, runHarnessEvaluation, runImprovementCycle } from './api.js'

const EMPTY = { status: {}, benchmarks: {}, harness: {}, patterns: [] }

function Metric({ label, value, suffix = '' }) {
  const numeric = Number(value)
  const normalized = Number.isFinite(numeric) ? Math.max(0, Math.min(100, numeric * 50)) : 0
  return <div className="lab-metric"><div><span>{label}</span><strong>{Number.isFinite(numeric) ? numeric.toFixed(2) : '—'}{value != null ? suffix : ''}</strong></div><div className="lab-meter"><i style={{ width: `${normalized}%` }} /></div></div>
}

function ExperimentButton({ icon: Icon, title, detail, busy, onClick }) {
  return <button className="experiment-action" disabled={busy} onClick={onClick}><span className="experiment-action__icon"><Icon size={19} /></span><span><strong>{title}</strong><small>{detail}</small></span><Play size={16} /></button>
}

export default function AgentLab() {
  const [data, setData] = useState(EMPTY)
  const [state, setState] = useState({ status: 'loading', action: '', message: '' })

  const load = useCallback((signal) => {
    setState((current) => ({ ...current, status: 'loading' }))
    return getAgentLab(signal).then((result) => {
      setData(result)
      setState((current) => ({ ...current, status: 'ready' }))
    }).catch((error) => {
      if (error.name !== 'AbortError') setState({ status: 'error', action: '', message: 'Data Agent Lab belum dapat dimuat.' })
    })
  }, [])

  useEffect(() => { const controller = new AbortController(); load(controller.signal); return () => controller.abort() }, [load])

  async function execute(action, runner) {
    setState((current) => ({ ...current, action, message: '' }))
    try {
      const result = await runner()
      const message = result.message || (action === 'harness' ? 'Evaluasi environment selesai.' : 'Eksperimen selesai dan hasil telah dicatat.')
      setState({ status: 'ready', action: '', message })
      await load()
    } catch (error) {
      setState({ status: 'ready', action: '', message: `Eksperimen gagal: ${error.message}` })
    }
  }

  const status = data.status
  const benchmarkRows = data.benchmarks.results || data.benchmarks.benchmark_results || []
  const passed = benchmarkRows.filter((item) => item.status === 'PASSED' || item.passed === true).length
  const weights = Object.entries(status.category_weights || {})
  const cycles = status.recent_cycles || []
  const score = status.best_score ?? data.benchmarks.accuracy_score ?? 0

  return <div className="page agent-lab-page">
    <header className="page-header"><div><h1>Agent Learning Lab</h1><p>Ukur kemampuan, jalankan eksperimen, dan pertahankan hanya perubahan yang terbukti lebih baik.</p></div><span className="lab-guard"><ShieldCheck size={17} />Never-regress aktif</span></header>

    <section className="lab-console">
      <div className="lab-score"><span>Skor terbaik</span><strong>{Number(score).toFixed(1)}</strong><small>dari 100</small></div>
      <div className="lab-console__identity"><div className="lab-orbit"><BrainCircuit size={30} /><i /><i /></div><div><span>Learning engine</span><h2>Generasi {status.generation ?? 0}</h2><p>{status.learning_engine === 'RECURSIVE_SELF_IMPROVEMENT_ACTIVE' ? 'Mesin belajar aktif dan dibatasi rule engineering.' : 'Menunggu status learning engine.'}</p></div></div>
      <div className="lab-console__facts"><div><span>Siklus</span><strong>{status.total_cycles ?? 0}</strong></div><div><span>Perubahan diterima</span><strong>{status.total_accepted_adjustments ?? 0}</strong></div><div><span>Pola tersimpan</span><strong>{data.patterns.length}</strong></div></div>
    </section>

    {state.message ? <div className={`notice ${state.message.includes('gagal') ? 'notice--error' : 'notice--success'}`}>{state.message.includes('gagal') ? <CircleAlert size={17} /> : <Check size={17} />}<span>{state.message}</span></div> : null}

    <div className="lab-layout">
      <section className="lab-bench"><div className="section-heading"><div><h2>Meja eksperimen</h2><p>Setiap aksi memakai data lokal dan meninggalkan jejak evaluasi.</p></div><FlaskConical size={22} /></div>
        <div className="experiment-actions">
          <ExperimentButton icon={Sparkles} title="Optimalkan learning layer" detail="Uji kandidat bobot dan terima hanya skor yang meningkat." busy={Boolean(state.action)} onClick={() => execute('improve', () => runImprovementCycle(4))} />
          <ExperimentButton icon={Activity} title="Evaluasi EnvHarness" detail="Uji agent pada environment dan kontrak yang terbungkus." busy={Boolean(state.action)} onClick={() => execute('harness', runHarnessEvaluation)} />
          <ExperimentButton icon={History} title="Belajar dari histori" detail="Cari precursor degradasi pada data pengukuran aktual." busy={Boolean(state.action)} onClick={() => execute('history', learnFromHistory)} />
        </div>
        <div className="lab-safety"><ShieldCheck size={18} /><div><strong>Yang boleh berubah</strong><span>Ranking skill dan kalibrasi confidence.</span></div><div><strong>Yang dikunci</strong><span>Threshold, rule diagnosis, dan safety guardrail.</span></div></div>
      </section>

      <aside className="lab-metrics"><div className="section-heading"><div><h2>Kalibrasi saat ini</h2><p>Bobot retrieval per domain.</p></div><Gauge size={22} /></div>{weights.length ? weights.map(([name, value]) => <Metric key={name} label={name.replaceAll('_', ' ')} value={value} />) : <div className="automation-empty automation-empty--small"><span>Belum ada bobot tersimpan.</span></div>}</aside>
    </div>

    <div className="lab-evidence-grid">
      <section className="benchmark-panel"><div className="section-heading"><div><h2>Benchmark diagnostik</h2><p>{benchmarkRows.length ? `${passed} dari ${benchmarkRows.length} skenario lulus.` : 'Belum ada hasil benchmark.'}</p></div><button className="icon-button" onClick={() => load()} aria-label="Muat ulang Agent Lab"><RefreshCw size={18} /></button></div>
        <div className="benchmark-list">{benchmarkRows.map((item, index) => <div className="benchmark-row" key={item.benchmark_id || index}><span className={`benchmark-state benchmark-state--${(item.status || (item.passed ? 'PASSED' : 'FAILED')).toLowerCase()}`}>{item.status || (item.passed ? 'PASSED' : 'FAILED')}</span><div><strong>{item.title || item.benchmark_id || `Skenario ${index + 1}`}</strong><span>{item.observed_failure_mode || item.message || item.expected_failure_mode}</span></div></div>)}{!benchmarkRows.length ? <div className="automation-empty automation-empty--small"><FlaskConical size={24} /><span>Benchmark belum menghasilkan rincian.</span></div> : null}</div>
      </section>

      <aside className="cycle-log"><div className="section-heading"><div><h2>Log generasi</h2><p>Lima siklus terbaru.</p></div></div>{cycles.map((cycle, index) => <div className="cycle-row" key={`${cycle.cycle_at || cycle.started_at || 'cycle'}-${index}`}><i /><div><strong>Generasi {cycle.generation ?? '?'}</strong><span>{cycle.baseline_score ?? 0} menjadi {cycle.final_score ?? 0}</span></div><small>{cycle.improved ? 'Diterima' : 'Tetap'}</small></div>)}{!cycles.length ? <div className="automation-empty automation-empty--small"><History size={24} /><span>Belum ada siklus tersimpan.</span></div> : null}</aside>
    </div>
  </div>
}
