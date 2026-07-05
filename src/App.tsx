/**
 * App Root Component
 * ==================
 * Top-level application component responsible for:
 * - Theme management (light / dark / system)
 * - Hash-based routing (Dashboard, ForgeEditor, Monitor, Settings)
 * - Global state providers (theme, backend status)
 * - Layout shell (sidebar + content area)
 *
 * Uses React Router v6 with hash history for Electron compatibility.
 */

import React, { useState, useEffect, useCallback, createContext } from "react";
import {
  HashRouter,
  Routes,
  Route,
  NavLink,
  useLocation,
} from "react-router-dom";
import type { ThemeMode } from "./types/common";

// ---------------------------------------------------------------------------
// Lazy-loaded page components
// ---------------------------------------------------------------------------

/** Fallback component shown while a page chunk loads. */
const PageFallback: React.FC = () => (
  <div className="flex items-center justify-center h-full">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
      <span className="text-sm text-secondary">Loading...</span>
    </div>
  </div>
);

const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const ForgeEditor = React.lazy(() => import("./pages/ForgeEditor"));
const Monitor = React.lazy(() => import("./pages/Monitor"));
const Settings = React.lazy(() => import("./pages/Settings"));

// ---------------------------------------------------------------------------
// Theme Context
// ---------------------------------------------------------------------------

interface ThemeContextValue {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  isDark: boolean;
}

export const ThemeContext = createContext<ThemeContextValue>({
  theme: "system",
  setTheme: () => {},
  isDark: false,
});

// ---------------------------------------------------------------------------
// Navigation items
// ---------------------------------------------------------------------------

interface NavItem {
  path: string;
  label: string;
  icon: string; // Simple text icon, will be replaced by proper icon set later
}

const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", icon: "D" },
  { path: "/forge", label: "Forge Editor", icon: "F" },
  { path: "/monitor", label: "Monitor", icon: "M" },
  { path: "/settings", label: "Settings", icon: "S" },
];

// ---------------------------------------------------------------------------
// Sidebar Component
// ---------------------------------------------------------------------------

/**
 * Persistent sidebar navigation.
 * Highlights the active route and provides quick access to all pages.
 */
const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <aside className="w-60 h-full flex flex-col bg-surface-sidebar border-r border-surface-border">
      {/* Logo area */}
      <div className="h-14 flex items-center px-4 border-b border-surface-border">
        <span className="text-lg font-bold text-primary-600">AgentForge</span>
        <span className="ml-auto text-xs text-tertiary">v0.1.0</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
                  : "text-secondary hover:bg-surface-hover hover:text-primary"
              }`}
            >
              <span
                className={`flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${
                  isActive
                    ? "bg-primary-500 text-white"
                    : "bg-surface-active text-tertiary"
                }`}
              >
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-surface-border">
        <ConnectionIndicator />
      </div>
    </aside>
  );
};

/**
 * Small component showing backend connection status in the sidebar footer.
 */
const ConnectionIndicator: React.FC = () => {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        if (window.electronAPI) {
          const status = await window.electronAPI.getBackendStatus();
          setConnected(status.running);
        }
      } catch {
        setConnected(false);
      }
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        className={`w-2 h-2 rounded-full ${
          connected ? "bg-success-500" : "bg-danger-500"
        }`}
      />
      <span className={connected ? "text-success-500" : "text-danger-500"}>
        {connected ? "Backend Online" : "Backend Offline"}
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Theme Toggle Component
// ---------------------------------------------------------------------------

/**
 * Quick theme switcher in the header area.
 */
const ThemeToggle: React.FC<{
  theme: ThemeMode;
  onChange: (mode: ThemeMode) => void;
}> = ({ theme, onChange }) => {
  const modes: { mode: ThemeMode; label: string }[] = [
    { mode: "light", label: "Light" },
    { mode: "dark", label: "Dark" },
    { mode: "system", label: "System" },
  ];

  return (
    <div className="flex items-center bg-surface-hover rounded-lg p-0.5">
      {modes.map(({ mode, label }) => (
        <button
          key={mode}
          onClick={() => onChange(mode)}
          className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
            theme === mode
              ? "bg-surface-card text-primary shadow-sm"
              : "text-tertiary hover:text-secondary"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
};

// ---------------------------------------------------------------------------
// App Component
// ---------------------------------------------------------------------------

/**
 * Root application component.
 *
 * Sets up the theme context, hash router, and overall layout shell
 * (sidebar + header + content area).
 */
export const App: React.FC = () => {
  // ---- Theme State ----
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem("agentforge-theme") as ThemeMode | null;
    return stored ?? "system";
  });

  const isDark = useCallback((): boolean => {
    if (theme === "dark") return true;
    if (theme === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }, [theme]);

  const [darkMode, setDarkMode] = useState(isDark);

  // Apply theme class to document
  useEffect(() => {
    const update = () => {
      const dark = isDark();
      setDarkMode(dark);
      document.documentElement.classList.toggle("dark", dark);
    };
    update();

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [theme, isDark]);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
    localStorage.setItem("agentforge-theme", mode);
  }, []);

  const themeContextValue: ThemeContextValue = { theme, setTheme, isDark: darkMode };

  // ---- Render ----
  return (
    <ThemeContext.Provider value={themeContextValue}>
      <HashRouter>
        <div className="flex h-screen w-screen overflow-hidden bg-surface-bg text-primary">
          {/* Sidebar */}
          <Sidebar />

          {/* Main content area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Header bar */}
            <header className="h-14 flex items-center justify-between px-6 border-b border-surface-border bg-surface-card shrink-0">
              <h1 className="text-sm font-semibold text-secondary tracking-wide">
                Agent Orchestration Platform
              </h1>
              <ThemeToggle theme={theme} onChange={setTheme} />
            </header>

            {/* Page content */}
            <main className="flex-1 overflow-hidden">
              <React.Suspense fallback={<PageFallback />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/forge" element={<ForgeEditor />} />
                  <Route path="/monitor" element={<Monitor />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </React.Suspense>
            </main>
          </div>
        </div>
      </HashRouter>
    </ThemeContext.Provider>
  );
};

export default App;
