/**
 * AgentPanel
 * ==========
 * Left sidebar panel listing available agents for drag-and-drop onto
 * the forge canvas.
 *
 * Features:
 * - Agent list sorted by role groups
 * - Role group headers (collapsible)
 * - Search/filter input
 * - Online/offline status badge per agent
 * - Drag-to-canvas support (HTML5 Drag & Drop API)
 * - Hover preview with role description
 *
 * Design: Dark panel (slate-900), amber accent on selected/drag state.
 */

import React, { useState, useMemo, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: "online" | "offline" | "busy" | "error";
}

interface AgentPanelProps {
  agents: AgentInfo[];
}

// ---------------------------------------------------------------------------
// Role Group Config
// ---------------------------------------------------------------------------

interface RoleGroup {
  role: string;
  label: string;
  description: string;
  color: string;
}

const ROLE_GROUPS: RoleGroup[] = [
  { role: "developer", label: "Developers", description: "Write and edit code", color: "text-blue-400" },
  { role: "reviewer", label: "Reviewers", description: "Review pull requests", color: "text-purple-400" },
  { role: "fixer", label: "Fixers", description: "Resolve issues and bugs", color: "text-orange-400" },
  { role: "tester", label: "Testers", description: "Run test suites", color: "text-teal-400" },
  { role: "deployer", label: "Deployers", description: "Deploy to environments", color: "text-emerald-400" },
];

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const SearchIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
  </svg>
);

const DragIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
  </svg>
);

const Chevron: React.FC<{ open: boolean; className?: string }> = ({ open, className = "" }) => (
  <svg className={`transition-transform duration-200 ${open ? "rotate-90" : ""} ${className}`} viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
  </svg>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Agent panel for the forge editor's left sidebar.
 */
const AgentPanel: React.FC<AgentPanelProps> = ({ agents }) => {
  const [search, setSearch] = useState("");
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = useCallback((role: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  }, []);

  // Group agents by role
  const grouped = useMemo(() => {
    const map = new Map<string, AgentInfo[]>();
    for (const a of agents) {
      if (!map.has(a.role)) map.set(a.role, []);
      map.get(a.role)!.push(a);
    }
    return map;
  }, [agents]);

  // Filter groups by search
  const filteredGroups = useMemo(() => {
    if (!search.trim()) return ROLE_GROUPS;
    const q = search.toLowerCase();
    return ROLE_GROUPS.filter((g) => {
      const groupAgents = grouped.get(g.role) || [];
      return (
        g.label.toLowerCase().includes(q) ||
        g.description.toLowerCase().includes(q) ||
        groupAgents.some((a) => a.name.toLowerCase().includes(q))
      );
    });
  }, [search, grouped]);

  // Handle drag start
  const onDragStart = useCallback(
    (event: React.DragEvent, agent: AgentInfo) => {
      event.dataTransfer.setData(
        "application/agentforge-agent",
        JSON.stringify(agent)
      );
      event.dataTransfer.effectAllowed = "move";
    },
    []
  );

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900">
      {/* ---- Header ---- */}
      <div className="border-b border-slate-800 px-4 py-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Agents
        </h3>
        <div className="mt-2.5 relative">
          <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter agents..."
            className="w-full rounded-lg border border-slate-800 bg-slate-950 py-1.5 pl-8 pr-3 text-[11px] text-slate-300 placeholder:text-slate-600 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/20"
          />
        </div>
      </div>

      {/* ---- Agent List by Role Groups ---- */}
      <div className="flex-1 overflow-y-auto">
        {filteredGroups.map((group) => {
          const groupAgents = (grouped.get(group.role) || []).filter(
            (a) =>
              !search.trim() ||
              a.name.toLowerCase().includes(search.toLowerCase())
          );
          const isCollapsed = collapsedGroups.has(group.role);

          // Count online/busy
          const onlineCount = groupAgents.filter(
            (a) => a.status === "online" || a.status === "busy"
          ).length;

          return (
            <div key={group.role} className="border-b border-slate-800/50">
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.role)}
                className="flex w-full items-center gap-2 px-4 py-2 text-left transition-colors hover:bg-slate-800/50"
              >
                <Chevron open={!isCollapsed} className="h-3 w-3 text-slate-600" />
                <span className="flex-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {group.label}
                </span>
                <span className="text-[9px] tabular-nums text-slate-600">
                  {onlineCount}/{groupAgents.length}
                </span>
              </button>

              {/* Agent Items */}
              {!isCollapsed &&
                groupAgents.map((agent) => (
                  <div
                    key={agent.id}
                    draggable
                    onDragStart={(e) => onDragStart(e, agent)}
                    className="group flex cursor-grab items-center gap-2.5 px-4 py-2 transition-colors hover:bg-slate-800/60 active:cursor-grabbing"
                  >
                    {/* Drag handle */}
                    <DragIcon className="h-3.5 w-3.5 shrink-0 text-slate-700 opacity-0 transition-opacity group-hover:opacity-100" />

                    {/* Agent Info */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-medium text-slate-300 group-hover:text-slate-200">
                        {agent.name}
                      </p>
                      <p className="text-[9px] text-slate-600">{agent.role}</p>
                    </div>

                    {/* Status Dot */}
                    <span
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                        agent.status === "online"
                          ? "bg-emerald-500"
                          : agent.status === "busy"
                          ? "bg-amber-500"
                          : agent.status === "error"
                          ? "bg-red-500"
                          : "bg-slate-700"
                      }`}
                    />
                  </div>
                ))}

              {/* Empty state for group */}
              {!isCollapsed && groupAgents.length === 0 && (
                <p className="px-4 py-3 text-[10px] text-slate-700">
                  No {group.label.toLowerCase()} available
                </p>
              )}
            </div>
          );
        })}

        {/* No results */}
        {filteredGroups.length === 0 && (
          <div className="flex flex-col items-center py-12 px-4">
            <SearchIcon className="mb-2 h-6 w-6 text-slate-700" />
            <p className="text-[11px] text-slate-600">No agents match</p>
          </div>
        )}
      </div>

      {/* ---- Footer: Agent Count ---- */}
      <div className="border-t border-slate-800 px-4 py-2">
        <p className="text-[10px] text-slate-600">
          {agents.filter((a) => a.status === "online").length} online ·{" "}
          {agents.length} total
        </p>
      </div>
    </aside>
  );
};

export default AgentPanel;
