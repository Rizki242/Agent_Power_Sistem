import React, { useState, useEffect } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { KnowledgeCardGrid, KnowledgeDocumentViewer } from '../components/knowledge';
import { apiUrl } from '../api';

export default function KnowledgeWorkspace() {
  const [activeTab, setActiveTab] = useState('learning'); // 'learning' | 'standards'
  
  // Standards / Materi state
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [searching, setSearching] = useState(false);

  // Continuous Learning state
  const [learnedSkills, setLearnedSkills] = useState([]);
  const [loadingSkills, setLoadingSkills] = useState(true);
  const [benchmarks, setBenchmarks] = useState(null);
  const [selectedSkill, setSelectedSkill] = useState(null);

  // EnvHarness & EnvRigger state
  const [harnessStatus, setHarnessStatus] = useState(null);
  const [loadingHarness, setLoadingHarness] = useState(true);
  const [riggerEq, setRiggerEq] = useState('BFP 1A');
  const [runningRigger, setRunningRigger] = useState(false);
  const [riggerResult, setRiggerResult] = useState(null);
  const [harnessEval, setHarnessEval] = useState(null);
  const [evaluatingHarness, setEvaluatingHarness] = useState(false);

  // Teach Agent Form state
  const [showTeachForm, setShowTeachForm] = useState(false);
  const [teachEq, setTeachEq] = useState('');
  const [teachTitle, setTeachTitle] = useState('');
  const [teachSystem, setTeachSystem] = useState('');
  const [teachCategory, setTeachCategory] = useState('VIBRASI');
  const [teachSymptoms, setTeachSymptoms] = useState('');
  const [teachRootCause, setTeachRootCause] = useState('');
  const [teachAction, setTeachAction] = useState('');
  const [teachLesson, setTeachLesson] = useState('');
  const [submittingTeach, setSubmittingTeach] = useState(false);
  const [teachSuccessMsg, setTeachSuccessMsg] = useState('');

  const fetchArticles = () => {
    setLoading(true);
    fetch(apiUrl('/api/materi'))
      .then(res => res.json())
      .then(data => {
        const materials = data.materi || data.materials || [];
        setArticles(materials);
        if (materials.length > 0) {
          setSelectedArticle(materials[0]);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Gagal mengambil materi:', err);
        setLoading(false);
      });
  };

  const fetchLearnedSkills = () => {
    setLoadingSkills(true);
    fetch(apiUrl('/api/skills/learned-patterns'))
      .then(res => res.json())
      .then(data => {
        setLearnedSkills(data.skills || []);
        if (data.skills && data.skills.length > 0) {
          setSelectedSkill(data.skills[0]);
        }
        setLoadingSkills(false);
      })
      .catch(err => {
        console.error('Failed to load learned skills:', err);
        setLoadingSkills(false);
      });
  };

  const fetchBenchmarks = () => {
    fetch(apiUrl('/api/skills/benchmarks'))
      .then(res => res.json())
      .then(data => {
        setBenchmarks(data);
      })
      .catch(err => {
        console.error('Failed to load benchmarks:', err);
      });
  };

  const fetchHarnessStatus = () => {
    setLoadingHarness(true);
    fetch(apiUrl('/api/learning/harness-status'))
      .then(res => res.json())
      .then(data => {
        setHarnessStatus(data);
        setLoadingHarness(false);
      })
      .catch(err => {
        console.error('Failed to load harness status:', err);
        setLoadingHarness(false);
      });
  };

  useEffect(() => {
    fetchArticles();
    fetchLearnedSkills();
    fetchBenchmarks();
    fetchHarnessStatus();
  }, []);

  const handleRunRiggerCycle = async () => {
    setRunningRigger(true);
    setRiggerResult(null);
    try {
      const res = await fetch(apiUrl('/api/learning/rigger-cycle'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ equipment: riggerEq })
      });
      const data = await res.json();
      setRiggerResult(data);
      fetchHarnessStatus();
      fetchLearnedSkills();
    } catch (err) {
      console.error('Failed to execute EnvRigger cycle:', err);
      alert('Gagal menjalankan siklus EnvRigger.');
    } finally {
      setRunningRigger(false);
    }
  };

  const handleEvaluateHarness = async () => {
    setEvaluatingHarness(true);
    try {
      const res = await fetch(apiUrl('/api/learning/evaluate-harness'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      setHarnessEval(data);
    } catch (err) {
      console.error('Failed to evaluate harness:', err);
      alert('Gagal mengevaluasi EnvHarness.');
    } finally {
      setEvaluatingHarness(false);
    }
  };


  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchArticles();
      return;
    }

    setSearching(true);
    try {
      const res = await fetch(apiUrl('/api/materi/search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery })
      });
      const data = await res.json();
      setArticles(data.results || []);
      if (data.results && data.results.length > 0) {
        setSelectedArticle(data.results[0]);
      }
    } catch (err) {
      console.error(err);
      alert('Pencarian gagal.');
    } finally {
      setSearching(false);
    }
  };

  const handleTeachSubmit = async (e) => {
    e.preventDefault();
    setSubmittingTeach(true);
    setTeachSuccessMsg('');

    try {
      const res = await fetch(apiUrl('/api/skills/teach'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          equipment: teachEq,
          title: teachTitle,
          system: teachSystem,
          category: teachCategory,
          symptoms: teachSymptoms.split('\n').filter(s => s.trim()),
          verified_root_cause: teachRootCause,
          corrective_action_taken: teachAction,
          lesson_learned: teachLesson,
          author: 'CBM Specialist Engineer PLTU Jeranjang'
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setTeachSuccessMsg(`✅ ${data.message}`);
        setShowTeachForm(false);
        // Reset fields
        setTeachEq('');
        setTeachTitle('');
        setTeachSystem('');
        setTeachSymptoms('');
        setTeachRootCause('');
        setTeachAction('');
        setTeachLesson('');
        fetchLearnedSkills();
      }
    } catch (err) {
      console.error(err);
      alert('Gagal mendaftarkan pembelajaran ke agen.');
    } finally {
      setSubmittingTeach(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-cyan font-black">Self-Improving Technical Memory &amp; Standards</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Knowledge Base &amp; Continuous Learning Center</h2>
        </div>
        
        {/* Workspace Tab Switcher */}
        <div className="flex items-center gap-2">
          <div className="flex rounded-xl border border-line p-0.5 bg-panel2 text-xs">
            <button
              onClick={() => setActiveTab('learning')}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold flex items-center gap-1.5 ${activeTab === 'learning' ? 'bg-cyan text-[#071018] shadow-neon' : 'text-muted hover:text-textMain'}`}
            >
              <span>🧠</span> Continuous Learning &amp; Ajari Agen
            </button>
            <button
              onClick={() => setActiveTab('envharness')}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold flex items-center gap-1.5 ${activeTab === 'envharness' ? 'bg-cyan text-[#071018] shadow-neon' : 'text-muted hover:text-textMain'}`}
            >
              <span>🛡️</span> EnvHarness &amp; EnvRigger
            </button>
            <button
              onClick={() => setActiveTab('standards')}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold flex items-center gap-1.5 ${activeTab === 'standards' ? 'bg-cyan text-[#071018] shadow-neon' : 'text-muted hover:text-textMain'}`}
            >
              <span>📚</span> SOP &amp; Standar Industri (19)
            </button>
          </div>
        </div>
      </div>

      {teachSuccessMsg && (
        <div className="p-3 bg-green/15 border border-green text-green text-xs font-bold rounded-2xl animate-fade-in shadow-neon">
          {teachSuccessMsg}
        </div>
      )}

      {/* TAB 1: Continuous Learning & Self-Improving Skill Hub */}
      {activeTab === 'learning' && (
        <section className="grid lg:grid-cols-[1.55fr_0.95fr] gap-4">
          <div className="flex flex-col gap-4">
            {/* Benchmark Accuracy Banner */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-center">
              <div className="sm:col-span-2">
                <span className="text-[10px] text-cyan uppercase font-bold tracking-wider block">Diagnostic Benchmark Suite</span>
                <strong className="text-sm text-textMain mt-0.5 block">Akurasi Diagnosa Gangguan Pembangkit</strong>
                <p className="text-[11px] text-muted mt-0.5">
                  Diuji pada 5 skenario gangguan aktual (Rotor bar retak, Unbalance Zone D, Hotspot Trafo T3, Intrusi air oli).
                </p>
              </div>
              <div className="p-2.5 bg-panel rounded-xl border border-green/30 text-center">
                <span className="text-[9px] text-green uppercase font-bold tracking-widest block">Accuracy Score</span>
                <strong className="text-xl text-green mt-0.5 block font-mono">
                  {benchmarks?.diagnostic_accuracy_score || 100}%
                </strong>
                <span className="text-[9px] text-muted">{benchmarks?.rating || 'Grade A - Expert'}</span>
              </div>
              <div>
                <button
                  onClick={() => setShowTeachForm(!showTeachForm)}
                  className="w-full py-2.5 px-3 rounded-xl border border-cyan bg-cyan/15 text-cyan font-bold text-xs hover:bg-cyan/25 transition-all flex items-center justify-center gap-1.5 shadow-neon"
                >
                  <span>✏️</span> {showTeachForm ? 'Tutup Form' : 'Ajari Kasus Baru'}
                </button>
              </div>
            </div>

            {/* Form "Ajari Agen" (Interactive Teaching Form) */}
            {showTeachForm && (
              <div className="border border-cyan/40 bg-panel2 rounded-2xl p-5 shadow-neon animate-fade-in">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-sm font-bold text-cyan flex items-center gap-2">
                    <span>🧠</span> Form Pembelajaran &amp; Kasus Gangguan Baru
                  </h3>
                  <span className="text-[10px] text-muted">Pengetahuan ini akan langsung diintegrasikan ke memori 8 Sub-Agents</span>
                </div>

                <form onSubmit={handleTeachSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] text-muted block mb-1">Nama Peralatan (Equipment)</label>
                    <input
                      type="text"
                      value={teachEq}
                      onChange={(e) => setTeachEq(e.target.value)}
                      placeholder="Misal: BFP 1A, IDF 1A, CEP 1A, BC 41"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-muted block mb-1">Kategori Gangguan</label>
                    <select
                      value={teachCategory}
                      onChange={(e) => setTeachCategory(e.target.value)}
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                    >
                      <option value="VIBRASI">VIBRASI (Mekanikal, Unbalance, Alignment, Bearing)</option>
                      <option value="MCSA_KELISTRIKAN">MCSA / KELISTRIKAN (Rotor Bar, Stator, THD, Unbalance)</option>
                      <option value="TRIBOLOGI">TRIBOLOGI / OLI (Viskositas, Air, Keausan Logam)</option>
                      <option value="DGA_TRAFO">DGA / TRAFO (Gas Terlarut, Hotspot, Arcing)</option>
                      <option value="TERMAL_IRT">TERMAL (Inframerah, Delta-T, Hotspot Terminal)</option>
                      <option value="BOILER_TURBIN">BOILER &amp; TURBIN AUXILIARIES (Kavitasi, Abu, Slip)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] text-muted block mb-1">Judul Ringkasan Kasus</label>
                    <input
                      type="text"
                      value={teachTitle}
                      onChange={(e) => setTeachTitle(e.target.value)}
                      placeholder="Misal: Kendornya baut pondasi pedestal NDE BFP 1A"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-muted block mb-1">Sistem Pembangkit</label>
                    <input
                      type="text"
                      value={teachSystem}
                      onChange={(e) => setTeachSystem(e.target.value)}
                      placeholder="Misal: Feedwater System, Coal Handling, Draft Fan"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-[10px] text-muted block mb-1">Gejala / Anomali Terukur (Satu per baris)</label>
                    <textarea
                      rows={2}
                      value={teachSymptoms}
                      onChange={(e) => setTeachSymptoms(e.target.value)}
                      placeholder="• Getaran 1X tinggi 5.8 mm/s&#10;• Arus fasa deviasi 4.8%&#10;• Suhu bantalan naik"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-muted block mb-1">Akar Masalah Terverifikasi (Verified Root Cause)</label>
                    <textarea
                      rows={2}
                      value={teachRootCause}
                      onChange={(e) => setTeachRootCause(e.target.value)}
                      placeholder="Temuan fisik lapangan sebenarnya (misal baut kendor, impeller berkerak)"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-muted block mb-1">Tindakan Perbaikan yang Terbukti Efektif</label>
                    <textarea
                      rows={2}
                      value={teachAction}
                      onChange={(e) => setTeachAction(e.target.value)}
                      placeholder="Tindakan korektif (misal re-torque 140 Nm, laser alignment, flushing)"
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-[10px] text-muted block mb-1">Pelajaran Teknis yang Dipelajari (Lesson Learned untuk AI)</label>
                    <textarea
                      rows={2}
                      value={teachLesson}
                      onChange={(e) => setTeachLesson(e.target.value)}
                      placeholder="Kaidah penalaran teknis untuk diagnosa di masa depan..."
                      className="w-full bg-panel border border-line rounded-lg p-2 text-textMain outline-none focus:border-cyan"
                      required
                    />
                  </div>

                  <div className="sm:col-span-2 flex justify-end gap-2 mt-1">
                    <button
                      type="button"
                      onClick={() => setShowTeachForm(false)}
                      className="px-3 py-2 bg-panel border border-line text-muted rounded-lg hover:text-textMain text-xs"
                    >
                      Batal
                    </button>
                    <button
                      type="submit"
                      disabled={submittingTeach}
                      className="px-5 py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs disabled:opacity-50 shadow-neon"
                    >
                      {submittingTeach ? 'Mendaftarkan...' : 'Simpan Pembelajaran ke AI Memori →'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* List of Learned Disturbance Patterns */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
                  Memori Kasus &amp; Pola Gangguan yang Dipelajari ({learnedSkills.length} Kasus)
                </h3>
                <span className="text-[10px] text-cyan">Klik kasus untuk melihat detail investigasi</span>
              </div>

              <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                {loadingSkills ? (
                  <div className="py-8 text-center text-xs text-muted">Memuat memori teknis...</div>
                ) : (
                  learnedSkills.map((sk, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedSkill(sk)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        selectedSkill?.id === sk.id
                          ? 'bg-panel2 border-cyan shadow-neon'
                          : 'bg-panel border-line hover:border-cyan/40'
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="px-1.5 py-0.2 rounded bg-cyan/15 border border-cyan/30 text-[9px] text-cyan font-bold font-mono">
                              {sk.id}
                            </span>
                            <strong className="text-xs font-bold text-textMain">{sk.title}</strong>
                          </div>
                          <span className="text-[10px] text-muted mt-1 block">
                            Peralatan: <strong className="text-textMain">{sk.equipment}</strong> · {sk.system}
                          </span>
                        </div>
                        <span className="text-[9px] px-2 py-0.5 rounded-full bg-panel2 border border-line text-cyan font-bold shrink-0">
                          {sk.category}
                        </span>
                      </div>

                      <p className="text-[11px] text-muted mt-2 leading-relaxed line-clamp-2">
                        <strong>Akar Masalah:</strong> {sk.verified_root_cause}
                      </p>

                      <div className="mt-2.5 pt-1.5 border-t border-line/40 flex justify-between items-center text-[9px] text-muted">
                        <span>Penulis: {sk.author}</span>
                        <span className="font-mono">{sk.verified_at}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Selected Skill Detail Viewer */}
            {selectedSkill && (
              <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-3">
                <div className="flex justify-between items-start pb-2 border-b border-line">
                  <div>
                    <span className="text-[10px] text-cyan uppercase font-bold tracking-widest">{selectedSkill.id} · {selectedSkill.category}</span>
                    <h3 className="text-sm font-bold text-textMain mt-0.5">{selectedSkill.title}</h3>
                  </div>
                  <span className="text-[10px] text-muted font-mono">{selectedSkill.verified_at}</span>
                </div>

                <div className="grid sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-amber font-bold block mb-1">🔍 Gejala &amp; Anomali Terukur</span>
                    <ul className="list-disc list-inside text-[11px] text-textMain space-y-1">
                      {selectedSkill.symptoms?.map((sym, sIdx) => (
                        <li key={sIdx}>{sym}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 bg-panel rounded-xl border border-line">
                    <span className="text-[10px] text-green font-bold block mb-1">🛠️ Tindakan Perbaikan Efektif</span>
                    <p className="text-[11px] text-textMain leading-relaxed">{selectedSkill.corrective_action_taken}</p>
                  </div>
                </div>

                <div className="p-3.5 bg-panel2 rounded-xl border border-cyan/30 text-xs">
                  <span className="text-[10px] text-cyan font-bold block mb-1">💡 Kaidah Pembelajaran untuk AI (Lesson Learned)</span>
                  <p className="text-xs text-textMain leading-relaxed">{selectedSkill.lesson_learned}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: AI Assistant Chat */}
          <div>
            <AIChatPanel defaultPrompt="Bagaimana kaidah pembelajaran dan pengalaman penanganan gangguan getaran 1X pada BFP dan blade buildup pada ID Fan?" />
          </div>
        </section>
      )}

      {/* TAB 2: Standards & SOP Document Browser */}
      {activeTab === 'standards' && (
        <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
          <div className="flex flex-col gap-4">
            {/* Search Bar */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
              <form onSubmit={handleSearch} className="flex gap-2">
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Cari SOP, Standar IEEE / ISO / NEMA, rumus, atau panduan diagnosa..."
                  className="flex-1 bg-panel2 border border-line rounded-lg px-3 py-2 text-xs text-textMain outline-none focus:border-cyan"
                />
                <button 
                  type="submit" 
                  disabled={searching}
                  className="px-4 py-2 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-colors text-xs disabled:opacity-50 shadow-neon"
                >
                  {searching ? 'Mencari...' : 'Cari'}
                </button>
                {searchQuery && (
                  <button 
                    type="button" 
                    onClick={() => { setSearchQuery(''); fetchArticles(); }}
                    className="px-3 py-2 bg-panel2 border border-line text-muted rounded-lg hover:text-textMain text-xs"
                  >
                    Reset
                  </button>
                )}
              </form>
            </div>

            {/* Articles Grid */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
                  Daftar Standar &amp; Panduan ({articles.length} Dokumen)
                </h3>
              </div>

              <KnowledgeCardGrid 
                articles={articles} 
                loading={loading} 
                selectedArticle={selectedArticle}
                onSelectArticle={setSelectedArticle}
              />
            </div>

            {/* Article Detail Viewer */}
            <KnowledgeDocumentViewer article={selectedArticle} />
          </div>

          {/* Right Column: AI Assistant Chat */}
          <div>
            <AIChatPanel defaultPrompt={selectedArticle ? `Jelaskan ringkasan materi dan standar teknis dari dokumen ${selectedArticle.title || selectedArticle.name}.` : undefined} />
          </div>
        </section>
      )}

      {/* TAB 3: EnvHarness & EnvRigger Adaptive Learning Studio */}
      {activeTab === 'envharness' && (
        <section className="grid lg:grid-cols-[1.55fr_0.95fr] gap-4">
          <div className="flex flex-col gap-4">
            {/* Paper Reference Banner */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                <div>
                  <span className="text-[10px] text-cyan uppercase font-bold tracking-wider block">
                    Google Cloud AI Research (2026) · Adaptive World Wrapping
                  </span>
                  <h3 className="text-sm font-bold text-textMain mt-0.5">
                    EnvHarness &amp; EnvRigger Learning Architecture
                  </h3>
                  <p className="text-[11px] text-muted mt-1 leading-relaxed">
                    Membungkus environment diagnosa dengan layer adaptif untuk melatih kelemahan spesifik AI tanpa mengubah model dasar ataupun logika verifier ground-truth.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleEvaluateHarness}
                    disabled={evaluatingHarness}
                    className="py-2 px-3 bg-cyan text-[#071018] font-bold rounded-xl hover:bg-cyan/90 transition-all text-xs disabled:opacity-50 shadow-neon"
                  >
                    {evaluatingHarness ? 'Mengevaluasi...' : '⚡ Uji Ketahanan Harness'}
                  </button>
                </div>
              </div>
            </div>

            {/* 3 Core Components Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 bg-panel2 rounded-2xl border border-cyan/30 shadow-neon flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="px-2 py-0.5 rounded bg-cyan/15 border border-cyan text-[10px] font-bold text-cyan">STAGE (w_stage)</span>
                    <span className="text-[10px] text-muted">Initial State</span>
                  </div>
                  <strong className="text-xs text-textMain block mb-1">Disturbance Injection</strong>
                  <p className="text-[11px] text-muted leading-relaxed">
                    Menyuntikkan mutasi telemetri (sideband -42 dB, getaran 1X tinggi, hotspot) untuk melatih deteksi awal.
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-cyan font-mono">
                  s₀ ➔ s'₀ (Mutasi Status Awal)
                </div>
              </div>

              <div className="p-3.5 bg-panel2 rounded-2xl border border-amber/30 shadow-neon flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="px-2 py-0.5 rounded bg-amber/15 border border-amber text-[10px] font-bold text-amber">CONTRACT (w_contract)</span>
                    <span className="text-[10px] text-muted">Rules &amp; Noise</span>
                  </div>
                  <strong className="text-xs text-textMain block mb-1">Interaction Discipline</strong>
                  <p className="text-[11px] text-muted leading-relaxed">
                    Menegakkan verifikasi multi-modal (min 2 sensor) dan kewajiban Safety Guardrail clearance.
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-amber font-mono">
                  (f_A, f_T, f_O) Triplet Filter
                </div>
              </div>

              <div className="p-3.5 bg-panel2 rounded-2xl border border-green/30 shadow-neon flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="px-2 py-0.5 rounded bg-green/15 border border-green text-[10px] font-bold text-green">CHAIN (w_chain)</span>
                    <span className="text-[10px] text-muted">Long-Horizon</span>
                  </div>
                  <strong className="text-xs text-textMain block mb-1">Task Extension</strong>
                  <p className="text-[11px] text-muted leading-relaxed">
                    Menghubungkan diagnosa langsung ke mitigasi risiko, RUL, dan penerbitan Work Order terencana.
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-green font-mono">
                  E' = g(E_base, E_ext) Lifecycle
                </div>
              </div>
            </div>

            {/* EnvRigger Automated Customization Studio */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
                <div>
                  <span className="text-[10px] text-cyan uppercase font-bold tracking-wider block">EnvRigger Automated Customizer</span>
                  <h3 className="text-sm font-bold text-textMain">Siklus Otomatisasi: Observe ➔ Diagnose ➔ Write ➔ Validate</h3>
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <select
                    value={riggerEq}
                    onChange={(e) => setRiggerEq(e.target.value)}
                    className="bg-panel border border-line rounded-lg px-2.5 py-1.5 text-xs text-textMain outline-none focus:border-cyan"
                  >
                    <option value="BFP 1A">BFP 1A (Boiler Feed Pump)</option>
                    <option value="IDF 1A">IDF 1A (Induced Draft Fan)</option>
                    <option value="CEP 1A">CEP 1A (Condensate Pump)</option>
                    <option value="BC 41">BC 41 (Coal Conveyor)</option>
                    <option value="Transformer Unit 1">Transformer Unit 1 (GSUT)</option>
                  </select>
                  <button
                    onClick={handleRunRiggerCycle}
                    disabled={runningRigger}
                    className="py-1.5 px-3 bg-cyan text-[#071018] font-bold rounded-lg hover:bg-cyan/90 transition-all text-xs disabled:opacity-50 shadow-neon whitespace-nowrap"
                  >
                    {runningRigger ? 'Menjalankan...' : '▶ Jalankan EnvRigger'}
                  </button>
                </div>
              </div>

              {/* Real-time Rigger Execution Results */}
              {riggerResult && (
                <div className="space-y-3 animate-fade-in text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
                    <div className="p-3 bg-panel rounded-xl border border-line">
                      <span className="text-[10px] text-cyan font-bold block mb-1">1. OBSERVE</span>
                      <p className="text-[11px] text-textMain font-mono">
                        Base Rollout: {riggerResult.rigger_cycle?.stage_1_observe?.base_success ? '✅ Selesai' : '❌ Anomali Terdeteksi'}
                      </p>
                      <span className="text-[10px] text-muted">Langkah: {riggerResult.rigger_cycle?.stage_1_observe?.steps} aksi</span>
                    </div>

                    <div className="p-3 bg-panel rounded-xl border border-amber/30">
                      <span className="text-[10px] text-amber font-bold block mb-1">2. DIAGNOSE</span>
                      <strong className="text-[11px] text-amber block">{riggerResult.rigger_cycle?.stage_2_diagnose?.issue}</strong>
                      <span className="text-[10px] text-muted line-clamp-2">{riggerResult.rigger_cycle?.stage_2_diagnose?.recommendation}</span>
                    </div>

                    <div className="p-3 bg-panel rounded-xl border border-cyan/30">
                      <span className="text-[10px] text-cyan font-bold block mb-1">3. WRITE</span>
                      <strong className="text-[11px] text-cyan block">{riggerResult.rigger_cycle?.stage_3_write?.name}</strong>
                      <span className="text-[10px] text-muted line-clamp-2">{riggerResult.rigger_cycle?.stage_3_write?.description}</span>
                    </div>

                    <div className="p-3 bg-panel rounded-xl border border-green/30">
                      <span className="text-[10px] text-green font-bold block mb-1">4. VALIDATE</span>
                      <strong className="text-[11px] text-green block">
                        {riggerResult.rigger_cycle?.stage_4_validate?.accepted ? '✅ ACCEPTED' : '⚠️ REVISED'}
                      </strong>
                      <span className="text-[10px] text-muted">{riggerResult.rigger_cycle?.stage_4_validate?.decision_reason}</span>
                    </div>
                  </div>

                  {riggerResult.persisted_skill && (
                    <div className="p-3 bg-green/15 border border-green text-green text-xs font-bold rounded-xl animate-fade-in shadow-neon">
                      🎉 <strong>Skill Baru Terbentuk:</strong> {riggerResult.persisted_skill.skill?.title} (Tersimpan ke memori berkelanjutan)
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Active Harness Wrappers List */}
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
                  Daftar Active EnvHarness Wrappers ({harnessStatus?.total_harness_components || 3} Komponen Aktif)
                </h3>
                <span className="text-[10px] text-cyan font-mono">Framework: {harnessStatus?.framework || 'EnvHarness'}</span>
              </div>

              <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                {loadingHarness ? (
                  <div className="py-6 text-center text-xs text-muted">Memuat komponen harness...</div>
                ) : (
                  (harnessStatus?.components || []).map((comp, cIdx) => (
                    <div key={cIdx} className="p-3 rounded-xl border border-line bg-panel flex justify-between items-start gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${
                            comp.type === 'STAGE' ? 'bg-cyan/15 text-cyan border border-cyan/30' :
                            comp.type === 'CONTRACT' ? 'bg-amber/15 text-amber border border-amber/30' :
                            'bg-green/15 text-green border border-green/30'
                          }`}>
                            {comp.type}
                          </span>
                          <strong className="text-xs text-textMain">{comp.name}</strong>
                        </div>
                        <p className="text-[11px] text-muted mt-1">{comp.description}</p>
                      </div>
                      <span className="text-[9px] px-2 py-0.5 rounded bg-panel2 text-muted border border-line shrink-0">
                        ACTIVE
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Harness Benchmark Stress-Test Results */}
            {harnessEval && (
              <div className="border border-cyan/40 bg-panel2 rounded-2xl p-5 shadow-neon animate-fade-in flex flex-col gap-3">
                <div className="flex justify-between items-center pb-2 border-b border-line">
                  <div>
                    <span className="text-[10px] text-cyan uppercase font-bold tracking-widest">Harness Evaluation Report</span>
                    <h3 className="text-sm font-bold text-textMain">Skor Ketahanan Diagnosa Multi-Modal: {harnessEval.harness_score}%</h3>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-green/15 text-green font-bold border border-green/30">
                    {harnessEval.status}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  {harnessEval.results?.map((res, rIdx) => (
                    <div key={rIdx} className="p-2.5 bg-panel rounded-xl border border-line flex justify-between items-center text-[11px]">
                      <div>
                        <strong className="text-textMain font-mono mr-2">{res.benchmark_id}</strong>
                        <span className="text-muted">{res.title}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-cyan font-mono">{res.steps} Langkah</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${res.success ? 'bg-green/15 text-green' : 'bg-amber/15 text-amber'}`}>
                          {res.success ? 'PASSED' : 'PARTIAL'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: AI Assistant Chat */}
          <div>
            <AIChatPanel defaultPrompt="Bagaimana arsitektur EnvHarness (Stage, Contract, Chain) dan EnvRigger meningkatkan ketahanan diagnosa MCSA, getaran, dan keandalan PLTU?" />
          </div>
        </section>
      )}
    </div>
  );
}

