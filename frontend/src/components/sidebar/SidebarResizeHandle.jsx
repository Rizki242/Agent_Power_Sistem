import React, { useCallback, useRef } from 'react';
import { useUIStore } from '../../stores/uiStore';

// Thin drag handle between the sidebar and the main workspace. The sidebar
// is the first flex child starting at the window's left edge, so the
// pointer's clientX during a drag *is* the new sidebar width - no offset
// math needed. Width is persisted (see uiStore) so it survives a reload,
// and double-click resets it - handy once a long equipment name gets
// truncated and the user just widens the tree to read it.
export default function SidebarResizeHandle() {
  const { setSidebarWidth, resetSidebarWidth } = useUIStore();
  const draggingRef = useRef(false);

  const handlePointerDown = useCallback((e) => {
    draggingRef.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!draggingRef.current) return;
    setSidebarWidth(e.clientX);
  }, [setSidebarWidth]);

  const handlePointerUp = useCallback((e) => {
    draggingRef.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
  }, []);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Seret untuk mengubah lebar sidebar, klik dua kali untuk reset"
      title="Seret untuk mengubah lebar sidebar - klik dua kali untuk reset"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onDoubleClick={resetSidebarWidth}
      className="hidden lg:block w-1.5 shrink-0 cursor-col-resize bg-transparent hover:bg-cyan/40 active:bg-cyan/60 transition-colors touch-none"
    />
  );
}
