import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/sidebar/Sidebar';
import SidebarResizeHandle from '../components/sidebar/SidebarResizeHandle';
import Topbar from '../components/Topbar';
import Breadcrumb from '../components/navigation/Breadcrumb';
import { useUIStore } from '../stores/uiStore';

// Application shell: Sidebar + Topbar + Breadcrumb + routed content
// (desaindakhir.md's APPLICATION SHELL / LEFT SIDEBAR / MAIN WORKSPACE / TOP BAR).
// Flex (not a fixed-width grid track) so the drag handle can resize the
// sidebar live.
export default function WorkspaceLayout() {
  const { isDark, toggleTheme } = useUIStore();

  return (
    <div className="min-h-screen bg-bg bg-hero-gradient text-textMain font-sans flex">
      <Sidebar />
      <SidebarResizeHandle />
      <main className="min-w-0 flex-1 flex flex-col h-screen overflow-y-auto">
        <Topbar toggleTheme={toggleTheme} isDark={isDark} />
        <Breadcrumb />
        <div className="p-4 md:p-6 lg:p-7 max-w-[1680px] w-full mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
