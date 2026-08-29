import React from 'react';

export default function FusionSummaryCards({ fleetData }) {
  const summary = fleetData?.health_summary || { HEALTHY: 0, WATCH: 0, WARNING: 0, ALERT: 0, CRITICAL: 0 };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-muted font-bold">Total Assets</span>
        <strong className="text-2xl text-textMain mt-1">{fleetData?.total_assets || 0}</strong>
        <span className="text-[10px] text-cyan">Monitored Drives</span>
      </div>

      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-muted font-bold">Fleet Health Index</span>
        <strong className="text-2xl text-cyan mt-1">{fleetData?.fleet_health_average || 90}/100</strong>
        <span className="text-[10px] text-green">Weighted Average</span>
      </div>

      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-green font-bold">Healthy (90-100)</span>
        <strong className="text-2xl text-green mt-1">{summary.HEALTHY || 0}</strong>
        <span className="text-[10px] text-muted">Optimal State</span>
      </div>

      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-blue font-bold">Watch (75-89)</span>
        <strong className="text-2xl text-blue mt-1">{summary.WATCH || 0}</strong>
        <span className="text-[10px] text-muted">Minor Deviation</span>
      </div>

      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-amber font-bold">Warning / Alert</span>
        <strong className="text-2xl text-amber mt-1">{(summary.WARNING || 0) + (summary.ALERT || 0)}</strong>
        <span className="text-[10px] text-muted">Action Suggested</span>
      </div>

      <div className="border border-line bg-card-gradient shadow-neon p-3.5 rounded-2xl flex flex-col justify-between">
        <span className="text-[10px] uppercase tracking-wider text-red font-bold">Critical (&lt;50)</span>
        <strong className="text-2xl text-red mt-1 animate-pulse">{summary.CRITICAL || 0}</strong>
        <span className="text-[10px] text-red">High Failure Risk</span>
      </div>
    </div>
  );
}
