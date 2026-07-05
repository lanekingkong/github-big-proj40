/**
 * StatsOverview
 * =============
 * Dashboard statistics panel showing key metrics with animated
 * number counters.
 *
 * Metrics displayed:
 * - Total projects
 * - Active agents (online)
 * - Tasks executed today
 * - Success rate (%)
 *
 * Design: 4-column grid of stat cards with gradient accent borders,
 * animated count-up numbers on mount.
 */

import React, { useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Inline SVG Icons
// ---------------------------------------------------------------------------

const StatIcons: Record<string, React.FC<{ className?: string }>> = {
  projects: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
    </svg>
  ),
  agents: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
    </svg>
  ),
  tasks: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
        clipRule="evenodd"
      />
    </svg>
  ),
  success: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z"
        clipRule="evenodd"
      />
    </svg>
  ),
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StatCard {
  /** Metric key */
  key: string;
  /** Display label */
  label: string;
  /** Current value */
  value: number;
  /** Optional suffix (e.g., "%") */
  suffix?: string;
  /** Accent color class for the border */
  accentClass: string;
  /** Icon component key */
  iconKey: string;
  /** Previous value for delta comparison */
  previousValue?: number;
}

// ---------------------------------------------------------------------------
// Animated Counter Hook
// ---------------------------------------------------------------------------

/**
 * Animate a number from 0 to the target value over a given duration.
 */
function useAnimatedCounter(
  target: number,
  duration: number = 1200,
  enabled: boolean = true
): number {
  const [current, setCurrent] = useState(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    if (!enabled) {
      setCurrent(target);
      return;
    }

    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(target * eased));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration, enabled]);

  return current;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface StatsOverviewProps {
  /** Total project count */
  totalProjects: number;
  /** Active (online) agent count */
  activeAgents: number;
  /** Tasks executed today */
  tasksToday: number;
  /** Success rate (0-100) */
  successRate: number;
}

/**
 * Dashboard statistics panel with animated counters.
 *
 * @example
 * ```tsx
 * <StatsOverview
 *   totalProjects={12}
 *   activeAgents={5}
 *   tasksToday={47}
 *   successRate={94}
 * />
 * ```
 */
const StatsOverview: React.FC<StatsOverviewProps> = ({
  totalProjects,
  activeAgents,
  tasksToday,
  successRate,
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Small delay to ensure mount animation plays
    const timer = setTimeout(() => setIsVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  const stats: StatCard[] = [
    {
      key: "projects",
      label: "Projects",
      value: totalProjects,
      accentClass: "border-l-amber-500",
      iconKey: "projects",
    },
    {
      key: "agents",
      label: "Active Agents",
      value: activeAgents,
      accentClass: "border-l-emerald-500",
      iconKey: "agents",
    },
    {
      key: "tasks",
      label: "Tasks Today",
      value: tasksToday,
      accentClass: "border-l-blue-500",
      iconKey: "tasks",
    },
    {
      key: "success",
      label: "Success Rate",
      value: successRate,
      suffix: "%",
      accentClass: "border-l-purple-500",
      iconKey: "success",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, i) => {
        const Icon = StatIcons[stat.iconKey];
        const animatedValue = useAnimatedCounter(stat.value, 1200, isVisible);

        return (
          <div
            key={stat.key}
            className={`rounded-xl border border-slate-800 bg-slate-900 p-5 transition-all duration-500 ${stat.accentClass} ${
              isVisible
                ? "translate-y-0 opacity-100"
                : "translate-y-4 opacity-0"
            }`}
            style={{ transitionDelay: `${i * 80}ms` }}
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                {stat.label}
              </span>
              <Icon className="h-4 w-4 text-slate-600" />
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold tabular-nums text-slate-200">
                {animatedValue.toLocaleString()}
              </span>
              {stat.suffix && (
                <span className="text-sm text-slate-500">{stat.suffix}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default StatsOverview;
