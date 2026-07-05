/**
 * QuickActions
 * ============
 * Dashboard quick-access panel for common actions.
 *
 * Actions:
 * - New Project (with suggested presets)
 * - Quick Start (preconfigured pipeline templates)
 * - Import Config
 * - Documentation link
 *
 * Design: Horizontal card row with icon-led actions.
 * Each action has a subtle hover background and arrow indicator.
 */

import React, { useState } from "react";

// ---------------------------------------------------------------------------
// Inline Icons
// ---------------------------------------------------------------------------

const ActionsIcons: Record<string, React.FC<{ className?: string }>> = {
  newProject: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
        clipRule="evenodd"
      />
    </svg>
  ),
  quickStart: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
        clipRule="evenodd"
      />
    </svg>
  ),
  import: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
        clipRule="evenodd"
      />
    </svg>
  ),
  docs: ({ className = "" }) => (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
    </svg>
  ),
};

const ArrowIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
      clipRule="evenodd"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Quick Start Presets
// ---------------------------------------------------------------------------

interface QuickStartPreset {
  id: string;
  name: string;
  description: string;
  agents: string[];
  collaboration: string;
}

const PRESETS: QuickStartPreset[] = [
  {
    id: "code-review",
    name: "Code Review Pipeline",
    description: "Developer → Reviewer → Fixer for PR quality.",
    agents: ["Developer", "Reviewer", "Fixer"],
    collaboration: "Sequential",
  },
  {
    id: "full-stack",
    name: "Full-Stack Dev Team",
    description: "Build, test, and deploy a feature end-to-end.",
    agents: ["Developer", "Tester", "Reviewer", "Deployer"],
    collaboration: "Sequential",
  },
  {
    id: "committee",
    name: "Committee Review",
    description: "3+ reviewers analyze code in parallel.",
    agents: ["Reviewer", "Reviewer", "Reviewer"],
    collaboration: "Committee",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface QuickActionsProps {
  /** Callback for "New Project" action */
  onNewProject: () => void;
  /** Callback for Quick Start with a preset */
  onQuickStart: (presetId: string) => void;
  /** Callback for import */
  onImport: () => void;
}

/**
 * Dashboard quick actions panel.
 *
 * @example
 * ```tsx
 * <QuickActions
 *   onNewProject={handleNewProject}
 *   onQuickStart={handleQuickStart}
 *   onImport={handleImport}
 * />
 * ```
 */
const QuickActions: React.FC<QuickActionsProps> = ({
  onNewProject,
  onQuickStart,
  onImport,
}) => {
  const [presetsOpen, setPresetsOpen] = useState(false);

  const actions: {
    key: string;
    label: string;
    description: string;
    iconKey: string;
    onClick: () => void;
  }[] = [
    {
      key: "newProject",
      label: "New Project",
      description: "Create a project from scratch.",
      iconKey: "newProject",
      onClick: onNewProject,
    },
    {
      key: "quickStart",
      label: "Quick Start",
      description: "Use a pre-built pipeline template.",
      iconKey: "quickStart",
      onClick: () => setPresetsOpen((p) => !p),
    },
    {
      key: "import",
      label: "Import Config",
      description: "Import a project from JSON/YAML.",
      iconKey: "import",
      onClick: onImport,
    },
    {
      key: "docs",
      label: "Documentation",
      description: "Read the AgentForge docs.",
      iconKey: "docs",
      onClick: () => window.open("https://github.com", "_blank"),
    },
  ];

  return (
    <div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {actions.map((action) => {
          const Icon = ActionsIcons[action.iconKey];
          return (
            <button
              key={action.key}
              onClick={action.onClick}
              className="group flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 text-left transition-all duration-200 hover:border-slate-700 hover:bg-slate-800/50"
            >
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-400 transition-colors group-hover:bg-amber-500/10 group-hover:text-amber-400">
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <span className="text-xs font-semibold text-slate-300">
                    {action.label}
                  </span>
                  <ArrowIcon className="h-3.5 w-3.5 text-slate-600 transition-transform group-hover:translate-x-0.5 group-hover:text-slate-400" />
                </div>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {action.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* ---- Quick Start Presets Flyout ---- */}
      {presetsOpen && (
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-xs font-semibold text-slate-300">
              Pipeline Presets
            </h4>
            <button
              onClick={() => setPresetsOpen(false)}
              className="text-[10px] text-slate-600 transition-colors hover:text-slate-400"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => {
                  onQuickStart(preset.id);
                  setPresetsOpen(false);
                }}
                className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-left transition-all hover:border-amber-500/30 hover:bg-slate-800/50"
              >
                <p className="text-xs font-semibold text-slate-300">
                  {preset.name}
                </p>
                <p className="mt-1 text-[10px] leading-relaxed text-slate-500">
                  {preset.description}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-[9px] text-slate-600">
                    {preset.collaboration}
                  </span>
                  <span className="text-slate-700">·</span>
                  <span className="text-[9px] text-slate-600">
                    {preset.agents.length} agents
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QuickActions;
