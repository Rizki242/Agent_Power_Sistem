import React from 'react';
import { NavLink } from 'react-router-dom';

// Icon by node type, not by domain - stays correct for any module a new
// manifest adds (docs/final.md Phase 25 / desaindakhir.md TreeNode).
const TYPE_ICON = {
  unit: '\u{1F3ED}', // factory
  module: '\u{1F4E1}', // satellite antenna (CBM/engineering module)
  equipment: '\u{2699}\u{FE0F}', // gear
};

const STATUS_DOT = {
  NORMAL: 'bg-green',
  ALARM: 'bg-amber',
  WARNING: 'bg-amber',
  HIGH: 'bg-red',
  CRITICAL: 'bg-red',
  STANDBY: 'bg-slate-400',
};

function statusDotClass(status) {
  return STATUS_DOT[String(status || '').toUpperCase()] || 'bg-muted';
}

export default function TreeNode({ node, depth, isExpanded, onToggle }) {
  const hasChildren = Array.isArray(node.children) && node.children.length > 0;
  const indent = { paddingLeft: `${10 + depth * 14}px` };
  const rowBase =
    'flex items-center gap-1.5 py-1.5 pr-2 rounded-lg text-[12.5px] w-full text-left transition-colors';

  if (node.type === 'equipment') {
    const to = `/workspace/${node.metadata?.moduleId}/${encodeURIComponent(node.metadata?.equipmentId)}`;
    return (
      <NavLink
        to={to}
        style={indent}
        className={({ isActive }) =>
          `${rowBase} ${isActive
            ? 'bg-panel2 border border-line text-textMain font-semibold shadow-[inset_3px_0_0_var(--cyan)]'
            : 'text-muted hover:bg-panel2 hover:text-textMain border border-transparent'}`
        }
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusDotClass(node.metadata?.status)}`} />
        <span className="truncate">{node.name}</span>
      </NavLink>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onToggle(node.id)}
      style={indent}
      className={`${rowBase} text-muted hover:bg-panel2 hover:text-textMain`}
      aria-expanded={hasChildren ? isExpanded : undefined}
    >
      {hasChildren && (
        <span className="text-[9px] w-3 shrink-0 text-muted">{isExpanded ? '▼' : '▶'}</span>
      )}
      <span className="shrink-0">{TYPE_ICON[node.type] || '\u{1F4C1}'}</span>
      <span className="truncate font-semibold">{node.name}</span>
      {hasChildren && node.type !== 'unit' && (
        <span className="ml-auto text-[10px] text-muted/70 font-mono">{node.children.length}</span>
      )}
    </button>
  );
}
