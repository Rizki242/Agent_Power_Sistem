import React, { useState, useEffect } from 'react';
import AIChatPanel from '../components/AIChatPanel';
import { KPICard } from '../components/common';
import { HealthDistributionGauge, AssetHealthMatrix } from '../components/health';
import { apiUrl } from '../api';

export default function AssetHealth() {
  const [summary, setSummary] = useState(null);
  const [alarmList, setAlarmList] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(apiUrl('/api/summary')).then(res => res.json()),
      fetch(apiUrl('/api/equipment?status=Alarm')).then(res => res.json()),
      fetch(apiUrl('/api/equipment?status=High')).then(res => res.json())
    ])
      .then(([sumData, alarmData, highData]) => {
        setSummary(sumData);
        const combinedAlerts = [
          ...(highData.equipment || []),
          ...(alarmData.equipment || [])
        ];
        setAlarmList(combinedAlerts);
        setLoading(false);
      })
      .catch(err => {
        console.error('Gagal mengambil data asset health:', err);
        setLoading(false);
      });
  }, []);

  const counts = summary?.counts || summary?.status_counts || { Normal: 0, Alarm: 0, High: 0, Standby: 0 };
  const total = summary?.total_equipment || 1;
  const normalCount = counts.Normal || 0;
  const alarmCount = counts.Alarm || 0;
  const highCount = counts.High || 0;
  const standbyCount = counts.Standby || 0;
  const healthPercent = Math.round((normalCount / total) * 100) || 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-green font-bold">Fleet Reliability Index</div>
          <h2 className="text-xl font-bold text-textMain mt-0.5">Asset Health Matrix</h2>
        </div>
        <div className="text-xs text-muted">
          PLTU Jeranjang · 3 × 25 MW
        </div>
      </div>

      <section className="grid lg:grid-cols-[1.6fr_0.9fr] gap-4">
        {/* Left Column: Health Overview & Watchlist */}
        <div className="flex flex-col gap-4">
          {/* Status Breakdown Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KPICard
              label="Normal Assets"
              value={loading ? '...' : normalCount}
              subtext={loading ? '-' : `${Math.round((normalCount/total)*100)}% of total`}
              color="green"
              icon="🟢"
            />
            <KPICard
              label="Alarm / Warning"
              value={loading ? '...' : alarmCount}
              subtext="Perlu investigasi"
              color="amber"
              icon="🟡"
              alert={alarmCount > 0}
            />
            <KPICard
              label="High / Critical"
              value={loading ? '...' : highCount}
              subtext="Mitigasi segera"
              color="red"
              icon="🔴"
              alert={highCount > 0}
            />
            <KPICard
              label="Standby"
              value={loading ? '...' : standbyCount}
              subtext="Cadangan siap pakai"
              color="muted"
              icon="⚪"
            />
          </div>

          {/* Plant Reliability Gauge & Health Score */}
          <HealthDistributionGauge
            healthPercent={healthPercent}
            loading={loading}
            normalCount={normalCount}
            alarmCount={alarmCount}
            highCount={highCount}
            total={total}
          />

          {/* Equipment Watchlist Table */}
          <AssetHealthMatrix
            alarmList={alarmList}
            loading={loading}
          />
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div>
          <AIChatPanel defaultPrompt="Berikan ringkasan executive summary untuk kesehatan peralatan PLTU Jeranjang dan daftar 5 peralatan dengan risiko kegagalan tertinggi." />
        </div>
      </section>
    </div>
  );
}
