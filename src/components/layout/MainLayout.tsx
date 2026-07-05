/**
 * MainLayout
 * ==========
 * Primary layout shell that composes Sidebar, TopBar, content area,
 * and StatusBar into a cohesive application frame.
 *
 * Uses CSS Grid for the overall structure:
 * ```
 * +------------------+---------------------------+
 * |                  |       TopBar              |
 * |     Sidebar      +---------------------------+
 * |                  |       Content             |
 * |                  |     (scrollable)          |
 * |                  +---------------------------+
 * |                  |       StatusBar           |
 * +------------------+---------------------------+
 * ```
 *
 * Design: Full-height grid, sidebar fixed width (16rem),
 * content area fills remaining space.
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import StatusBar from "./StatusBar";

// ---------------------------------------------------------------------------
// Theme Hook (simple, without Zustand — for this iteration)
// ---------------------------------------------------------------------------

type Theme = "dark" | "light";

function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === "undefined") return "dark";
    const stored = localStorage.getItem("agentforge-theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("agentforge-theme", theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return [theme, toggle];
}

// ---------------------------------------------------------------------------
// Responsive Hook — detect mobile
// ---------------------------------------------------------------------------

function useIsMobile(breakpoint: number = 768): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.innerWidth < breakpoint;
  });

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);

  return isMobile;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Root layout component. All routes render inside this layout via `<Outlet />`.
 *
 * Manages:
 * - Theme state (dark/light)
 * - Sidebar collapse on mobile
 * - Scroll position restoration on route change
 *
 * @example
 * ```tsx
 * // In router config:
 * <Route element={<MainLayout />}>
 *   <Route index element={<Dashboard />} />
 *   <Route path="projects" element={<Projects />} />
 * </Route>
 * ```
 */
const MainLayout: React.FC = () => {
  const [theme, toggleTheme] = useTheme();
  const isMobile = useIsMobile();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Auto-close sidebar on route change (mobile)
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

  // Restore scroll position on route change
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = 0;
    }
  }, [location.pathname]);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200 antialiased">
      {/* ---- Sidebar ---- */}
      <Sidebar
        collapsed={isMobile && !sidebarOpen}
        onToggle={toggleSidebar}
      />

      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ---- Right Panel (TopBar + Content + StatusBar) ---- */}
      <div
        className={`flex flex-1 flex-col overflow-hidden transition-all duration-300 ${
          !isMobile ? "ml-64" : ""
        }`}
      >
        {/* Mobile hamburger + TopBar */}
        <TopBar theme={theme} onToggleTheme={toggleTheme} />

        {/* ---- Main Content Area ---- */}
        <main
          ref={contentRef}
          className="flex-1 overflow-y-auto bg-slate-950"
        >
          <div className="mx-auto max-w-7xl p-6">
            <Outlet />
          </div>
        </main>

        {/* ---- Status Bar ---- */}
        <StatusBar />
      </div>
    </div>
  );
};

export default MainLayout;
