import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch, apiUrl } from '../../api';

export default function AlarmAnnunciator() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [alarms, setAlarms] = useState([]);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef(null);

  const fetchAlarms = () => {
    Promise.all([
      apiFetch(apiUrl('/api/equipment?status=High')).then(r => r.json()),
      apiFetch(apiUrl('/api/equipment?status=Alarm')).then(r => r.json())
    ])
      .then(([highData, alarmData]) => {
        const combined = [
          ...(highData.equipment || []),
          ...(alarmData.equipment || [])
        ];
        setAlarms(combined);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load alarms:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchAlarms();
    const interval = setInterval(fetchAlarms, 30000); // 30s auto-refresh
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const highCount = alarms.filter(a => a.condition?.toUpperCase() === 'HIGH').length;
  const alarmCount = alarms.filter(a => a.condition?.toUpperCase() === 'ALARM' || a.condition?.toUpperCase() === 'WARNING').length;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Alarm Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`h-8 px-2.5 rounded-lg border transition-all flex items-center gap-1.5 text-xs font-bold ${
          alarms.length > 0
            ? 'border-red/40 bg-red/10 text-red shadow-[0_0_12px_rgba(239,68,68,0.2)]'
            : 'border-line bg-panel2 text-muted hover:text-textMain'
        }`}
        title="Pusat Alarm Pembangkit (Annunciator)"
      >
        <span className={alarms.length > 0 ? 'animate-bounce' : ''}>🔔</span>
        {alarms.length > 0 ? (
          <span className="flex items-center gap-1">
            <span className="px-1.5 py-0.2 rounded-full bg-red text-white text-[10px] font-black">
              {alarms.length}
            </span>
          </span>
        ) : (
          <span className="hidden sm:inline text-[11px]">0 Alarm</span>
        )}
      </button>

      {/* Dropdown Annunciator Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-panel2 border border-line shadow-[0_0_30px_rgba(0,0,0,0.5)] z-50 p-4 animate-fade-in flex flex-col gap-3">
          <div className="flex justify-between items-center pb-2 border-b border-line">
            <div>
              <strong className="text-xs text-textMain block flex items-center gap-1.5">
                <span>⚠️</span> Alarm Annunciator Center
              </strong>
              <span className="text-[10px] text-muted">
                {highCount} Kritis (High) · {alarmCount} Waspada (Alarm)
              </span>
            </div>
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('/health');
              }}
              className="text-[10px] text-cyan hover:underline font-bold"
            >
              Lihat Semua →
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto space-y-1.5 divide-y divide-line/40 pr-1">
            {loading ? (
              <div className="py-6 text-center text-xs text-muted">Memuat daftar alarm...</div>
            ) : alarms.length === 0 ? (
              <div className="py-6 text-center text-xs text-green font-bold">
                ✅ Seluruh armada peralatan dalam kondisi Normal atau Standby.
              </div>
            ) : (
              alarms.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    setIsOpen(false);
                    navigate('/fusion');
                  }}
                  className="pt-1.5 first:pt-0 flex items-center justify-between hover:bg-panel p-1.5 rounded-lg cursor-pointer transition-colors"
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-1.5">
                      <strong className="text-xs text-textMain truncate">{item.equipment}</strong>
                      <span className="text-[10px] text-muted font-mono">({item.unit})</span>
                    </div>
                    <span className="text-[10px] text-muted block truncate">
                      {item.condition?.toUpperCase() === 'HIGH' ? 'Rotor bar/unbalance kritis' : 'Parameter melewati ambang waspada'}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[9px] font-bold border shrink-0 ${
                      item.condition?.toUpperCase() === 'HIGH'
                        ? 'bg-red/15 text-red border-red/40 animate-pulse'
                        : 'bg-amber/15 text-amber border-amber/40'
                    }`}
                  >
                    {item.condition?.toUpperCase()}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="pt-2 border-t border-line flex justify-between items-center text-[10px] text-muted">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse"></span> Auto-Sync 30s
            </span>
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('/workorders');
              }}
              className="text-cyan font-bold hover:underline"
            >
              Buka Work Order Center →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
