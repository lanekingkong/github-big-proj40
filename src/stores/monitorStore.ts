/**
 * Monitor State Store
 * ===================
 * Zustand store for real-time pipeline monitoring.
 *
 * Manages:
 * - Real-time log stream from agent execution
 * - Agent status updates (via WebSocket)
 * - Task progress tracking
 * - Performance metrics (tokens/sec, latency, etc.)
 *
 * This store is the primary consumer of WebSocket events during
 * pipeline execution.
 */

import { create } from "zustand";
import type { LogEntry, LogLevel, MetricData } from "../types/common";
import { AgentStatus } from "../types/agent";
import { TaskStatus } from "../types/project";

// ---------------------------------------------------------------------------
// Task Progress Entry
// ---------------------------------------------------------------------------

/**
 * Live progress of a single task during execution.
 */
export interface TaskProgress {
  /** Task ID */
  taskId: string;

  /** Associated agent ID */
  agentId: string;

  /** Associated project ID */
  projectId: string;

  /** Current task status */
  status: TaskStatus;

  /** Progress percentage (0-100) */
  progress: number;

  /** Brief description of the current step */
  currentStep: string;

  /** When the task started (ISO 8601) */
  startedAt: string | null;

  /** When the task completed (ISO 8601, null if still running) */
  completedAt: string | null;
}

// ---------------------------------------------------------------------------
// Agent Runtime Info
// ---------------------------------------------------------------------------

/**
 * Runtime information for a single agent during monitoring.
 */
export interface AgentRuntimeInfo {
  /** Agent config ID */
  agentId: string;

  /** Agent display name */
  name: string;

  /** Current status */
  status: AgentStatus;

  /** Current task ID (null if idle) */
  currentTaskId: string | null;

  /** Tasks completed in this session */
  completedTasks: number;

  /** Tasks failed in this session */
  failedTasks: number;

  /** Uptime in seconds */
  uptime: number;

  /** Last heartbeat timestamp (ISO 8601) */
  lastHeartbeat: string | null;
}

// ---------------------------------------------------------------------------
// Pipeline Run Info
// ---------------------------------------------------------------------------

/**
 * Summary of the current pipeline run.
 */
export interface PipelineRunInfo {
  /** Run ID */
  runId: string | null;

  /** Project ID */
  projectId: string | null;

  /** Whether a run is currently active */
  isRunning: boolean;

  /** Overall progress percentage (0-100) */
  overallProgress: number;

  /** Current stage name */
  currentStage: string | null;

  /** When the run started (ISO 8601) */
  startedAt: string | null;

  /** Estimated completion time (ISO 8601) */
  estimatedCompletion: string | null;
}

// ---------------------------------------------------------------------------
// Log Filter
// ---------------------------------------------------------------------------

/**
 * Filter configuration for the log viewer.
 */
export interface LogFilter {
  /** Filter by severity level */
  levels: LogLevel[];

  /** Filter by source (agent name or component) */
  sources: string[];

  /** Search query string */
  searchQuery: string;

  /** Show only logs after this timestamp */
  since: string | null;
}

// ---------------------------------------------------------------------------
// Store State
// ---------------------------------------------------------------------------

interface MonitorState {
  // ---- Pipeline Run ----
  run: PipelineRunInfo;

  // ---- Agent Runtime ----
  agents: AgentRuntimeInfo[];

  // ---- Tasks ----
  tasks: TaskProgress[];

  // ---- Logs ----
  logs: LogEntry[];

  /** Maximum number of logs to keep in memory */
  maxLogs: number;

  /** Active log filters */
  logFilter: LogFilter;

  // ---- Metrics ----
  /** Recent metric data points */
  metrics: MetricData[];

  /** Maximum metrics data points to keep */
  maxMetrics: number;

  // ---- WebSocket ----
  /** Whether the WebSocket is connected */
  wsConnected: boolean;

  // ---- Actions: Pipeline Run ----
  /** Start tracking a new pipeline run */
  startRun: (runId: string, projectId: string) => void;

  /** Update overall pipeline progress */
  updateRunProgress: (progress: number, currentStage?: string) => void;

  /** Complete the current run */
  completeRun: () => void;

  /** Fail the current run */
  failRun: () => void;

  // ---- Actions: Agent Runtime ----
  /** Update or add agent runtime info */
  upsertAgent: (agent: AgentRuntimeInfo) => void;

  /** Update agent status by ID */
  updateAgentStatus: (agentId: string, status: AgentStatus) => void;

  /** Remove an agent from monitoring */
  removeAgent: (agentId: string) => void;

  // ---- Actions: Tasks ----
  /** Add or update task progress */
  upsertTask: (task: TaskProgress) => void;

  /** Update task status */
  updateTaskStatus: (taskId: string, status: TaskStatus, progress?: number) => void;

  // ---- Actions: Logs ----
  /** Append a log entry */
  addLog: (entry: LogEntry) => void;

  /** Append multiple log entries at once */
  addLogs: (entries: LogEntry[]) => void;

  /** Update log filter */
  setLogFilter: (filter: Partial<LogFilter>) => void;

  /** Clear all logs */
  clearLogs: () => void;

  // ---- Actions: Metrics ----
  /** Add a metric data point */
  addMetric: (metric: MetricData) => void;

  /** Add multiple metric data points */
  addMetrics: (metrics: MetricData[]) => void;

  // ---- Actions: WebSocket ----
  setWsConnected: (connected: boolean) => void;

  // ---- Actions: Reset ----
  /** Reset all monitor state */
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate a unique log entry ID */
function generateLogId(): string {
  return `log-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// Store Implementation
// ---------------------------------------------------------------------------

/**
 * Zustand store hook for real-time monitoring.
 */
export const useMonitorStore = create<MonitorState>((set, get) => ({
  // ---- Initial State ----
  run: {
    runId: null,
    projectId: null,
    isRunning: false,
    overallProgress: 0,
    currentStage: null,
    startedAt: null,
    estimatedCompletion: null,
  },
  agents: [],
  tasks: [],
  logs: [],
  maxLogs: 5000,
  logFilter: {
    levels: [],
    sources: [],
    searchQuery: "",
    since: null,
  },
  metrics: [],
  maxMetrics: 1000,
  wsConnected: false,

  // ---- Pipeline Run ----
  startRun: (runId: string, projectId: string) =>
    set({
      run: {
        runId,
        projectId,
        isRunning: true,
        overallProgress: 0,
        currentStage: "Initializing",
        startedAt: new Date().toISOString(),
        estimatedCompletion: null,
      },
    }),

  updateRunProgress: (progress: number, currentStage?: string) =>
    set((state) => ({
      run: {
        ...state.run,
        overallProgress: progress,
        ...(currentStage !== undefined ? { currentStage } : {}),
      },
    })),

  completeRun: () =>
    set((state) => ({
      run: { ...state.run, isRunning: false, overallProgress: 100 },
    })),

  failRun: () =>
    set((state) => ({
      run: { ...state.run, isRunning: false },
    })),

  // ---- Agent Runtime ----
  upsertAgent: (agent: AgentRuntimeInfo) =>
    set((state) => {
      const existing = state.agents.findIndex((a) => a.agentId === agent.agentId);
      if (existing >= 0) {
        const updated = [...state.agents];
        updated[existing] = agent;
        return { agents: updated };
      }
      return { agents: [...state.agents, agent] };
    }),

  updateAgentStatus: (agentId: string, status: AgentStatus) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.agentId === agentId ? { ...a, status } : a
      ),
    })),

  removeAgent: (agentId: string) =>
    set((state) => ({
      agents: state.agents.filter((a) => a.agentId !== agentId),
    })),

  // ---- Tasks ----
  upsertTask: (task: TaskProgress) =>
    set((state) => {
      const existing = state.tasks.findIndex((t) => t.taskId === task.taskId);
      if (existing >= 0) {
        const updated = [...state.tasks];
        updated[existing] = task;
        return { tasks: updated };
      }
      return { tasks: [...state.tasks, task] };
    }),

  updateTaskStatus: (
    taskId: string,
    status: TaskStatus,
    progress?: number
  ) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.taskId === taskId
          ? {
              ...t,
              status,
              ...(progress !== undefined ? { progress } : {}),
              ...(status === TaskStatus.Completed || status === TaskStatus.Failed
                ? { completedAt: new Date().toISOString() }
                : {}),
            }
          : t
      ),
    })),

  // ---- Logs ----
  addLog: (entry: LogEntry) =>
    set((state) => ({
      logs: [...state.logs.slice(-state.maxLogs + 1), entry],
    })),

  addLogs: (entries: LogEntry[]) =>
    set((state) => {
      const combined = [...state.logs, ...entries];
      return {
        logs: combined.slice(-state.maxLogs),
      };
    }),

  setLogFilter: (filter: Partial<LogFilter>) =>
    set((state) => ({
      logFilter: { ...state.logFilter, ...filter },
    })),

  clearLogs: () => set({ logs: [] }),

  // ---- Metrics ----
  addMetric: (metric: MetricData) =>
    set((state) => ({
      metrics: [...state.metrics.slice(-state.maxMetrics + 1), metric],
    })),

  addMetrics: (metrics: MetricData[]) =>
    set((state) => {
      const combined = [...state.metrics, ...metrics];
      return {
        metrics: combined.slice(-state.maxMetrics),
      };
    }),

  // ---- WebSocket ----
  setWsConnected: (connected: boolean) =>
    set({ wsConnected: connected }),

  // ---- Reset ----
  reset: () =>
    set({
      run: {
        runId: null,
        projectId: null,
        isRunning: false,
        overallProgress: 0,
        currentStage: null,
        startedAt: null,
        estimatedCompletion: null,
      },
      agents: [],
      tasks: [],
      logs: [],
      metrics: [],
      wsConnected: false,
    }),
}));
