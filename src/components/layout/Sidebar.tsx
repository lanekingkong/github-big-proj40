/**
 * Sidebar
 * =======
 * Primary navigation sidebar with industrial-minimalist design.
 *
 * Features:
 * - Application logo and branding
 * - Navigation menu with active state indicators
 * - Project quick-switcher dropdown
 * - Bottom status indicator (backend connectivity)
 * - Collapsible on smaller viewports
 *
 * Design language: Dark sidebar (slate-950) with warm amber accents,
 * precision typography, subtle hover transitions.
 */

import React, { useState, useCallback } from "react";
import { NavLink, useLocation } from "react-router-dom";

// ---------------------------------------------------------------------------
// Navigation items
// ---------------------------------------------------------------------------

interface NavItem {
  /** Route path */
  to: string;
  /** Display label */
  label: string;
  /** SVG path data for icon */
  icon: string;
  /** Whether this item has a notification badge */
  badge?: number;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Dashboard",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  },
  {
    to: "/projects",
    label: "Projects",
    icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10",
    badge: 3,
  },
  {
    to: "/monitor",
    label: "Monitor",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  {
    to: "/settings",
    label: "Settings",
    icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  },
];

// ---------------------------------------------------------------------------
// Mock Projects for Quick Switch
// ---------------------------------------------------------------------------

const MOCK_PROJECTS = [
  { id: "1", name: "Auth Microservice", status: "in_progress" },
  { id: "2", name: "Dashboard Redesign", status: "planning" },
  { id: "3", name: "API Gateway v2", status: "completed" },
];

// ---------------------------------------------------------------------------
// Icons (inline SVG)
// ---------------------------------------------------------------------------

const LogoSVG: React.FC = () => (
  <svg
    viewBox="0 0 32 32"
    className="w-7 h-7"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Anvil shape — industrial forge metaphor */}
    <path
      d="M8 6h16v4l-2 2H10l-2-2V6z"
      className="fill-amber-500"
    />
    <path
      d="M10 10h12l-1 3H11l-1-3z"
      className="fill-amber-600"
    />
    <rect x="12" y="13" width="8" height="2" rx="1" className="fill-amber-500" />
    <path d="M14 15v6h4v-6" className="fill-amber-400" />
    <path d="M11 21h10l-3 4h-4l-3-4z" className="fill-amber-500" />
  </svg>
);

const ChevronDown: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={`w-4 h-4 ${className}`} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
      clipRule="evenodd"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SidebarProps {
  /** Whether the sidebar is collapsed (mobile) */
  collapsed?: boolean;
  /** Callback to toggle collapsed state */
  onToggle?: () => void;
}

/**
 * Primary application sidebar component.
 *
 * @example
 * ```tsx
 * <Sidebar collapsed={isMobile} onToggle={() => setMobile(false)} />
 * ```
 */
const Sidebar: React.FC<SidebarProps> = ({ collapsed = false }) => {
  const [projectMenuOpen, setProjectMenuOpen] = useState(false);
  const location = useLocation();

  const toggleProjectMenu = useCallback(() => {
    setProjectMenuOpen((prev) => !prev);
  }, []);

  const getStatusClass = (status: string): string => {
    switch (status) {
      case "in_progress":
        return "bg-amber-500";
      case "planning":
        return "bg-slate-500";
      case "completed":
        return "bg-emerald-500";
      default:
        return "bg-slate-600";
    }
  };

  if (collapsed) return null;

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r border-slate-800 bg-slate-950 text-slate-300">
      {/* ---- Logo Section ---- */}
      <div className="flex h-14 items-center gap-3 border-b border-slate-800 px-5">
        <LogoSVG />
        <span className="text-sm font-semibold tracking-widest text-slate-200 uppercase">
          AgentForge
        </span>
        <span className="ml-auto rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
          BETA
        </span>
      </div>

      {/* ---- Project Quick Switch ---- */}
      <div className="border-b border-slate-800 px-3 py-3">
        <button
          onClick={toggleProjectMenu}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-slate-400 transition-colors hover:bg-slate-900 hover:text-slate-200"
        >
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
          <span className="flex-1 truncate">Auth Microservice</span>
          <ChevronDown
            className={`transition-transform duration-200 ${
              projectMenuOpen ? "rotate-180" : ""
            }`}
          />
        </button>

        {projectMenuOpen && (
          <div className="mt-1 space-y-0.5 rounded-lg bg-slate-900 p-1">
            {MOCK_PROJECTS.map((project) => (
              <button
                key={project.id}
                className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${getStatusClass(
                    project.status
                  )}`}
                />
                <span className="truncate">{project.name}</span>
              </button>
            ))}
            <div className="mt-1 border-t border-slate-800 pt-1">
              <button className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs text-amber-400 transition-colors hover:bg-slate-800">
                <span className="text-base leading-none">+</span>
                <span>New Project</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ---- Navigation ---- */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to);

            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive: active }) =>
                    `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                      active || isActive
                        ? "bg-amber-500/10 text-amber-400"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`
                  }
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className={`h-5 w-5 transition-colors ${
                      isActive ? "text-amber-400" : "text-slate-500 group-hover:text-slate-300"
                    }`}
                  >
                    <path d={item.icon} />
                  </svg>
                  <span className="flex-1">{item.label}</span>
                  {item.badge !== undefined && (
                    <span className="rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ---- Bottom Status ---- */}
      <div className="border-t border-slate-800 px-5 py-3">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <span className="text-xs text-slate-500">Backend connected</span>
        </div>
        <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-600">
          <span>3 agents online</span>
          <span className="text-slate-700">|</span>
          <span>2 tasks running</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
