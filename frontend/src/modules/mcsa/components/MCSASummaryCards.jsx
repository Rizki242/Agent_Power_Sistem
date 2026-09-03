import React from 'react';
import { KPICard } from '../../../components/common';

export default function MCSASummaryCards({ summary }) {
  if (!summary) return null;
  const counts = summary.counts || { Normal: 0, Alarm: 0, High: 0, Standby: 0 };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Motor MCSA"
        value={`${summary.total_equipment || 0} Unit`}
        subtext="PLTU Jeranjang"
        color="cyan"
        icon="⚡"
      />
      <KPICard
        label="Normal"
        value={counts.Normal || 0}
        subtext="Kondisi Sehat"
        color="green"
        icon="🟢"
      />
      <KPICard
        label="Alarm"
        value={counts.Alarm || 0}
        subtext="Investigasi Ringan"
        color="amber"
        icon="🟡"
        alert={counts.Alarm > 0}
      />
      <KPICard
        label="High (Critical)"
        value={counts.High || 0}
        subtext="Mitigasi Segera"
        color="red"
        icon="🔴"
        alert={counts.High > 0}
      />
      <KPICard
        label="Standby"
        value={counts.Standby || 0}
        subtext="Siap Pakai"
        color="muted"
        icon="⚪"
      />
    </div>
  );
}
