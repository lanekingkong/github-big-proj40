/**
 * PipelinePanel
 * =============
 * Right sidebar panel for configuring the collaboration pipeline.
 *
 * Sections:
 * 1. Collaboration Mode Selection — 4 radio-card options:
 *    - Sequential     (chain: A → B → C)
 *    - Parallel       (all agents work simultaneously)
 *    - Review Loop    (reviewer validates, loops back if needed)
 *    - Committee      (majority vote)
 *
 * 2. Preset Templates — quick-start pipeline templates:
 *    - Code Review (developer → reviewer → deployer)
 *    - Bug Fix (tester → developer → reviewer → deployer)
 *    - R&D (developer parallel → reviewer → deployer)
 *
 * 3. Stage Configuration — add/remove/sort pipeline stages,
 *    each stage specifies a required Agent role.
 *
 * Design: Dark panel (slate-900), amber accent on active selection.
 */

import React, { useState, useCallback } from "react";
import type { CollaborationMode, StageConfig } from "./ForgeEditor";

// ---------------------------------------------------------------------------
// Mode Card Config
// ---------------------------------------------------------------------------

interface ModeOption {
  value: CollaborationMode;
  label: string;
  description: string;
  icon: string; // emoji or short symbol
}

const MODE_OPTIONS: ModeOption[] = [
  {
    value: "sequential",
    label: "Sequential",
    description: "Agents execute in order, each passing output to the next.",
    icon: "→",
  },
  {
    value: "parallel",
    label: "Parallel",
    description: "All agents work simultaneously on independent tasks.",
    icon: "⇉",
  },
  {
    value: "review_loop",
    label: "Review Loop",
    description: "Reviewer validates output; loops back to developer on failure.",
    icon: "↻",
  },
  {
    value: "committee",
    label: "Committee",
    description: "Multiple reviewers vote; majority decides the final output.",
    icon: "⊕",
  },
];

// ---------------------------------------------------------------------------
// Preset Templates
// ---------------------------------------------------------------------------

interface PresetTemplate {
  name: string;
  mode: CollaborationMode;
  stages: Omit<StageConfig, "id">[];
}

const PRESETS: PresetTemplate[] = [
  {
    name: "Code Review",
    mode: "sequential",
    stages: [
      { name: "Develop", requiredRole: "developer", description: "Write initial code" },
      { name: "Review", requiredRole: "reviewer", description: "Review code changes" },
      { name: "Deploy", requiredRole: "deployer", description: "Deploy to staging" },
    ],
  },
  {
    name: "Bug Fix",
    mode: "sequential",
    stages: [
      { name: "Test", requiredRole: "tester", description: "Identify and report bugs" },
      { name: "Fix", requiredRole: "fixer", description: "Resolve reported issues" },
      { name: "Review", requiredRole: "reviewer", description: "Verify fixes" },
      { name: "Deploy", requiredRole: "deployer", description: "Ship the fix" },
    ],
  },
  {
    name: "R&D Sprint",
    mode: "parallel",
    stages: [
      { name: "Research", requiredRole: "developer", description: "Explore solutions" },
      { name: "Prototype", requiredRole: "developer", description: "Build proof-of-concept" },
      { name: "Review", requiredRole: "reviewer", description: "Evaluate prototypes" },
      { name: "Deploy", requiredRole: "deployer", description: "Push to production" },
    ],
  },
];

// ---------------------------------------------------------------------------
// Available Roles (for stage role selector)
// ---------------------------------------------------------------------------

const AVAILABLE_ROLES = [
  { value: "developer", label: "Developer" },
  { value: "reviewer", label: "Reviewer" },
  { value: "fixer", label: "Fixer" },
  { value: "tester", label: "Tester" },
  { value: "deployer", label: "Deployer" },
  { value: "planner", label: "Planner" },
];

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const PlusIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
  </svg>
);

const TrashIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.18-2.365.335a.75.75 0 10.23 1.482l.149-.022.841 10.627A1.75 1.75 0 006.592 18h6.816a1.75 1.75 0 001.737-1.385l.841-10.627.149.022a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193v-.443A2.75 2.75 0 0011.25 1h-2.5zM10 6a.75.75 0 01.75.75v7.5a.75.75 0 01-1.5 0v-7.5A.75.75 0 0110 6zm-2.25.75a.75.75 0 011.5 0v7.5a.75.75 0 01-1.5 0v-7.5z" clipRule="evenodd" />
  </svg>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface PipelinePanelProps {
  mode: CollaborationMode;
  onModeChange: (mode: CollaborationMode) => void;
  stages: StageConfig[];
  onStagesChange: (stages: StageConfig[]) => void;
}

/**
 * Right-side pipeline configuration panel.
 */
const PipelinePanel: React.FC<PipelinePanelProps> = ({
  mode,
  onModeChange,
  stages,
  onStagesChange,
}) => {
  const [newStageName, setNewStageName] = useState("");
  const [newStageRole, setNewStageRole] = useState("developer");
  const [expandedSection, setExpandedSection] = useState<"mode" | "presets" | "stages">("stages");

  // ---- Stage Management ----
  const addStage = useCallback(() => {
    if (!newStageName.trim()) return;
    const stage: StageConfig = {
      id: `stage-${Date.now()}`,
      name: newStageName.trim(),
      requiredRole: newStageRole,
    };
    onStagesChange([...stages, stage]);
    setNewStageName("");
    setNewStageRole("developer");
  }, [newStageName, newStageRole, stages, onStagesChange]);

  const removeStage = useCallback(
    (stageId: string) => {
      onStagesChange(stages.filter((s) => s.id !== stageId));
    },
    [stages, onStagesChange]
  );

  const moveStage = useCallback(
    (index: number, dir: -1 | 1) => {
      const target = index + dir;
      if (target < 0 || target >= stages.length) return;
      const next = [...stages];
      [next[index], next[target]] = [next[target], next[index]];
      onStagesChange(next);
    },
    [stages, onStagesChange]
  );

  // ---- Apply Preset ----
  const applyPreset = useCallback(
    (preset: PresetTemplate) => {
      onModeChange(preset.mode);
      onStagesChange(
        preset.stages.map((s, i) => ({
          ...s,
          id: `stage-preset-${Date.now()}-${i}`,
        }))
      );
    },
    [onModeChange, onStagesChange]
  );

  return (
    <aside className="flex w-72 shrink-0 flex-col border-l border-slate-800 bg-slate-900">
      {/* ---- Header ---- */}
      <div className="border-b border-slate-800 px-4 py-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Pipeline
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* ======== Section: Mode ======== */}
        <div className="border-b border-slate-800/50">
          <button
            onClick={() => setExpandedSection(expandedSection === "mode" ? "" : "mode")}
            className="flex w-full items-center px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50"
          >
            <span className="flex-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Collaboration Mode
            </span>
            <svg
              className={`h-3 w-3 text-slate-600 transition-transform ${expandedSection === "mode" ? "rotate-180" : ""}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {(expandedSection === "mode") && (
            <div className="space-y-1.5 px-3 pb-3">
              {MODE_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className={`block cursor-pointer rounded-lg border px-3 py-2.5 transition-all duration-150 ${
                    mode === opt.value
                      ? "border-amber-500/40 bg-amber-500/5 ring-1 ring-amber-500/10"
                      : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
                  }`}
                >
                  <input
                    type="radio"
                    name="collaboration-mode"
                    value={opt.value}
                    checked={mode === opt.value}
                    onChange={() => onModeChange(opt.value)}
                    className="peer sr-only"
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-amber-400">{opt.icon}</span>
                    <span className={`text-[11px] font-medium ${
                      mode === opt.value ? "text-amber-300" : "text-slate-300"
                    }`}>
                      {opt.label}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[9px] leading-relaxed text-slate-600">
                    {opt.description}
                  </p>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* ======== Section: Presets ======== */}
        <div className="border-b border-slate-800/50">
          <button
            onClick={() => setExpandedSection(expandedSection === "presets" ? "" : "presets")}
            className="flex w-full items-center px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50"
          >
            <span className="flex-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Templates
            </span>
            <svg
              className={`h-3 w-3 text-slate-600 transition-transform ${expandedSection === "presets" ? "rotate-180" : ""}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {(expandedSection === "presets") && (
            <div className="space-y-1.5 px-3 pb-3">
              {PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => applyPreset(preset)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-left transition-all hover:border-slate-700 hover:bg-slate-800/50"
                >
                  <p className="text-[11px] font-medium text-slate-300">{preset.name}</p>
                  <p className="mt-0.5 text-[9px] text-slate-600">
                    {preset.stages.map((s) => s.name).join(" → ")}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ======== Section: Stages ======== */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === "stages" ? "" : "stages")}
            className="flex w-full items-center px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50"
          >
            <span className="flex-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Stages
              {stages.length > 0 && (
                <span className="ml-1.5 text-amber-400">{stages.length}</span>
              )}
            </span>
            <svg
              className={`h-3 w-3 text-slate-600 transition-transform ${expandedSection === "stages" ? "rotate-180" : ""}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {(expandedSection === "stages") && (
            <div className="px-3 pb-3 space-y-1.5">
              {/* Existing stages */}
              {stages.map((stage, idx) => (
                <div
                  key={stage.id}
                  className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/50 px-2.5 py-2"
                >
                  {/* Order badge */}
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-800 text-[9px] font-mono tabular-nums text-slate-500">
                    {idx + 1}
                  </span>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[11px] font-medium text-slate-300">
                      {stage.name}
                    </p>
                    <p className="text-[9px] text-slate-600">{stage.requiredRole}</p>
                  </div>

                  {/* Move up/down */}
                  <div className="flex flex-col -space-y-1">
                    <button
                      onClick={() => moveStage(idx, -1)}
                      disabled={idx === 0}
                      className="text-slate-600 hover:text-slate-400 disabled:opacity-30"
                      aria-label="Move up"
                    >
                      <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.832 6.29 12.77a.75.75 0 11-1.08-1.04l4.25-4.5a.75.75 0 011.08 0l4.25 4.5a.75.75 0 01-.02 1.06z" clipRule="evenodd" />
                      </svg>
                    </button>
                    <button
                      onClick={() => moveStage(idx, 1)}
                      disabled={idx === stages.length - 1}
                      className="text-slate-600 hover:text-slate-400 disabled:opacity-30"
                      aria-label="Move down"
                    >
                      <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>

                  {/* Delete */}
                  <button
                    onClick={() => removeStage(stage.id)}
                    className="text-slate-600 hover:text-red-400"
                    aria-label="Remove stage"
                  >
                    <TrashIcon className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}

              {/* Empty state */}
              {stages.length === 0 && (
                <p className="py-3 text-center text-[10px] text-slate-700">
                  Add stages below or select a template
                </p>
              )}

              {/* Add new stage form */}
              <div className="space-y-2 rounded-lg border border-dashed border-slate-800 bg-slate-950/30 p-2.5">
                <input
                  type="text"
                  value={newStageName}
                  onChange={(e) => setNewStageName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addStage()}
                  placeholder="Stage name..."
                  className="w-full rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[11px] text-slate-300 placeholder:text-slate-600 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/20"
                />
                <div className="flex items-center gap-2">
                  <select
                    value={newStageRole}
                    onChange={(e) => setNewStageRole(e.target.value)}
                    className="flex-1 rounded-md border border-slate-800 bg-slate-950 px-2 py-1.5 text-[11px] text-slate-400 focus:border-amber-500/50 focus:outline-none"
                  >
                    {AVAILABLE_ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={addStage}
                    disabled={!newStageName.trim()}
                    className="flex shrink-0 items-center gap-1 rounded-md bg-amber-500/10 px-2.5 py-1.5 text-[10px] font-medium text-amber-400 transition-colors hover:bg-amber-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <PlusIcon className="h-3 w-3" />
                    Add
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default PipelinePanel;
