import React from 'react';
import { KPICard } from '../common';

export default function DGASummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Transformator"
        value={`${summary.total_transformers || 0} Unit`}
        subtext="GSU & UAT Transformers"
        color="cyan"
        icon="⚡"
      />
      <KPICard
        label="Condition 1 (Normal)"
        value={summary.by_status?.['Condition 1'] || summary.by_status?.NORMAL || 0}
        subtext="TDCG ≤ 720 ppm"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Condition 2 (Warning)"
        value={summary.by_status?.['Condition 2'] || summary.by_status?.WARNING || 0}
        subtext="721 - 1920 ppm"
        color="yellow"
        icon="🟡"
        alert={(summary.by_status?.['Condition 2'] || summary.by_status?.WARNING || 0) > 0}
      />
      <KPICard
        label="Condition 3 (Alarm)"
        value={summary.by_status?.['Condition 3'] || summary.by_status?.ALARM || 0}
        subtext="1921 - 4630 ppm"
        color="amber"
        icon="🟠"
        alert={(summary.by_status?.['Condition 3'] || summary.by_status?.ALARM || 0) > 0}
      />
      <KPICard
        label="Condition 4 (Critical)"
        value={summary.by_status?.['Condition 4'] || summary.by_status?.CRITICAL || 0}
        subtext="> 4630 ppm TDCG"
        color="red"
        icon="🔴"
        alert={(summary.by_status?.['Condition 4'] || summary.by_status?.CRITICAL || 0) > 0}
      />
    </div>
  );
}
