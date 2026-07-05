/**
 * ForgeEditor
 * ===========
 * Core visual orchestration editor — the heart of AgentForge.
 *
 * Three-column layout:
 *   ┌──────────────┬──────────────────────┬──────────────┐
 *   │  AgentPanel  │     ForgeCanvas      │ PipelinePanel│
 *   │  (w-64)      │     (flex-1)         │  (w-72)      │
 *   └──────────────┴──────────────────────┴──────────────┘
 *
 * Keyboard shortcuts:
 * - Ctrl+S      : Save project
 * - Ctrl+Z      : Undo
 * - Ctrl+Shift+Z: Redo
 * - Delete      : Delete selected nodes/edges
 *
 * The editor is the primary interface where users drag agents onto a
 * ReactFlow canvas and wire them together into collaboration pipelines.
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlowProvider,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type Connection,
} from "reactflow";
import AgentPanel from "./AgentPanel";
import ForgeCanvas from "./ForgeCanvas";
import PipelinePanel from "./PipelinePanel";
import ForgeToolbar from "./ForgeToolbar";
import RunDialog from "./RunDialog";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Data attached to each agent node on the canvas */
export interface AgentNodeData {
  agentId: string;
  agentName: string;
  role: string;
  status: "online" | "offline" | "busy" | "error";
  instruction?: string;
  /** Stage index within the pipeline (0-based) */
  stageIndex?: number;
}

/** Collaboration mode */
export type CollaborationMode =
  | "sequential"
  | "parallel"
  | "review_loop"
  | "committee";

/** A pipeline stage configuration */
export interface StageConfig {
  id: string;
  name: string;
  requiredRole: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// Mock Data (would come from stores in production)
// ---------------------------------------------------------------------------

const MOCK_AGENTS = [
  { id: "agent-1", name: "Dev GPT-4", role: "developer", status: "online" as const },
  { id: "agent-2", name: "Dev Claude", role: "developer", status: "online" as const },
  { id: "agent-3", name: "Reviewer GPT", role: "reviewer", status: "online" as const },
  { id: "agent-4", name: "Fixer Bot", role: "fixer", status: "busy" as const },
  { id: "agent-5", name: "Test Runner", role: "tester", status: "offline" as const },
  { id: "agent-6", name: "Deploy Bot", role: "deployer", status: "online" as const },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ForgeEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [nodes, setNodes] = useState<Node<AgentNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [mode, setMode] = useState<CollaborationMode>("sequential");
  const [stages, setStages] = useState<StageConfig[]>([]);
  const [projectName, setProjectName] = useState("Untitled Project");
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // ---- Node/Edge Change Handlers ----
  const onNodesChange: OnNodesChange = useCallback((changes) => {
    setNodes((nds) => {
      // Minimal implementation — real app would use applyNodeChanges
      const next = [...nds];
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          const idx = next.findIndex((n) => n.id === change.id);
          if (idx !== -1) {
            next[idx] = { ...next[idx], position: change.position };
          }
        }
        if (change.type === "remove") {
          return next.filter((n) => n.id !== change.id);
        }
      }
      return next;
    });
  }, []);

  const onEdgesChange: OnEdgesChange = useCallback((changes) => {
    setEdges((eds) => {
      const next = [...eds];
      for (const change of changes) {
        if (change.type === "remove") {
          return next.filter((e) => e.id !== change.id);
        }
      }
      return next;
    });
  }, []);

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      // Prevent duplicate edges and self-loops
      const exists = edges.some(
        (e) =>
          e.source === connection.source &&
          e.target === connection.target
      );
      if (exists || connection.source === connection.target) return;

      const newEdge: Edge = {
        id: `e-${connection.source}-${connection.target}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle || undefined,
        targetHandle: connection.targetHandle || undefined,
        type: "animated",
        animated: true,
      };
      setEdges((eds) => [...eds, newEdge]);
    },
    [edges]
  );

  // ---- Drag & Drop Agent onto Canvas ----
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const agentData = event.dataTransfer.getData("application/agentforge-agent");
      if (!agentData) return;

      const agent = JSON.parse(agentData) as {
        id: string;
        name: string;
        role: string;
        status: "online" | "offline" | "busy" | "error";
      };

      // Calculate drop position relative to the canvas
      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      const position = bounds
        ? {
            x: event.clientX - bounds.left - 80,
            y: event.clientY - bounds.top - 30,
          }
        : { x: event.clientX - 320, y: event.clientY - 120 };

      const newNode: Node<AgentNodeData> = {
        id: `node-${Date.now()}`,
        type: "agentNode",
        position,
        data: {
          agentId: agent.id,
          agentName: agent.name,
          role: agent.role,
          status: agent.status,
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    []
  );

  // ---- Keyboard Shortcuts ----
  useEffect(() => {
    const handler = (e: globalThis.KeyboardEvent) => {
      // Ctrl+S — Save
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
      // Delete — Remove selection
      if (e.key === "Delete" || e.key === "Backspace") {
        // Remove selected nodes/edges via forgestore would be here
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [nodes, edges, stages, mode]);

  // ---- Save ----
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    // Simulate save
    await new Promise((r) => setTimeout(r, 600));
    setIsSaving(false);
  }, []);

  // ---- Auto Layout (dagre) ----
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;
    // Simple grid layout fallback when dagre is not available
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const spacing = 200;
    const positioned = nodes.map((node, i) => ({
      ...node,
      position: {
        x: 100 + (i % cols) * spacing,
        y: 80 + Math.floor(i / cols) * 160,
      },
    }));
    setNodes(positioned);
  }, [nodes]);

  // ---- Clear Canvas ----
  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
  }, []);

  // ---- Export / Import ----
  const handleExport = useCallback(() => {
    const config = {
      projectName,
      mode,
      stages,
      nodes: nodes.map((n) => ({
        id: n.id,
        position: n.position,
        data: n.data,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
      })),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${projectName.replace(/\s+/g, "_")}.agentforge.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [projectName, mode, stages, nodes, edges]);

  const handleImport = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const text = await file.text();
      try {
        const config = JSON.parse(text);
        setProjectName(config.projectName || "Imported Project");
        setMode(config.mode || "sequential");
        setStages(config.stages || []);
        setNodes(
          (config.nodes || []).map((n: Node<AgentNodeData>) => ({
            ...n,
            type: "agentNode",
          }))
        );
        setEdges(
          (config.edges || []).map((e: Edge) => ({
            ...e,
            type: "animated",
            animated: true,
          }))
        );
      } catch {
        // Silently fail on invalid JSON
      }
    };
    input.click();
  }, []);

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col overflow-hidden bg-slate-950">
        {/* ---- Toolbar ---- */}
        <ForgeToolbar
          onSave={handleSave}
          onRun={() => setRunDialogOpen(true)}
          onUndo={() => {}}
          onRedo={() => {}}
          onAutoLayout={handleAutoLayout}
          onClear={handleClear}
          onExport={handleExport}
          onImport={handleImport}
          isSaving={isSaving}
          canUndo={false}
          canRedo={false}
        />

        {/* ---- Three-column body ---- */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Agent Panel */}
          <AgentPanel agents={MOCK_AGENTS} />

          {/* Center: Canvas */}
          <div
            ref={reactFlowWrapper}
            className="relative flex-1"
            onDragOver={onDragOver}
            onDrop={onDrop}
          >
            <ForgeCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              mode={mode}
            />
          </div>

          {/* Right: Pipeline Panel */}
          <PipelinePanel
            mode={mode}
            onModeChange={setMode}
            stages={stages}
            onStagesChange={setStages}
          />
        </div>

        {/* ---- Run Dialog ---- */}
        <RunDialog
          isOpen={runDialogOpen}
          onClose={() => setRunDialogOpen(false)}
          projectName={projectName}
          mode={mode}
          stages={stages}
          agentCount={nodes.length}
          onConfirm={() => {
            setRunDialogOpen(false);
            navigate(`/monitor/${id || "new"}`);
          }}
        />
      </div>
    </ReactFlowProvider>
  );
};

export default ForgeEditor;
