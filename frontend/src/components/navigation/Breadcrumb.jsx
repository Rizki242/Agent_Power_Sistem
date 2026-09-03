import React from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { useTreeStore } from '../../stores/treeStore';

const FIXED_LABELS = {
  '': 'Overview',
  fusion: 'Reliability Fusion',
  twin: 'Digital Twin',
  health: 'Fleet Health',
  workorders: 'Work Orders & EAM',
  knowledge: 'Knowledge Base',
  'engineering-modules': 'Engineering Modules',
};

function findEquipmentName(tree, moduleId, equipmentId) {
  for (const unit of tree) {
    const moduleNode = unit.children?.find((m) => m.metadata?.moduleId === moduleId);
    const eqNode = moduleNode?.children?.find((e) => e.metadata?.equipmentId === equipmentId);
    if (eqNode) return { unitName: unit.name, moduleName: moduleNode.name, equipmentName: eqNode.name };
  }
  return null;
}

// Path shown above the workspace content, derived from the current route -
// mirrors desaindakhir.md's "Breadcrumb" main-area element.
export default function Breadcrumb() {
  const location = useLocation();
  const params = useParams();
  const { tree } = useTreeStore();

  const segments = [{ label: 'PLTU Jeranjang', to: '/' }];

  if (location.pathname.startsWith('/workspace/')) {
    // Each workspace route spells its module out literally
    // (workspace/mcsa/:equipmentId?), so there is no :moduleId param to read -
    // it has to come from the path itself.
    const moduleId = location.pathname.split('/').filter(Boolean)[1];
    const { equipmentId } = params;
    const resolved = findEquipmentName(tree, moduleId, equipmentId);
    segments.push({ label: 'Engineering' });
    segments.push({ label: resolved?.unitName || '...' });
    segments.push({ label: resolved?.moduleName || moduleId });
    if (equipmentId) segments.push({ label: resolved?.equipmentName || decodeURIComponent(equipmentId) });
  } else {
    const key = location.pathname.replace(/^\//, '');
    segments.push({ label: FIXED_LABELS[key] || key });
  }

  return (
    <div className="flex items-center gap-1.5 text-[11px] text-muted px-5 md:px-7 pt-3 flex-wrap">
      {segments.map((seg, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-muted/50">/</span>}
          {seg.to ? (
            <Link to={seg.to} className="hover:text-cyan transition-colors">
              {seg.label}
            </Link>
          ) : (
            <span className={i === segments.length - 1 ? 'text-textMain font-semibold' : ''}>{seg.label}</span>
          )}
        </span>
      ))}
    </div>
  );
}
