import React from 'react';
import { NavLink } from 'react-router-dom';

export default function Sidebar() {
  const activeClass = "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] bg-panel2 border border-line text-textMain shadow-[inset_3px_0_0_var(--cyan)] font-semibold";
  const inactiveClass = "flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] text-muted hover:bg-panel2 hover:text-textMain transition-colors";

  return (
    <aside className="sticky top-0 h-screen p-5 border-r border-line bg-bg/95 backdrop-blur-md flex flex-col gap-5 overflow-y-auto hidden lg:flex">
      <div className="flex items-center gap-3 px-2">
        <div className="w-10 h-10 border border-cyan/30 rounded-xl flex items-center justify-center shadow-[inset_0_0_28px_rgba(50,213,255,0.08)] bg-cyan/5">
          <span className="font-black text-cyan tracking-tighter text-lg">⚡</span>
        </div>
        <div>
          <h1 className="text-[15px] font-bold m-0 tracking-wide text-textMain">PPLE AGENT</h1>
          <p className="m-0 mt-0.5 text-muted text-[10px] tracking-widest uppercase">Predictive Maintenance AI</p>
        </div>
      </div>

      <div className="mx-2 p-3 border border-line rounded-xl bg-gradient-to-b from-panel to-panel2">
        <small className="block text-muted text-[10px] uppercase tracking-[0.12em] font-bold">Active Plant</small>
        <strong className="block mt-1 text-[13px] text-textMain">PLTU Jeranjang · 3 × 25 MW</strong>
      </div>

      <div className="flex flex-col gap-5 mt-2 flex-1">
        <div>
          <div className="text-[10px] text-muted uppercase tracking-[0.16em] px-3 mb-2 font-bold">Command Center</div>
          <nav className="flex flex-col gap-1">
            <NavLink to="/" className={({isActive}) => isActive ? activeClass : inactiveClass} end>
              <span className="w-2 h-2 rounded-full bg-cyan shadow-[0_0_12px_var(--cyan)]"></span> Overview
            </NavLink>
            <NavLink to="/fusion" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-purple shadow-[0_0_12px_var(--purple)]"></span> Reliability Fusion
            </NavLink>
            <NavLink to="/twin" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-blue shadow-[0_0_12px_var(--blue)]"></span> Digital Twin
            </NavLink>
            <NavLink to="/health" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-green"></span> Fleet Health
            </NavLink>
            <NavLink to="/workorders" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-amber"></span> Work Orders & EAM
            </NavLink>
          </nav>
        </div>

        <div>
          <div className="text-[10px] text-muted uppercase tracking-[0.16em] px-3 mb-2 font-bold">PdM Workspaces</div>
          <nav className="flex flex-col gap-1">
            <NavLink to="/mcsa" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-cyan"></span> MCSA (Electrical)
            </NavLink>
            <NavLink to="/vibration" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-blue"></span> Vibration
            </NavLink>
            <NavLink to="/tribology" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-amber"></span> Tribology (Oil)
            </NavLink>
            <NavLink to="/thermal" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-orange-400"></span> Thermal (IRT)
            </NavLink>
            <NavLink to="/dga" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-purple"></span> DGA (Transformer)
            </NavLink>
          </nav>
        </div>

        <div>
          <div className="text-[10px] text-muted uppercase tracking-[0.16em] px-3 mb-2 font-bold">Knowledge & SOP</div>
          <nav className="flex flex-col gap-1">
            <NavLink to="/knowledge" className={({isActive}) => isActive ? activeClass : inactiveClass}>
              <span className="w-2 h-2 rounded-full bg-slate-400"></span> Knowledge Base
            </NavLink>
          </nav>
        </div>
      </div>

      <div className="p-3 border border-line rounded-xl bg-panel text-xs text-muted flex items-center justify-between">
        <span className="text-[10px] font-mono">Agent Engine v3.0</span>
        <span className="flex items-center gap-1.5 text-[10px] text-green font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse"></span> ONLINE
        </span>
      </div>
    </aside>
  );
}
