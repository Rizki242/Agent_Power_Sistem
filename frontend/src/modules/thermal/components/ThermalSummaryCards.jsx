import React from 'react';
import { KPICard } from '../../../components/common';

export default function ThermalSummaryCards({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Titik IRT"
        value={`${summary.total_inspections || 0} Titik`}
        subtext="Infrared Thermography"
        color="orange"
        icon="🌡️"
      />
      <KPICard
        label="Normal (Low ΔT)"
        value={summary.by_status?.NORMAL || 0}
        subtext="ΔT ≤ 3°C"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Prewarning (Medium)"
        value={summary.by_status?.PREWARNING || 0}
        subtext="ΔT: 4 - 10°C"
        color="yellow"
        icon="🟡"
        alert={(summary.by_status?.PREWARNING || 0) > 0}
      />
      <KPICard
        label="Warning / High"
        value={summary.by_status?.WARNING || summary.by_status?.HIGH || 0}
        subtext="ΔT: 11 - 20°C"
        color="amber"
        icon="🟠"
        alert={(summary.by_status?.WARNING || summary.by_status?.HIGH || 0) > 0}
      />
      <KPICard
        label="Critical (Alarm)"
        value={summary.by_status?.CRITICAL || summary.by_status?.ALARM || 0}
        subtext="ΔT > 20°C Hotspot"
        color="red"
        icon="🔴"
        alert={(summary.by_status?.CRITICAL || summary.by_status?.ALARM || 0) > 0}
      />
    </div>
  );
}
