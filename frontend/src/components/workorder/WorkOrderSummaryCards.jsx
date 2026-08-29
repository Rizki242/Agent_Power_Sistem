import React from 'react';
import { KPICard } from '../common';

export default function WorkOrderSummaryCards({ workOrders = [] }) {
  const total = workOrders.length;
  const critical = workOrders.filter(w => (w.priority || '').toUpperCase().includes('P1') || (w.priority || '').toUpperCase().includes('CRITICAL')).length;
  const high = workOrders.filter(w => (w.priority || '').toUpperCase().includes('P2') || (w.priority || '').toUpperCase().includes('HIGH')).length;
  const pending = workOrders.filter(w => (w.status || '').toUpperCase().includes('PENDING')).length;
  const approved = workOrders.filter(w => (w.status || '').toUpperCase().includes('APPROVED') || (w.status || '').toUpperCase().includes('IN-PROGRESS')).length;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-2.5">
      <KPICard
        label="Total Work Orders"
        value={`${total} WO`}
        subtext="CMMS Pipeline"
        color="cyan"
        icon="📋"
      />
      <KPICard
        label="P1 - Critical"
        value={critical}
        subtext="Eksekusi Segera"
        color="red"
        icon="🚨"
        alert={critical > 0}
      />
      <KPICard
        label="P2 - High Priority"
        value={high}
        subtext="Dalam 24-48 Jam"
        color="amber"
        icon="⚠️"
        alert={high > 0}
      />
      <KPICard
        label="Pending Otorisasi"
        value={pending}
        subtext="Perlu Tanda Tangan"
        color="yellow"
        icon="✍️"
      />
      <KPICard
        label="Approved / Active"
        value={approved}
        subtext="Dispatched to Field"
        color="green"
        icon="✅"
      />
    </div>
  );
}
