/**
 * AgentNode
 * =========
 * Custom ReactFlow node representing an AI Agent on the forge canvas.
 *
 * Visual elements:
 * - Role icon (distinct SVG per role: developer/reviewer/fixer/tester/deployer)
 * - Agent name label
 * - Status indicator dot (online=green, offline=gray, busy=amber-pulse, error=red-flash)
 * - Source/input handle (bottom: output connection)
 * - Target handle (top: input connection)
 * - Selection highlight (amber border)
 * - Role-colored accent line at top
 *
 * Design: Dark card (slate-900) with subtle shadow. Compact but readable.
 */

import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import type { AgentNodeData } from "./ForgeEditor";

// ---------------------------------------------------------------------------
// Role Icons (inline SVG)
// ---------------------------------------------------------------------------

const RoleIcon: React.FC<{ role: string }> = ({ role }) => {
  switch (role) {
    case "developer":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
          <path d="M12 4l-4 16" opacity="0.4" />
        </svg>
      );
    case "reviewer":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      );
    case "fixer":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
        </svg>
      );
    case "tester":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
        </svg>
      );
    case "deployer":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      );
  }
};

// ---------------------------------------------------------------------------
// Status Indicator
// ---------------------------------------------------------------------------

const StatusDot: React.FC<{ status: string }> = ({ status }) => {
  const base = "inline-block h-2 w-2 rounded-full";

  switch (status) {
    case "online":
      return (
        <span className="relative flex h-2 w-2">
          <span className={`${base} absolute animate-ping bg-emerald-400 opacity-75`} />
          <span className={`${base} relative bg-emerald-500`} />
        </span>
      );
    case "busy":
      return (
        <span className="relative flex h-2 w-2">
          <span className={`${base} absolute animate-ping bg-amber-400 opacity-75`} />
          <span className={`${base} relative bg-amber-500`} />
        </span>
      );
    case "error":
      return <span className={`${base} animate-pulse bg-red-500`} />;
    default:
      return <span className={`${base} bg-slate-600`} />;
  }
};

// ---------------------------------------------------------------------------
// Role accent colors
// ---------------------------------------------------------------------------

const ROLE_ACCENT: Record<string, string> = {
  developer: "bg-blue-500",
  reviewer: "bg-purple-500",
  fixer: "bg-orange-500",
  tester: "bg-teal-500",
  deployer: "bg-emerald-500",
};

const ROLE_TEXT: Record<string, string> = {
  developer: "text-blue-400",
  reviewer: "text-purple-400",
  fixer: "text-orange-400",
  tester: "text-teal-400",
  deployer: "text-emerald-400",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Custom ReactFlow agent node.
 */
const AgentNode: React.FC<NodeProps<AgentNodeData>> = ({ data, selected }) => {
  const accent = ROLE_ACCENT[data.role] || "bg-slate-500";
  const textColor = ROLE_TEXT[data.role] || "text-slate-400";

  return (
    <div
      className={`relative min-w-[180px] overflow-hidden rounded-xl border bg-slate-900 shadow-lg shadow-black/30 transition-all duration-200 ${
        selected
          ? "border-amber-500/60 shadow-amber-500/10 ring-1 ring-amber-500/30"
          : "border-slate-800 hover:border-slate-700"
      }`}
    >
      {/* ---- Accent Top Bar ---- */}
      <div className={`h-1 w-full ${accent}`} />

      {/* ---- Node Body ---- */}
      <div className="px-4 py-3">
        {/* Header: Icon + Name + Status */}
        <div className="mb-2 flex items-center gap-2.5">
          <span className={`${textColor}`}>
            <RoleIcon role={data.role} />
          </span>
          <span className="flex-1 truncate text-xs font-semibold text-slate-200">
            {data.agentName}
          </span>
          <StatusDot status={data.status} />
        </div>

        {/* Role label */}
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-slate-800 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-slate-500">
            {data.role}
          </span>
          {data.stageIndex !== undefined && (
            <span className="text-[9px] text-slate-600">
              Stage {data.stageIndex + 1}
            </span>
          )}
        </div>
      </div>

      {/* ---- Handles ---- */}
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-slate-700 !bg-slate-900 transition-colors hover:!border-amber-500"
        style={{ top: -5 }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-slate-700 !bg-slate-900 transition-colors hover:!border-amber-500"
        style={{ bottom: -5 }}
      />
    </div>
  );
};

export default memo(AgentNode);
