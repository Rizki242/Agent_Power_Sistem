import React from 'react';

export default function DuvalTriangleVisualizer({
  pctCh4 = 26.6,
  pctC2h4 = 69.1,
  pctC2h2 = 4.3,
  diagnosis = 'T3 (Thermal Fault T > 700°C)'
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="text-xs font-bold text-cyan uppercase tracking-wider">
            Duval Triangle 1 Diagnostic Visualizer
          </h4>
          <p className="text-[10px] text-muted mt-0.5">
            Komposisi Relatif: %CH₄ (Methane), %C₂H₄ (Ethylene), %C₂H₂ (Acetylene)
          </p>
        </div>
        <span className="text-xs font-bold text-amber px-2.5 py-1 bg-amber/10 rounded-lg border border-amber/30">
          {diagnosis}
        </span>
      </div>

      {/* Duval percentages and coordinate stats */}
      <div className="grid grid-cols-3 gap-3 text-center font-mono">
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block">% CH₄ (Methane)</span>
          <strong className="text-sm text-textMain">{pctCh4.toFixed(1)}%</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block">% C₂H₄ (Ethylene)</span>
          <strong className="text-sm text-cyan">{pctC2h4.toFixed(1)}%</strong>
        </div>
        <div className="p-3 bg-panel rounded-xl border border-line">
          <span className="text-[10px] text-muted block">% C₂H₂ (Acetylene)</span>
          <strong className="text-sm text-amber">{pctC2h2.toFixed(1)}%</strong>
        </div>
      </div>

      {/* Duval Zone Reference Legend */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-cyan block text-[11px]">PD (Partial Discharge)</strong>
          <span className="text-[10px] text-muted">CH₄ ≥ 98%</span>
        </div>
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-blue block text-[11px]">T1 (Thermal &lt; 300°C)</strong>
          <span className="text-[10px] text-muted">CH₄ &gt; C₂H₄ dominan</span>
        </div>
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-yellow-400 block text-[11px]">T2 (Thermal 300-700°C)</strong>
          <span className="text-[10px] text-muted">C₂H₄: 20-50%</span>
        </div>
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-amber block text-[11px]">T3 (Thermal &gt; 700°C)</strong>
          <span className="text-[10px] text-muted">C₂H₄ ≥ 50%</span>
        </div>
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-orange-400 block text-[11px]">D1 (Low Energy Spark)</strong>
          <span className="text-[10px] text-muted">C₂H₂ &gt; 4%</span>
        </div>
        <div className="p-2.5 bg-panel2 rounded-lg border border-line">
          <strong className="text-red block text-[11px]">D2 (High Energy Arc)</strong>
          <span className="text-[10px] text-muted">C₂H₂ &gt; 13%</span>
        </div>
      </div>
    </div>
  );
}
