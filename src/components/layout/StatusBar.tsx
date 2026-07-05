/**
 * StatusBar
 * =========
 * Bottom status bar displaying system health and runtime metrics.
 *
 * Features:
 * - Backend connection status (green/red dot + ping latency)
 * - Active agent count
 * - Running tasks count
 * - Memory usage indicator (simulated)
 * - Auto-refresh of metrics
 *
 * Design language: Compact dark bar (slate-950) with monospaced values,
 * warm amber accents for active counts, emerald for healthy state.
 */

import React, { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Inline Icons
// ---------------------------------------------------------------------------

const ActivityIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M1 8a.5.5 0 01.5-.5h2a.5.5 0 01.47.33l1.19 3.56 2.38-9.51a.5.5 0 01.92 0l1.68 6.72 1.1-2.2A.5.5 0 0111.5 6h3a.5.5 0 010 1h-2.69l-1.44 2.89a.5.5 0 01-.9-.06L7.87 3.26 5.97 10.85a.5.5 0 01-.94.06l-1.38-4.14L3.28 7.7A.5.5 0 013 7.5H1.5A.5.5 0 011 8z"
    />
  </svg>
);

const MemoryIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor">
    <path d="M3 2a1 1 0 00-1 1v3h1V3h2v3h1V3h2v3h1V3h2v3h1V3a1 1 0 00-1-1H3zm-1 5v5a1 1 0 001 1h10a1 1 0 001-1V7H2zm2 2h2v2H4V9zm4 0h1v2H8V9zm2 0h2v2h-2V9z" />
  </svg>
);

const TaskIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 1a.5.5 0 01.5.5V2h2a.5.5 0 01.5.5v2a.5.5 0 01-.5.5h-5a.5.5 0 01-.5-.5v-2a.5.5 0 01.5-.5h2v-.5A.5.5 0 018 1zM5.5 6h5a.5.5 0 01.5.5V8H5V6.5a.5.5 0 01.5-.5zM5 9h6v5.5a.5.5 0 01-.5.5h-5a.5.5 0 01-.5-.5V9z" />
  </svg>
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SystemMetrics {
  /** Backend is reachable */
  connected: boolean;
  /** Simulated ping in ms */
  pingMs: number;
  /** Number of active agents */
  activeAgents: number;
  /** Number of currently running tasks */
  runningTasks: number;
  /** Simulated memory usage in MB */
  memoryUsedMb: number;
  /** Simulated total memory in MB */
  memoryTotalMb: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Bottom status bar displaying system health metrics.
 *
 * Auto-refreshes metrics every 5 seconds (simulated data).
 *
 * @example
 * ```tsx
 * <StatusBar />
 * ```
 */
const StatusBar: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics>({
    connected: true,
    pingMs: 12,
    activeAgents: 3,
    runningTasks: 2,
    memoryUsedMb: 284,
    memoryTotalMb: 1024,
  });

  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // Simulate periodic metrics refresh
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => ({
        ...prev,
        pingMs: Math.max(8, Math.min(35, prev.pingMs + (Math.random() - 0.5) * 6)),
        memoryUsedMb: Math.max(
          200,
          Math.min(900, prev.memoryUsedMb + (Math.random() - 0.5) * 20)
        ),
      }));
      setLastUpdated(new Date());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const memoryPercent = Math.round(
    (metrics.memoryUsedMb / metrics.memoryTotalMb) * 100
  );

  const formatMemory = useCallback((mb: number): string => {
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${Math.round(mb)} MB`;
  }, []);

  return (
    <footer className="flex h-8 items-center gap-4 border-t border-slate-800 bg-slate-950 px-6 text-[11px] text-slate-500">
      {/* ---- Backend Status ---- */}
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          {metrics.connected && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          )}
          <span
            className={`relative inline-flex h-2 w-2 rounded-full ${
              metrics.connected ? "bg-emerald-500" : "bg-red-500"
            }`}
          />
        </span>
        <span className="font-mono text-slate-500">
          {metrics.connected ? `connected` : "disconnected"}
        </span>
        {metrics.connected && (
          <span className="font-mono text-slate-600">
            {Math.round(metrics.pingMs)}ms
          </span>
        )}
      </div>

      {/* ---- Spacer ---- */}
      <div className="flex-1" />

      {/* ---- Active Agents ---- */}
      <div className="flex items-center gap-1.5">
        <ActivityIcon className="h-3.5 w-3.5 text-slate-600" />
        <span className="font-mono text-amber-400">{metrics.activeAgents}</span>
        <span className="text-slate-600">agents</span>
      </div>

      {/* ---- Running Tasks ---- */}
      <div className="flex items-center gap-1.5">
        <TaskIcon className="h-3.5 w-3.5 text-slate-600" />
        <span className="font-mono text-amber-400">{metrics.runningTasks}</span>
        <span className="text-slate-600">running</span>
      </div>

      {/* ---- Memory ---- */}
      <div className="flex items-center gap-1.5">
        <MemoryIcon className="h-3.5 w-3.5 text-slate-600" />
        <span className="font-mono">
          {formatMemory(metrics.memoryUsedMb)} / {formatMemory(metrics.memoryTotalMb)}
        </span>
        {/* Minimal memory bar */}
        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-slate-600 transition-all duration-1000"
            style={{ width: `${memoryPercent}%` }}
          />
        </div>
      </div>

      {/* ---- Divider ---- */}
      <span className="text-slate-700 select-none">|</span>

      {/* ---- Last Updated ---- */}
      <span className="font-mono text-slate-600">
        {lastUpdated.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })}
      </span>
    </footer>
  );
};

export default StatusBar;
