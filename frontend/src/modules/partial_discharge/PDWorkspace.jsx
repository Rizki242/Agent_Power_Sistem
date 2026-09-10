import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AIChatPanel from '../../components/AIChatPanel';
import {
  StatusBadge,
  FilterBar,
  TabNavigation,
  DataDisclaimerBanner,
} from '../../components/common';
import {
  PDSummaryCards,
  PDSampleList,
  PDParameterGrid,
  PDAssessmentPanel,
} from './components';
import { apiFetch, apiUrl } from '../../api';

// Selected sample is driven by the route (/workspace/partial_discharge/:equipmentId),
// same redesign as the other five workspaces (desaindakhir.md / docs/final.md
// Phase 25). The disclaimer banner is mandatory here: PD has no real source
// data, see src/pd_data.py's module docstring.
export default function PDWorkspace() {
  const { equipmentId } = useParams();
  const navigate = useNavigate();
  const selectedSampleId = equipmentId ? decodeURIComponent(equipmentId) : null;

  // --- Sample List State ---
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [unitFilter, setUnitFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [summary, setSummary] = useState(null);

  // --- Sample Detail State ---
  const [sampleDetail, setSampleDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [assessment, setAssessment] = useState(null);
  const [loadingAssessment, setLoadingAssessment] = useState(false);
  const [activeTab, setActiveTab] = useState('params'); // 'params' | 'assessment'

  // Navigating (not just setting local state) keeps the sidebar tree's
  // NavLink highlighting and the breadcrumb in sync with selection.
  const goToSample = useCallback((id, opts) => {
    navigate(`/workspace/partial_discharge/${encodeURIComponent(id)}`, opts);
  }, [navigate]);

  useEffect(() => {
    if (!selectedSampleId) {
      setSampleDetail(null);
      setAssessment(null);
      return;
    }
    setLoadingDetail(true);
    apiFetch(apiUrl(`/api/pd/samples/${encodeURIComponent(selectedSampleId)}`))
      .then(res => res.json())
      .then(data => {
        setSampleDetail(data);
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error('Gagal memuat detail sampel PD:', err);
        setLoadingDetail(false);
      });
  }, [selectedSampleId]);

  // PDAgent runs server-side; only fetch it when the tab is actually opened.
  useEffect(() => {
    if (!selectedSampleId || activeTab !== 'assessment') return;
    setLoadingAssessment(true);
    apiFetch(apiUrl(`/api/pd/samples/${encodeURIComponent(selectedSampleId)}/assessment`))
      .then(res => res.json())
      .then(data => {
        setAssessment(data);
        setLoadingAssessment(false);
      })
      .catch(err => {
        console.error('Gagal memuat analisa PD Agent:', err);
        setLoadingAssessment(false);
      });
  }, [selectedSampleId, activeTab]);

  // --- Fetch Samples ---
  const fetchSamples = useCallback(() => {
    setLoading(true);
    let url = apiUrl('/api/pd/samples?');
    if (unitFilter !== 'ALL') url += `unit=${encodeURIComponent(unitFilter)}&`;
    if (statusFilter !== 'ALL') url += `status=${encodeURIComponent(statusFilter)}&`;
    if (search.trim()) url += `search=${encodeURIComponent(search.trim())}&`;

    apiFetch(url)
      .then(res => res.json())
      .then(data => {
        setSamples(data.samples || []);
        setLoading(false);
        if (!selectedSampleId && data.samples && data.samples.length > 0) {
          goToSample(data.samples[0].sample_id, { replace: true });
        }
      })
      .catch(err => {
        console.error('Gagal mengambil data sampel PD:', err);
        setLoading(false);
      });
  }, [unitFilter, statusFilter, search, selectedSampleId, goToSample]);

  // --- Fetch Summary ---
  useEffect(() => {
    apiFetch(apiUrl('/api/pd/summary'))
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchSamples();
  }, [fetchSamples]);

  const pdTabs = [
    { id: 'params', label: 'Parameter PRPD', icon: '📊' },
    { id: 'assessment', label: 'Rekomendasi', icon: '🤖' },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Mandatory: PD data is illustrative, not measured */}
      <DataDisclaimerBanner />

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-purple-400 font-bold">Insulation Condition Monitoring</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Partial Discharge Workspace</h2>
        </div>
        <div className="text-xs text-muted">IEC 60270 · IEEE 1434 · CIGRE WG D1.33</div>
      </div>

      {/* Summary Cards */}
      <PDSummaryCards summary={summary} />

      {/* Main Layout */}
      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column: Filter + List + Detail */}
        <div className="flex flex-col gap-4">
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            onSearchSubmit={fetchSamples}
            searchPlaceholder="Cari Peralatan / Sample ID PD..."
            unitFilter={unitFilter}
            onUnitChange={setUnitFilter}
            unitOptions={['ALL', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON']}
            statusFilter={statusFilter}
            onStatusChange={setStatusFilter}
            statusOptions={['ALL', 'NORMAL', 'PREWARNING', 'WARNING', 'HIGH']}
            accentColor="purple"
          />

          <PDSampleList
            samples={samples}
            loading={loading}
            selectedSampleId={selectedSampleId}
            onSelect={goToSample}
          />

          {/* Sample Detail Card */}
          {selectedSampleId && (
            <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 pb-3 border-b border-line">
                <div>
                  <span className="text-[10px] text-purple-400 uppercase tracking-wider font-bold">Hasil Pengukuran Partial Discharge</span>
                  <h3 className="text-lg font-bold text-textMain mt-0.5">
                    {sampleDetail?.equipment || selectedSampleId}
                    <span className="text-xs text-muted font-normal ml-2">
                      ({sampleDetail?.unit} · {sampleDetail?.method})
                    </span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <TabNavigation
                    tabs={pdTabs}
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                    accentColor="purple"
                  />
                  <StatusBadge status={sampleDetail?.status} size="lg" />
                </div>
              </div>

              {loadingDetail ? (
                <div className="py-8 text-center text-muted text-xs">Memuat detail pengukuran PD...</div>
              ) : sampleDetail ? (
                <div className="flex flex-col gap-4">
                  {activeTab === 'params' && (
                    <PDParameterGrid sampleDetail={sampleDetail} />
                  )}
                  {activeTab === 'assessment' && (
                    <PDAssessmentPanel assessment={assessment} loading={loadingAssessment} />
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel
            defaultPrompt={sampleDetail
              ? `Bagaimana evaluasi partial discharge untuk ${sampleDetail.equipment}? Jelaskan magnitudo pulsa, NQN, dan tipe discharge-nya.`
              : undefined}
          />
        </div>
      </section>
    </div>
  );
}
