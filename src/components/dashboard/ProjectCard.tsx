/**
 * ProjectCard
 * ===========
 * Card component displayed in the Dashboard project grid.
 *
 * Visual hierarchy:
 * - Title + status badge (top)
 * - Description snippet
 * - Agent team avatar row
 * - Progress bar
 * - Last updated timestamp
 *
 * Design: Dark card (slate-900) with subtle border. Warm amber accents
 * for active/in-progress states. Hover lift effect.
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import type { Project, ProjectStatus } from "../../types/project";
import { formatRelativeTime } from "../../utils/formatters";

// ---------------------------------------------------------------------------
// Status Config
// ---------------------------------------------------------------------------

interface StatusStyle {
  label: string;
  bgClass: string;
  textClass: string;
  dotClass: string;
}

const STATUS_MAP: Record<ProjectStatus, StatusStyle> = {
  planning: {
    label: "Planning",
    bgClass: "bg-slate-800",
    textClass: "text-slate-400",
    dotClass: "bg-slate-500",
  },
  in_progress: {
    label: "In Progress",
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-400",
    dotClass: "bg-amber-500",
  },
  reviewing: {
    label: "Reviewing",
    bgClass: "bg-blue-500/10",
    textClass: "text-blue-400",
    dotClass: "bg-blue-500",
  },
  completed: {
    label: "Completed",
    bgClass: "bg-emerald-500/10",
    textClass: "text-emerald-400",
    dotClass: "bg-emerald-500",
  },
  failed: {
    label: "Failed",
    bgClass: "bg-red-500/10",
    textClass: "text-red-400",
    dotClass: "bg-red-500",
  },
  paused: {
    label: "Paused",
    bgClass: "bg-slate-800",
    textClass: "text-slate-400",
    dotClass: "bg-slate-500",
  },
  archived: {
    label: "Archived",
    bgClass: "bg-slate-800/50",
    textClass: "text-slate-500",
    dotClass: "bg-slate-600",
  },
};

// ---------------------------------------------------------------------------
// Agent Role Badge Colors
// ---------------------------------------------------------------------------

const ROLE_COLORS: Record<string, { bg: string; text: string }> = {
  developer: { bg: "bg-blue-900/50", text: "text-blue-400" },
  reviewer: { bg: "bg-purple-900/50", text: "text-purple-400" },
  fixer: { bg: "bg-orange-900/50", text: "text-orange-400" },
  tester: { bg: "bg-teal-900/50", text: "text-teal-400" },
  deployer: { bg: "bg-green-900/50", text: "text-green-400" },
};

const ROLE_INITIALS: Record<string, string> = {
  developer: "Dv",
  reviewer: "Rv",
  fixer: "Fx",
  tester: "Ts",
  deployer: "Dp",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ProjectCardProps {
  /** Project data to display */
  project: Project;
  /** Card animation delay index (for staggered appearance) */
  index?: number;
}

/**
 * Dashboard project card component.
 *
 * @example
 * ```tsx
 * <ProjectCard project={project} index={0} />
 * ```
 */
const ProjectCard: React.FC<ProjectCardProps> = ({ project, index = 0 }) => {
  const navigate = useNavigate();
  const statusStyle = STATUS_MAP[project.status] || STATUS_MAP.planning;

  const handleClick = () => {
    navigate(`/forge/${project.id}`);
  };

  return (
    <article
      onClick={handleClick}
      className="group cursor-pointer rounded-xl border border-slate-800 bg-slate-900 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-lg hover:shadow-black/30"
      style={{ animationDelay: `${index * 50}ms` }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`Open project: ${project.name}`}
    >
      {/* ---- Header: Name + Status ---- */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="truncate text-sm font-semibold text-slate-200 transition-colors group-hover:text-amber-400">
          {project.name}
        </h3>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle.bgClass} ${statusStyle.textClass}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${statusStyle.dotClass}`} />
          {statusStyle.label}
        </span>
      </div>

      {/* ---- Description ---- */}
      {project.description && (
        <p className="mb-4 line-clamp-2 text-xs leading-relaxed text-slate-500">
          {project.description}
        </p>
      )}

      {/* ---- Agent Team Avatars ---- */}
      {project.agentAssignments && project.agentAssignments.length > 0 && (
        <div className="mb-4 flex items-center gap-1.5">
          <span className="mr-1 text-[10px] text-slate-600">Team:</span>
          {project.agentAssignments.slice(0, 5).map((assignment, i) => {
            const role = assignment.role || "developer";
            const colors = ROLE_COLORS[role] || ROLE_COLORS.developer;
            return (
              <span
                key={i}
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-bold ${colors.bg} ${colors.text}`}
                title={role}
              >
                {ROLE_INITIALS[role] || "?"}
              </span>
            );
          })}
          {project.agentAssignments.length > 5 && (
            <span className="text-[10px] text-slate-600">
              +{project.agentAssignments.length - 5}
            </span>
          )}
        </div>
      )}

      {/* ---- Progress Bar ---- */}
      {project.progress !== undefined && (
        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[10px] text-slate-600">Progress</span>
            <span className="text-[10px] font-mono text-slate-500">
              {project.progress}%
            </span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-amber-500 transition-all duration-500"
              style={{ width: `${project.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* ---- Footer: Updated Time ---- */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-600">
          {project.updatedAt
            ? `Updated ${formatRelativeTime(project.updatedAt)}`
            : "Not modified"}
        </span>
        <span className="text-[10px] text-slate-700 opacity-0 transition-opacity group-hover:opacity-100">
          Open →
        </span>
      </div>
    </article>
  );
};

export default ProjectCard;
