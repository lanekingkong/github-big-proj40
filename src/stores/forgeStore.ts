/**
 * Forge Editor State Store
 * ========================
 * Zustand store for the visual Agent pipeline editor.
 *
 * Manages:
 * - ReactFlow nodes and edges
 * - Collaboration mode for the pipeline
 * - Pipeline execution state
 * - Undo/redo history
 * - Node selection and editing
 *
 * This store is the single source of truth for the Forge Editor canvas.
 */

import { create } from "zustand";
import {
  applyNodeChanges,
  applyEdgeChanges,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from "reactflow";
import type {
  ForgeNode,
  ForgeEdge,
  ForgeNodeData,
  ForgeEdgeData,
  ForgeCanvasState,
  ExecutionState,
  CollaborationMode,
} from "../types/forge";
import { AgentRole, AgentStatus } from "../types/agent";
import type { PipelineConfig } from "../types/project";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum undo history depth */
const MAX_HISTORY = 50;

/** Auto-generated node ID counter */
let nodeIdCounter = 0;

function generateNodeId(): string {
  nodeIdCounter += 1;
  return `forge-node-${nodeIdCounter}`;
}

function generateEdgeId(): string {
  return `forge-edge-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// Default Node Data
// ---------------------------------------------------------------------------

const DEFAULT_NODE_DATA: Record<AgentRole, Partial<ForgeNodeData>> = {
  [AgentRole.Developer]: {
    role: AgentRole.Developer,
    label: "Developer",
    instruction: "Implement the requested feature or fix.",
  },
  [AgentRole.Reviewer]: {
    role: AgentRole.Reviewer,
    label: "Reviewer",
    instruction: "Review the code for correctness and best practices.",
  },
  [AgentRole.Fixer]: {
    role: AgentRole.Fixer,
    label: "Fixer",
    instruction: "Fix identified issues in the codebase.",
  },
  [AgentRole.Tester]: {
    role: AgentRole.Tester,
    label: "Tester",
    instruction: "Write and run tests for the changes.",
  },
  [AgentRole.Deployer]: {
    role: AgentRole.Deployer,
    label: "Deployer",
    instruction: "Deploy the changes to the target environment.",
  },
  [AgentRole.Generalist]: {
    role: AgentRole.Generalist,
    label: "Generalist",
    instruction: "Handle the assigned task.",
  },
};

// ---------------------------------------------------------------------------
// Store State
// ---------------------------------------------------------------------------

interface ForgeState {
  // ---- Canvas Data ----
  nodes: ForgeNode[];
  edges: ForgeEdge[];
  collaborationMode: CollaborationMode;
  pipelineName: string;

  // ---- UI State ----
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  isDirty: boolean;

  // ---- Execution State ----
  execution: ExecutionState;

  // ---- Undo/Redo ----
  undoStack: Pick<ForgeCanvasState, "nodes" | "edges">[];
  redoStack: Pick<ForgeCanvasState, "nodes" | "edges">[];

  // ---- Actions: Node Management ----
  /** Handle ReactFlow onNodesChange events */
  onNodesChange: (changes: NodeChange[]) => void;

  /** Handle ReactFlow onEdgesChange events */
  onEdgesChange: (changes: EdgeChange[]) => void;

  /** Handle ReactFlow onConnect event */
  onConnect: (connection: Connection) => void;

  /** Add a new agent node to the canvas at the given position */
  addNode: (role: AgentRole, position: { x: number; y: number }) => void;

  /** Delete the selected node and its connected edges */
  deleteSelectedNode: () => void;

  /** Delete the selected edge */
  deleteSelectedEdge: () => void;

  /** Update node data by ID */
  updateNodeData: (nodeId: string, data: Partial<ForgeNodeData>) => void;

  /** Update edge data by ID */
  updateEdgeData: (edgeId: string, data: Partial<ForgeEdgeData>) => void;

  // ---- Actions: Selection ----
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;

  // ---- Actions: Collaboration Mode ----
  setCollaborationMode: (mode: CollaborationMode) => void;

  // ---- Actions: Pipeline Name ----
  setPipelineName: (name: string) => void;

  // ---- Actions: Execution ----
  /** Set the overall execution state */
  setExecutionState: (state: Partial<ExecutionState>) => void;

  /** Update execution status/progress for a specific node */
  updateNodeExecution: (
    nodeId: string,
    updates: { status?: AgentStatus; progress?: number; error?: string | null }
  ) => void;

  /** Start pipeline execution */
  startExecution: () => void;

  /** Stop/cancel pipeline execution */
  stopExecution: () => void;

  // ---- Actions: Undo/Redo ----
  undo: () => void;
  redo: () => void;

  // ---- Actions: Canvas I/O ----
  /** Export canvas state to a serializable object */
  exportCanvas: () => ForgeCanvasState;

  /** Import canvas state from a serialized object */
  importCanvas: (state: ForgeCanvasState) => void;

  /** Clear the entire canvas */
  clearCanvas: () => void;

  /** Mark canvas as saved (clears isDirty) */
  markSaved: () => void;

  /** Convert canvas to PipelineConfig for the backend */
  toPipelineConfig: () => PipelineConfig;
}

// ---------------------------------------------------------------------------
// Store Implementation
// ---------------------------------------------------------------------------

/**
 * Zustand store hook for the Forge Editor.
 */
export const useForgeStore = create<ForgeState>((set, get) => ({
  // ---- Initial State ----
  nodes: [],
  edges: [],
  collaborationMode: "sequential" as CollaborationMode,
  pipelineName: "Untitled Pipeline",
  selectedNodeId: null,
  selectedEdgeId: null,
  isDirty: false,
  execution: {
    isRunning: false,
    runId: null,
    startedAt: null,
    overallProgress: 0,
    nodeStatus: {},
    nodeProgress: {},
    logs: [],
  },
  undoStack: [],
  redoStack: [],

  // ---- Snapshots for Undo ----

  /** Push current state to undo stack before mutation */
  pushUndo: (
    set: (fn: (s: ForgeState) => Partial<ForgeState>) => void,
    get: () => ForgeState
  ) => {
    const { nodes, edges } = get();
    set((s) => ({
      undoStack: [
        ...s.undoStack.slice(-MAX_HISTORY + 1),
        { nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) },
      ],
      redoStack: [],
    }));
  },

  // ---- Node Changes ----
  onNodesChange: (changes: NodeChange[]) => {
    set((state) => {
      // Push undo before structural changes
      const isStructural = changes.some(
        (c) => c.type === "remove" || c.type === "add"
      );
      if (isStructural) {
        state.undoStack = [
          ...state.undoStack.slice(-MAX_HISTORY + 1),
          {
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
          },
        ];
        state.redoStack = [];
      }
      return {
        nodes: applyNodeChanges(changes, state.nodes) as ForgeNode[],
        isDirty: true,
      };
    });
  },

  // ---- Edge Changes ----
  onEdgesChange: (changes: EdgeChange[]) => {
    set((state) => {
      const isStructural = changes.some(
        (c) => c.type === "remove" || c.type === "add"
      );
      if (isStructural) {
        state.undoStack = [
          ...state.undoStack.slice(-MAX_HISTORY + 1),
          {
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
          },
        ];
        state.redoStack = [];
      }
      return {
        edges: applyEdgeChanges(changes, state.edges) as ForgeEdge[],
        isDirty: true,
      };
    });
  },

  // ---- Connect ----
  onConnect: (connection: Connection) => {
    if (!connection.source || !connection.target) return;
    set((state) => {
      state.undoStack = [
        ...state.undoStack.slice(-MAX_HISTORY + 1),
        {
          nodes: JSON.parse(JSON.stringify(state.nodes)),
          edges: JSON.parse(JSON.stringify(state.edges)),
        },
      ];
      state.redoStack = [];
      const newEdge: ForgeEdge = {
        id: generateEdgeId(),
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle ?? undefined,
        targetHandle: connection.targetHandle ?? undefined,
        type: "smoothstep",
        animated: true,
        data: {
          mode: state.collaborationMode,
          onSuccess: true,
          onFailure: false,
          maxRetries: 3,
          timeout: 300,
        },
      };
      return {
        edges: [...state.edges, newEdge],
        isDirty: true,
      };
    });
  },

  // ---- Add Node ----
  addNode: (role: AgentRole, position: { x: number; y: number }) => {
    set((state) => {
      state.undoStack = [
        ...state.undoStack.slice(-MAX_HISTORY + 1),
        {
          nodes: JSON.parse(JSON.stringify(state.nodes)),
          edges: JSON.parse(JSON.stringify(state.edges)),
        },
      ];
      state.redoStack = [];
      const defaults = DEFAULT_NODE_DATA[role];
      const newNode: ForgeNode = {
        id: generateNodeId(),
        type: "agentNode",
        position,
        data: {
          label: defaults.label!,
          role: defaults.role!,
          assignedAgentId: null,
          agentStatus: AgentStatus.Idle,
          instruction: defaults.instruction!,
          stageConfig: {},
          isExecuting: false,
          progress: null,
          error: null,
        },
      };
      return {
        nodes: [...state.nodes, newNode],
        selectedNodeId: newNode.id,
        isDirty: true,
      };
    });
  },

  // ---- Delete Selected ----
  deleteSelectedNode: () => {
    const { selectedNodeId } = get();
    if (!selectedNodeId) return;
    set((state) => {
      state.undoStack = [
        ...state.undoStack.slice(-MAX_HISTORY + 1),
        {
          nodes: JSON.parse(JSON.stringify(state.nodes)),
          edges: JSON.parse(JSON.stringify(state.edges)),
        },
      ];
      state.redoStack = [];
      return {
        nodes: state.nodes.filter((n) => n.id !== selectedNodeId),
        edges: state.edges.filter(
          (e) => e.source !== selectedNodeId && e.target !== selectedNodeId
        ),
        selectedNodeId: null,
        isDirty: true,
      };
    });
  },

  deleteSelectedEdge: () => {
    const { selectedEdgeId } = get();
    if (!selectedEdgeId) return;
    set((state) => {
      state.undoStack = [
        ...state.undoStack.slice(-MAX_HISTORY + 1),
        {
          nodes: JSON.parse(JSON.stringify(state.nodes)),
          edges: JSON.parse(JSON.stringify(state.edges)),
        },
      ];
      state.redoStack = [];
      return {
        edges: state.edges.filter((e) => e.id !== selectedEdgeId),
        selectedEdgeId: null,
        isDirty: true,
      };
    });
  },

  // ---- Update Data ----
  updateNodeData: (nodeId: string, data: Partial<ForgeNodeData>) => {
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, ...data } }
          : n
      ),
      isDirty: true,
    }));
  },

  updateEdgeData: (edgeId: string, data: Partial<ForgeEdgeData>) => {
    set((state) => ({
      edges: state.edges.map((e) =>
        e.id === edgeId
          ? { ...e, data: { ...e.data, ...data } }
          : e
      ),
      isDirty: true,
    }));
  },

  // ---- Selection ----
  selectNode: (nodeId: string | null) =>
    set({ selectedNodeId: nodeId, selectedEdgeId: null }),
  selectEdge: (edgeId: string | null) =>
    set({ selectedEdgeId: edgeId, selectedNodeId: null }),

  // ---- Collaboration Mode ----
  setCollaborationMode: (mode: CollaborationMode) =>
    set({ collaborationMode: mode, isDirty: true }),

  // ---- Pipeline Name ----
  setPipelineName: (name: string) =>
    set({ pipelineName: name, isDirty: true }),

  // ---- Execution ----
  setExecutionState: (partial: Partial<ExecutionState>) =>
    set((state) => ({
      execution: { ...state.execution, ...partial },
    })),

  updateNodeExecution: (nodeId, updates) =>
    set((state) => {
      const nodeStatus = { ...state.execution.nodeStatus };
      const nodeProgress = { ...state.execution.nodeProgress };
      if (updates.status !== undefined) nodeStatus[nodeId] = updates.status;
      if (updates.progress !== undefined) nodeProgress[nodeId] = updates.progress;
      return {
        execution: {
          ...state.execution,
          nodeStatus,
          nodeProgress,
        },
        nodes: state.nodes.map((n) =>
          n.id === nodeId
            ? {
                ...n,
                data: {
                  ...n.data,
                  agentStatus: updates.status ?? n.data.agentStatus,
                  progress: updates.progress ?? n.data.progress,
                  error: updates.error ?? n.data.error,
                  isExecuting:
                    updates.status === AgentStatus.Busy ||
                    updates.status === AgentStatus.Initializing,
                },
              }
            : n
        ),
      };
    }),

  startExecution: () =>
    set((state) => ({
      execution: {
        isRunning: true,
        runId: `run-${Date.now()}`,
        startedAt: new Date().toISOString(),
        overallProgress: 0,
        nodeStatus: {},
        nodeProgress: {},
        logs: [],
      },
    })),

  stopExecution: () =>
    set((state) => ({
      execution: {
        ...state.execution,
        isRunning: false,
      },
    })),

  // ---- Undo/Redo ----
  undo: () =>
    set((state) => {
      if (state.undoStack.length === 0) return state;
      const previous = state.undoStack[state.undoStack.length - 1];
      return {
        nodes: previous.nodes,
        edges: previous.edges,
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [
          ...state.redoStack,
          {
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
          },
        ],
        isDirty: true,
      };
    }),

  redo: () =>
    set((state) => {
      if (state.redoStack.length === 0) return state;
      const next = state.redoStack[state.redoStack.length - 1];
      return {
        nodes: next.nodes,
        edges: next.edges,
        redoStack: state.redoStack.slice(0, -1),
        undoStack: [
          ...state.undoStack,
          {
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
          },
        ],
        isDirty: true,
      };
    }),

  // ---- Canvas I/O ----
  exportCanvas: (): ForgeCanvasState => ({
    nodes: get().nodes,
    edges: get().edges,
    viewport: { x: 0, y: 0, zoom: 1 },
    collaborationMode: get().collaborationMode,
    pipelineName: get().pipelineName,
    lastSaved: new Date().toISOString(),
  }),

  importCanvas: (canvas: ForgeCanvasState) =>
    set({
      nodes: canvas.nodes,
      edges: canvas.edges,
      collaborationMode: canvas.collaborationMode,
      pipelineName: canvas.pipelineName,
      undoStack: [],
      redoStack: [],
      isDirty: false,
    }),

  clearCanvas: () =>
    set({
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      undoStack: [],
      redoStack: [],
      isDirty: false,
    }),

  markSaved: () => set({ isDirty: false }),

  // ---- Convert to PipelineConfig ----
  toPipelineConfig: (): PipelineConfig => {
    const { nodes, edges, collaborationMode } = get();
    return {
      stages: nodes.map((node) => ({
        id: node.id,
        name: node.data.label,
        taskType: "generate_code" as const,
        requiredRoles: [node.data.role],
        config: {
          instruction: node.data.instruction,
        },
        dependsOn: edges
          .filter((e) => e.target === node.id)
          .map((e) => e.source),
        timeout: 0,
      })),
      timeout: 3600,
      retryCount: 3,
      stopOnFailure: collaborationMode === "sequential",
      notifications: {
        onStageStart: true,
        onStageComplete: true,
        onStageFailure: true,
        onPipelineComplete: true,
      },
    };
  },
}));
