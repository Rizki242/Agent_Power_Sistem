import React from 'react';

export default function KPICard({ label, value, subtext, color = 'textMain', icon, alert = false }) {
  const colorMap = {
    textMain: 'text-textMain',
    cyan: 'text-cyan',
    green: 'text-green',
    amber: 'text-amber',
    red: 'text-red',
    blue: 'text-blue',
    yellow: 'text-yellow-400',
    purple: 'text-purple-400',
    muted: 'text-slate-400'
  };

  const borderClass = alert ? 'border-amber/40 bg-amber/5' : 'border-line bg-panel';
  const textColorClass = colorMap[color] || 'text-textMain';

  return (
    <div className={`border rounded-xl p-3 text-center transition-all hover:border-line/80 ${borderClass}`}>
      <div className="flex items-center justify-center gap-1.5 mb-1">
        {icon && <span className="text-xs">{icon}</span>}
        <span className="text-[10px] text-muted uppercase tracking-wider block font-semibold">{label}</span>
      </div>
      <strong className={`text-lg sm:text-xl font-bold block ${textColorClass}`}>{value}</strong>
      {subtext && <small className="text-[10px] text-muted block mt-0.5">{subtext}</small>}
    </div>
  );
}
