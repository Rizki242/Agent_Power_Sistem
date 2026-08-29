import React from 'react';

export default function StatusBadge({ status, size = 'sm', pulse = false }) {
  const s = String(status || '').toUpperCase().trim();

  let colorClasses = 'bg-muted/10 text-muted border-line';
  let label = status || 'UNKNOWN';

  if (s === 'NORMAL' || s === 'HEALTHY' || s === 'GOOD' || s === 'LOW' || s === 'ZONE A' || s === 'CONDITION 1') {
    colorClasses = 'bg-green/10 text-green border-green/30';
    label = s === 'HEALTHY' ? 'HEALTHY' : s === 'CONDITION 1' ? 'COND 1 (NORMAL)' : 'NORMAL';
  } else if (s === 'PREWARNING' || s === 'WATCH' || s === 'MEDIUM' || s === 'ZONE B' || s === 'CONDITION 2') {
    colorClasses = 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    label = s === 'WATCH' ? 'WATCH' : s === 'CONDITION 2' ? 'COND 2 (WARNING)' : 'PREWARNING';
  } else if (s === 'ALARM' || s === 'WARNING' || s === 'ALERT' || s === 'ZONE C' || s === 'CONDITION 3') {
    colorClasses = 'bg-amber/10 text-amber border-amber/30';
    label = s === 'ALERT' ? 'ALERT' : s === 'CONDITION 3' ? 'COND 3 (ALARM)' : (s === 'WARNING' ? 'WARNING' : 'ALARM');
  } else if (s === 'HIGH' || s === 'CRITICAL' || s === 'DANGER' || s === 'UNACCEPTABLE' || s === 'ZONE D' || s === 'CONDITION 4') {
    colorClasses = 'bg-red/10 text-red border-red/30';
    label = s === 'CRITICAL' ? 'CRITICAL' : s === 'CONDITION 4' ? 'COND 4 (CRITICAL)' : 'HIGH';
  } else if (s === 'STANDBY' || s === 'STD BY' || s === 'IDLE') {
    colorClasses = 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    label = 'STANDBY';
  }

  const sizeClasses = size === 'xs' 
    ? 'px-1.5 py-0.2 text-[9px]' 
    : size === 'lg' 
    ? 'px-3 py-1 text-xs' 
    : 'px-2 py-0.5 text-[10px] sm:text-[11px]';

  const shouldPulse = pulse || s === 'CRITICAL' || s === 'HIGH';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-bold border ${sizeClasses} ${colorClasses} ${shouldPulse ? 'animate-pulse' : ''}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80"></span>
      <span>{label}</span>
    </span>
  );
}
