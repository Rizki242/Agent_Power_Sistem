// Holds the sidebar's asset tree (see services/assetTree.js). This store
// owns *data*, not selection - the selected equipment lives in the URL
// (/workspace/:moduleId/:equipmentId), so tree highlighting works through
// react-router's own NavLink active-matching instead of duplicated state
// that could drift from the address bar.
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { buildAssetTree } from '../services/assetTree';

const TreeStoreContext = createContext(null);

export function TreeStoreProvider({ children }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    buildAssetTree()
      .then((nodes) => {
        setTree(nodes);
        // Auto-expand unit nodes on first load so the tree isn't empty-looking.
        setExpandedIds((prev) => (prev.size > 0 ? prev : new Set(nodes.map((n) => n.id))));
      })
      .catch((err) => setError(err.message || 'Gagal memuat asset tree'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const toggleExpand = useCallback((nodeId) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  const value = { tree, loading, error, expandedIds, toggleExpand, reload };
  return <TreeStoreContext.Provider value={value}>{children}</TreeStoreContext.Provider>;
}

export function useTreeStore() {
  const ctx = useContext(TreeStoreContext);
  if (!ctx) throw new Error('useTreeStore must be used within TreeStoreProvider');
  return ctx;
}
