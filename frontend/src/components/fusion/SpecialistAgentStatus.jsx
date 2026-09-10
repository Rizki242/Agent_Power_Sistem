import React, { useState, useEffect } from 'react';
import { apiFetch, apiUrl } from '../../api';

export default function SpecialistAgentStatus({ onSelectAgent }) {
  const [specialists, setSpecialists] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(apiUrl('/api/agents/specialists'))
      .then(res => res.json())
      .then(data => {
        setSpecialists(data.specialists || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch specialist subagents:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4 flex flex-col gap-3">
      <div className="flex justify-between items-center pb-2 border-b border-line">
        <h4 className="text-xs font-bold text-cyan uppercase tracking-wider flex items-center gap-2">
          <span>🤖</span> AI O&amp;M Multi-Agent Specialist Cluster ({specialists.length || 8} Sub-Agents)
        </h4>
        <div className="flex items-center gap-1.5 text-[10px] text-green font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse"></span> All Specialists Online &amp; Synchronized
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {loading ? (
          <div className="col-span-full py-4 text-center text-xs text-muted">Memuat status cluster sub-agent...</div>
        ) : (
          specialists.map((ag, idx) => (
            <div 
              key={idx} 
              className="p-2.5 bg-panel rounded-xl border border-line flex flex-col justify-between hover:border-cyan/50 transition-colors"
            >
              <div className="flex items-start gap-2">
                <div className="w-7 h-7 rounded-lg bg-panel2 border border-line flex items-center justify-center text-sm shrink-0">
                  {ag.icon || '🤖'}
                </div>
                <div className="flex-1 min-w-0">
                  <strong className="text-[11px] text-textMain block truncate" title={ag.name}>{ag.name}</strong>
                  <span className="text-[9px] text-muted block truncate font-mono">{ag.role}</span>
                </div>
                <span className="text-[8px] px-1 py-0.2 rounded bg-green/10 text-green border border-green/30 font-bold shrink-0">
                  ONLINE
                </span>
              </div>
              <div className="mt-2 pt-1.5 border-t border-line/40 flex items-center justify-between">
                <span className="text-[9px] text-cyan font-mono truncate max-w-[150px]">
                  {ag.standards?.[0] || ag.domain}
                </span>
                <span className="text-[8px] text-muted">Active</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
