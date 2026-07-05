/**
 * ProjectList
 * ===========
 * Grid layout displaying project cards with empty-state handling
 * and a floating action button for creating new projects.
 *
 * Features:
 * - Responsive grid (1/2/3 columns depending on viewport)
 * - Staggered card entrance animation
 * - Empty state illustration and guidance
 * - Floating "New Project" action button
 */

import React, { useState, useEffect } from "react";
import ProjectCard from "./ProjectCard";
import type { Project } from "../../types/project";

// ---------------------------------------------------------------------------
// Inline Icons
// ---------------------------------------------------------------------------

const PlusIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
      clipRule="evenodd"
    />
  </svg>
);

const EmptyFolderIcon: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    <path d="M12 11v4M10 13h4" opacity="0.4" />
  </svg>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ProjectListProps {
  /** List of projects to display */
  projects: Project[];
  /** Whether projects are being loaded */
  isLoading: boolean;
  /** Callback to create a new project */
  onCreateProject: () => void;
  /** Search filter query (to highlight no results) */
  searchQuery?: string;
}

/**
 * Project grid list component with create FAB.
 *
 * @example
 * ```tsx
 * <ProjectList
 *   projects={projects}
 *   isLoading={loading}
 *   onCreateProject={handleCreate}
 * />
 * ```
 */
const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  isLoading,
  onCreateProject,
  searchQuery = "",
}) => {
  const [visible, setVisible] = useState(false);

  // Staggered entrance animation
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // ---- Loading State ----
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-slate-800 bg-slate-900 p-5"
          >
            <div className="mb-3 h-4 w-2/3 rounded bg-slate-800" />
            <div className="mb-4 h-3 w-full rounded bg-slate-800" />
            <div className="mb-4 flex gap-2">
              {Array.from({ length: 3 }).map((_, j) => (
                <div key={j} className="h-5 w-5 rounded-full bg-slate-800" />
              ))}
            </div>
            <div className="h-1 w-full rounded-full bg-slate-800" />
          </div>
        ))}
      </div>
    );
  }

  // ---- Empty State ----
  if (projects.length === 0) {
    const isSearchEmpty = searchQuery.length > 0;

    return (
      <div className="flex flex-col items-center justify-center py-20">
        <EmptyFolderIcon className="mb-5 h-16 w-16 text-slate-700" />
        <h3 className="mb-2 text-sm font-semibold text-slate-400">
          {isSearchEmpty ? "No matching projects" : "No projects yet"}
        </h3>
        <p className="mb-6 max-w-xs text-center text-xs leading-relaxed text-slate-600">
          {isSearchEmpty
            ? `No projects match "${searchQuery}". Try a different search term.`
            : "Create your first project to start orchestrating AI agents as a team."}
        </p>
        {!isSearchEmpty && (
          <button
            onClick={onCreateProject}
            className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-slate-950 transition-all hover:bg-amber-400 active:scale-95"
          >
            <PlusIcon className="h-4 w-4" />
            Create Project
          </button>
        )}
      </div>
    );
  }

  // ---- Grid ----
  return (
    <>
      <div
        className={`grid grid-cols-1 gap-4 transition-all duration-500 sm:grid-cols-2 lg:grid-cols-3 ${
          visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
        }`}
      >
        {projects.map((project, i) => (
          <ProjectCard key={project.id} project={project} index={i} />
        ))}
      </div>

      {/* Floating Action Button */}
      <button
        onClick={onCreateProject}
        className="fixed bottom-16 right-6 z-20 flex h-12 w-12 items-center justify-center rounded-full bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/25 transition-all duration-200 hover:scale-110 hover:bg-amber-400 hover:shadow-xl hover:shadow-amber-500/40 active:scale-95"
        aria-label="Create new project"
      >
        <PlusIcon className="h-5 w-5" />
      </button>
    </>
  );
};

export default ProjectList;
