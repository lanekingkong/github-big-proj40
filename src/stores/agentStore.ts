/**
 * Agent State Store
 * =================
 * Zustand store for Agent lifecycle management, online status tracking,
 * and agent selection for the Forge Editor.
 *
 * Manages:
 * - List of registered Agent configs
 * - Agent online/offline status (real-time via WebSocket)
 * - Currently selected agent for editing
 * - Agent registration and deregistration
 */

import { create } from "zustand";
import type {
  AgentConfig,
  AgentStatus,
  AgentRegistrationDTO,
  AgentUpdateDTO,
} from "../types/agent";

// ---------------------------------------------------------------------------
// Store State
// ---------------------------------------------------------------------------

interface AgentState {
  // ---- Data ----
  /** All registered agent configurations */
  agents: AgentConfig[];

  /** Live status map: agentId → AgentStatus */
  agentStatuses: Record<string, AgentStatus>;

  /** Currently selected agent for detail view / editing */
  selectedAgent: AgentConfig | null;

  // ---- UI State ----
  /** Whether the agent list is loading */
  isLoading: boolean;

  /** Whether a mutation is in progress */
  isSaving: boolean;

  /** Error message from the last failed operation */
  error: string | null;

  // ---- Actions ----
  /** Fetch all registered agents from the backend */
  fetchAgents: () => Promise<void>;

  /** Register a new agent */
  registerAgent: (dto: AgentRegistrationDTO) => Promise<AgentConfig>;

  /** Update an existing agent */
  updateAgent: (id: string, dto: AgentUpdateDTO) => Promise<AgentConfig>;

  /** Unregister (delete) an agent */
  unregisterAgent: (id: string) => Promise<void>;

  /** Select an agent for detail view */
  selectAgent: (agent: AgentConfig | null) => void;

  /** Update the live status of an agent (called by WebSocket handler) */
  updateAgentStatus: (agentId: string, status: AgentStatus) => void;

  /** Bulk update statuses from a WebSocket event */
  bulkUpdateStatuses: (statuses: Record<string, AgentStatus>) => void;

  /** Get agents filtered by role */
  getAgentsByRole: (role: string) => AgentConfig[];

  /** Get agents filtered by status */
  getAgentsByStatus: (status: AgentStatus) => AgentConfig[];

  /** Get online agents */
  getOnlineAgents: () => AgentConfig[];

  /** Clear error state */
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getBackendUrl(): string {
  return "http://127.0.0.1:18090";
}

// ---------------------------------------------------------------------------
// Store Implementation
// ---------------------------------------------------------------------------

/**
 * Zustand store hook for Agent state management.
 */
export const useAgentStore = create<AgentState>((set, get) => ({
  // ---- Initial State ----
  agents: [],
  agentStatuses: {},
  selectedAgent: null,
  isLoading: false,
  isSaving: false,
  error: null,

  // ---- Fetch Agents ----
  fetchAgents: async () => {
    set({ isLoading: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/agents`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const agents: AgentConfig[] = data.data ?? data;
      // Build status map from current agent statuses
      const statuses: Record<string, AgentStatus> = {};
      agents.forEach((a) => {
        statuses[a.id] = a.status;
      });
      set({ agents, agentStatuses: statuses, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to fetch agents",
        isLoading: false,
      });
    }
  },

  // ---- Register Agent ----
  registerAgent: async (dto: AgentRegistrationDTO): Promise<AgentConfig> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dto),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const agent: AgentConfig = data.data ?? data;
      set((state) => ({
        agents: [agent, ...state.agents],
        agentStatuses: {
          ...state.agentStatuses,
          [agent.id]: agent.status,
        },
        isSaving: false,
      }));
      return agent;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to register agent",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Update Agent ----
  updateAgent: async (id: string, dto: AgentUpdateDTO): Promise<AgentConfig> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/agents/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dto),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const agent: AgentConfig = data.data ?? data;
      set((state) => ({
        agents: state.agents.map((a) => (a.id === id ? agent : a)),
        selectedAgent: state.selectedAgent?.id === id ? agent : state.selectedAgent,
        isSaving: false,
      }));
      return agent;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to update agent",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Unregister Agent ----
  unregisterAgent: async (id: string): Promise<void> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/agents/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      set((state) => {
        const { [id]: _, ...remaining } = state.agentStatuses;
        return {
          agents: state.agents.filter((a) => a.id !== id),
          agentStatuses: remaining,
          selectedAgent:
            state.selectedAgent?.id === id ? null : state.selectedAgent,
          isSaving: false,
        };
      });
    } catch (err) {
      set({
        error:
          err instanceof Error ? err.message : "Failed to unregister agent",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Select Agent ----
  selectAgent: (agent: AgentConfig | null) => {
    set({ selectedAgent: agent });
  },

  // ---- Update Status (Single) ----
  updateAgentStatus: (agentId: string, status: AgentStatus) => {
    set((state) => ({
      agentStatuses: {
        ...state.agentStatuses,
        [agentId]: status,
      },
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, status } : a
      ),
    }));
  },

  // ---- Bulk Update Statuses ----
  bulkUpdateStatuses: (statuses: Record<string, AgentStatus>) => {
    set((state) => {
      const merged = { ...state.agentStatuses, ...statuses };
      return {
        agentStatuses: merged,
        agents: state.agents.map((a) =>
          a.id in statuses ? { ...a, status: statuses[a.id] } : a
        ),
      };
    });
  },

  // ---- Selectors ----
  getAgentsByRole: (role: string) => {
    return get().agents.filter((a) => a.role === role);
  },

  getAgentsByStatus: (status: AgentStatus) => {
    return get().agents.filter(
      (a) => (get().agentStatuses[a.id] ?? a.status) === status
    );
  },

  getOnlineAgents: () => {
    return get().agents.filter(
      (a) => (get().agentStatuses[a.id] ?? a.status) === "online"
    );
  },

  // ---- Clear Error ----
  clearError: () => set({ error: null }),
}));
