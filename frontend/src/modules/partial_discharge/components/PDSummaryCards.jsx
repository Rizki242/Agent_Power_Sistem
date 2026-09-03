import React from 'react';
import { KPICard } from '../../../components/common';

// Thresholds shown as subtext are src/pd_data.py's _pd_status boundaries,
// which are themselves PDAgent.evaluate()'s - keep the two in step.
export default function PDSummaryCards({ summary }) {
  if (!summary) return null;

  const byStatus = summary.by_status || {};

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Sampel"
        value={`${summary.total_samples || 0} Titik`}
        subtext="PRPD / HFCT / UHF"
        color="purple"
        icon="⚡"
      />
      <KPICard
        label="Normal"
        value={byStatus.NORMAL || 0}
        subtext="< 250 pC"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Prewarning"
        value={byStatus.PREWARNING || 0}
        subtext="250 - 499 pC"
        color="yellow"
        icon="🟡"
        alert={(byStatus.PREWARNING || 0) > 0}
      />
      <KPICard
        label="Warning"
        value={byStatus.WARNING || 0}
        subtext="500 - 1499 pC"
        color="amber"
        icon="🟠"
        alert={(byStatus.WARNING || 0) > 0}
      />
      <KPICard
        label="High"
        value={byStatus.HIGH || 0}
        subtext="≥ 1500 pC atau NQN ≥ 100"
        color="red"
        icon="🔴"
        alert={(byStatus.HIGH || 0) > 0}
      />
    </div>
  );
}
