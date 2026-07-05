/**
 * TopBar
 * ======
 * Application top bar with page context and utility controls.
 *
 * Features:
 * - Current page title with optional breadcrumb trail
 * - Theme toggle (dark / light)
 * - Notification center with unread count
 * - Keyboard shortcut hints (inactive—decorative)
 *
 * Design language: Dark bar (slate-900) with subtle glass effect,
 * warm amber accents for interactive elements.
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

// ---------------------------------------------------------------------------
// Breadcrumb mapping
// ---------------------------------------------------------------------------

const BREADCRUMB_MAP: Record<string, { title: string; parent?: string }> = {
  "/": { title: "Dashboard" },
  "/projects": { title: "Projects" },
  "/monitor": { title: "Monitor" },
  "/settings": { title: "Settings" },
};

// ---------------------------------------------------------------------------
// Inline SVG Icons
// ---------------------------------------------------------------------------

const SunIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
      clipRule="evenodd"
    />
  </svg>
);

const MoonIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
  </svg>
);

const BellIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
  </svg>
);

const CloseIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
      clipRule="evenodd"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Mock Notifications
// ---------------------------------------------------------------------------

interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type: "info" | "success" | "warning" | "error";
}

const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: "1",
    title: "Pipeline complete",
    message: "Auth Microservice pipeline finished successfully.",
    time: "2m ago",
    read: false,
    type: "success",
  },
  {
    id: "2",
    title: "Agent offline",
    message: "Tester agent disconnected unexpectedly.",
    time: "15m ago",
    read: false,
    type: "warning",
  },
  {
    id: "3",
    title: "New version available",
    message: "AgentForge v0.2.0 is ready to install.",
    time: "1h ago",
    read: true,
    type: "info",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface TopBarProps {
  /** Current theme: "dark" or "light" */
  theme: "dark" | "light";
  /** Callback to toggle theme */
  onToggleTheme: () => void;
}

/**
 * Application top bar component.
 *
 * @example
 * ```tsx
 * <TopBar theme={theme} onToggleTheme={toggleTheme} />
 * ```
 */
const TopBar: React.FC<TopBarProps> = ({ theme, onToggleTheme }) => {
  const location = useLocation();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);

  const unreadCount = MOCK_NOTIFICATIONS.filter((n) => !n.read).length;

  // Close notification panel on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        notificationRef.current &&
        !notificationRef.current.contains(e.target as Node)
      ) {
        setNotificationsOpen(false);
      }
    };
    if (notificationsOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [notificationsOpen]);

  const toggleNotifications = useCallback(() => {
    setNotificationsOpen((prev) => !prev);
  }, []);

  // Derive breadcrumb from path
  const pathSegments = location.pathname.split("/").filter(Boolean);
  const currentPath = pathSegments.length === 0 ? "/" : `/${pathSegments[0]}`;
  const pageInfo = BREADCRUMB_MAP[currentPath] || { title: "Unknown" };

  const typeBorderClass: Record<string, string> = {
    success: "border-l-emerald-500",
    warning: "border-l-amber-500",
    info: "border-l-blue-500",
    error: "border-l-red-500",
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-slate-800 bg-slate-900/80 px-6 backdrop-blur-md">
      {/* ---- Page Title & Breadcrumb ---- */}
      <div className="flex items-baseline gap-2">
        <h1 className="text-sm font-semibold tracking-wide text-slate-200">
          {pageInfo.title}
        </h1>
        {pageInfo.parent && (
          <>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs text-slate-500">{pageInfo.parent}</span>
          </>
        )}
      </div>

      {/* ---- Spacer ---- */}
      <div className="flex-1" />

      {/* ---- Keyboard Hint (decorative) ---- */}
      <div className="hidden items-center gap-1.5 rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-[10px] text-slate-600 sm:flex">
        <kbd className="rounded border border-slate-700 px-1 py-0.5 text-[9px] text-slate-500">
          Ctrl
        </kbd>
        <span className="text-slate-700">+</span>
        <kbd className="rounded border border-slate-700 px-1 py-0.5 text-[9px] text-slate-500">
          K
        </kbd>
      </div>

      {/* ---- Notification Bell ---- */}
      <div className="relative" ref={notificationRef}>
        <button
          onClick={toggleNotifications}
          className={`relative rounded-lg p-2 transition-colors hover:bg-slate-800 ${
            notificationsOpen ? "bg-slate-800 text-amber-400" : "text-slate-400"
          }`}
          aria-label="Notifications"
        >
          <BellIcon className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[9px] font-bold text-slate-950">
              {unreadCount}
            </span>
          )}
        </button>

        {/* Notification Dropdown */}
        {notificationsOpen && (
          <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <span className="text-xs font-semibold text-slate-300">
                Notifications
              </span>
              <button
                onClick={() => setNotificationsOpen(false)}
                className="rounded p-0.5 text-slate-500 transition-colors hover:text-slate-300"
              >
                <CloseIcon className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {MOCK_NOTIFICATIONS.map((notif) => (
                <div
                  key={notif.id}
                  className={`border-l-2 px-4 py-3 transition-colors hover:bg-slate-900 ${
                    notif.read
                      ? "border-l-transparent opacity-60"
                      : typeBorderClass[notif.type]
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-slate-200">
                      {notif.title}
                    </p>
                    <span className="shrink-0 text-[10px] text-slate-600">
                      {notif.time}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {notif.message}
                  </p>
                </div>
              ))}
            </div>
            <div className="border-t border-slate-800 px-4 py-2">
              <button className="text-[10px] font-medium text-amber-400 transition-colors hover:text-amber-300">
                Mark all as read
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ---- Theme Toggle ---- */}
      <button
        onClick={onToggleTheme}
        className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-amber-400"
        aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      >
        {theme === "dark" ? (
          <SunIcon className="h-5 w-5" />
        ) : (
          <MoonIcon className="h-5 w-5" />
        )}
      </button>
    </header>
  );
};

export default TopBar;
