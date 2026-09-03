// Small UI-only store (theme). Moved out of App.jsx so layout/App stay thin.
// Plain Context+useState - no state-management library added, per CLAUDE.md
// ("do not add new frameworks unless they clearly remove real complexity").
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const UIStoreContext = createContext(null);
const THEME_STORAGE_KEY = 'ppleTheme';
const SIDEBAR_WIDTH_STORAGE_KEY = 'ppleSidebarWidth';
export const DEFAULT_SIDEBAR_WIDTH = 268;
const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 480;

function readStoredTheme() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
}

function clampSidebarWidth(width) {
  return Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, width));
}

function readStoredSidebarWidth() {
  try {
    const raw = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY);
    const parsed = raw ? parseInt(raw, 10) : NaN;
    return Number.isFinite(parsed) ? clampSidebarWidth(parsed) : DEFAULT_SIDEBAR_WIDTH;
  } catch {
    return DEFAULT_SIDEBAR_WIDTH;
  }
}

export function UIStoreProvider({ children }) {
  const [isDark, setIsDark] = useState(() => readStoredTheme() !== 'light');
  const [sidebarWidth, setSidebarWidthState] = useState(readStoredSidebarWidth);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, isDark ? 'dark' : 'light');
    } catch {
      // best-effort only (e.g. private browsing)
    }
  }, [isDark]);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth));
    } catch {
      // best-effort only (e.g. private browsing)
    }
  }, [sidebarWidth]);

  const toggleTheme = useCallback(() => setIsDark((v) => !v), []);
  const setSidebarWidth = useCallback((width) => setSidebarWidthState(clampSidebarWidth(width)), []);
  const resetSidebarWidth = useCallback(() => setSidebarWidthState(DEFAULT_SIDEBAR_WIDTH), []);

  return (
    <UIStoreContext.Provider
      value={{ isDark, toggleTheme, sidebarWidth, setSidebarWidth, resetSidebarWidth }}
    >
      {children}
    </UIStoreContext.Provider>
  );
}

export function useUIStore() {
  const ctx = useContext(UIStoreContext);
  if (!ctx) throw new Error('useUIStore must be used within UIStoreProvider');
  return ctx;
}
