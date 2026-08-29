import React from 'react';
import { KPICard } from '../common';

export default function VibrationSummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Asset Vibrasi"
        value={`${summary.total_assets || 0} Tag`}
        subtext="Peralatan Berputar"
        color="cyan"
        icon="📊"
      />
      <KPICard
        label="Total Pengujian"
        value={`${summary.total_reports || 0} Record`}
        subtext="Trend Bulanan"
        color="blue"
        icon="📈"
      />
      <KPICard
        label="Normal (Zone A/B)"
        value={summary.by_status?.NORMAL || summary.by_status?.GOOD || 0}
        subtext="≤ 2.8 - 4.5 mm/s"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Alarm (Zone C)"
        value={summary.by_status?.ALARM || summary.by_status?.WARNING || 0}
        subtext="4.5 - 7.1 mm/s"
        color="amber"
        icon="🟡"
        alert={(summary.by_status?.ALARM || summary.by_status?.WARNING || 0) > 0}
      />
      <KPICard
        label="High (Zone D)"
        value={summary.by_status?.HIGH || summary.by_status?.CRITICAL || 0}
        subtext="> 7.1 mm/s RMS"
        color="red"
        icon="🔴"
        alert={(summary.by_status?.HIGH || summary.by_status?.CRITICAL || 0) > 0}
      />
    </div>
  );
}
