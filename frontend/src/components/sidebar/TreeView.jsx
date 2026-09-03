import React from 'react';
import TreeNode from './TreeNode';
import { useTreeStore } from '../../stores/treeStore';

// Recursive renderer over a TreeNode[] - the generic-tree piece of
// desaindakhir.md's sidebar. Doesn't know about units/modules/equipment
// specifically, only about the `children` shape, so a future 'system' or
// 'folder' level slots in without touching this component.
function TreeBranch({ nodes, depth }) {
  const { expandedIds, toggleExpand } = useTreeStore();

  return (
    <>
      {nodes.map((node) => {
        const isExpanded = expandedIds.has(node.id);
        return (
          <React.Fragment key={node.id}>
            <TreeNode node={node} depth={depth} isExpanded={isExpanded} onToggle={toggleExpand} />
            {node.type !== 'equipment' && isExpanded && node.children?.length > 0 && (
              <TreeBranch nodes={node.children} depth={depth + 1} />
            )}
          </React.Fragment>
        );
      })}
    </>
  );
}

export default function TreeView() {
  const { tree, loading, error } = useTreeStore();

  if (loading) {
    return <div className="px-3 py-2 text-[11px] text-muted">Memuat asset tree...</div>;
  }
  if (error) {
    return <div className="px-3 py-2 text-[11px] text-red">{error}</div>;
  }
  if (tree.length === 0) {
    return <div className="px-3 py-2 text-[11px] text-muted">Belum ada data equipment.</div>;
  }

  return (
    <nav className="flex flex-col gap-0.5">
      <TreeBranch nodes={tree} depth={0} />
    </nav>
  );
}
