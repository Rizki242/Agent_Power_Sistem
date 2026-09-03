import React from 'react';
import { KPICard } from '../../../components/common';

export default function TribologySummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Sampel Oli"
        value={`${summary.total_samples || 0} Titik`}
        subtext="Pelumas Turbin & Aux"
        color="cyan"
        icon="🧪"
      />
      <KPICard
        label="Normal (Good)"
        value={summary.by_status?.NORMAL || 0}
        subtext="Kondisi Oli Baik"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Prewarning"
        value={summary.by_status?.PREWARNING || 0}
        subtext="Aditif Terdegradasi"
        color="yellow"
        icon="🟡"
        alert={(summary.by_status?.PREWARNING || 0) > 0}
      />
      <KPICard
        label="Warning / Alarm"
        value={summary.by_status?.WARNING || summary.by_status?.ALARM || 0}
        subtext="Ganti / Purifikasi"
        color="amber"
        icon="🟠"
        alert={(summary.by_status?.WARNING || summary.by_status?.ALARM || 0) > 0}
      />
      <KPICard
        label="Critical (High Wear)"
        value={summary.by_status?.CRITICAL || summary.by_status?.HIGH || 0}
        subtext="Keausan Komponen"
        color="red"
        icon="🔴"
        alert={(summary.by_status?.CRITICAL || summary.by_status?.HIGH || 0) > 0}
      />
    </div>
  );
}
