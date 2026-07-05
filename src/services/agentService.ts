/**
 * Agent API Service
 * =================
 * HTTP service layer for Agent CRUD operations.
 *
 * Encapsulates all communication with the Python FastAPI backend's
 * Agent endpoints (/api/v1/agents).
 *
 * All methods return typed responses and handle errors consistently.
 */

import type {
  AgentConfig,
  AgentRegistrationDTO,
  AgentUpdateDTO,
  AgentInstance,
} from "../types/agent";
import type { ApiResponse, PaginationParams, PaginatedResponse } from "../types/common";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Default backend URL (overridden in Electron via IPC) */
let BASE_URL = "http://127.0.0.1:18090/api/v1";

/**
 * Update the base URL for API requests.
 * Called by the app initialization when running in Electron.
 */
export function setAgentServiceBaseUrl(url: string): void {
  BASE_URL = url.replace(/\/$/, "");
}

/**
 * Get the current base URL.
 */
export function getBaseUrl(): string {
  return BASE_URL;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Standard request wrapper with error handling and response parsing.
 *
 * @template T - Expected response data type
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorBody: ApiResponse = await response.json();
      errorMessage = errorBody.error || errorMessage;
    } catch {
      // Response body is not JSON
    }
    throw new Error(errorMessage);
  }

  const result: ApiResponse<T> = await response.json();

  if (!result.success) {
    throw new Error(result.error || "Unknown API error");
  }

  return result.data as T;
}

// ---------------------------------------------------------------------------
// Agent API Methods
// ---------------------------------------------------------------------------

/**
 * Fetch a paginated list of registered agents.
 *
 * @param params - Pagination and sorting parameters
 * @returns Paginated agent list
 */
export async function getAgents(
  params?: Partial<PaginationParams>
): Promise<PaginatedResponse<AgentConfig>> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  if (params?.sortBy) query.set("sort_by", params.sortBy);
  if (params?.sortOrder) query.set("sort_order", params.sortOrder);
  const qs = query.toString();
  return request<PaginatedResponse<AgentConfig>>(
    `/agents${qs ? `?${qs}` : ""}`
  );
}

/**
 * Fetch all agents (no pagination, for small agent counts).
 *
 * @returns Array of all agent configs
 */
export async function getAllAgents(): Promise<AgentConfig[]> {
  return request<AgentConfig[]>("/agents?page_size=1000");
}

/**
 * Get a single agent by its ID.
 *
 * @param id - Agent configuration ID
 * @returns The agent configuration
 */
export async function getAgent(id: string): Promise<AgentConfig> {
  return request<AgentConfig>(`/agents/${id}`);
}

/**
 * Get the runtime instance of an agent (includes live status).
 *
 * @param id - Agent configuration ID
 * @returns The live agent instance
 */
export async function getAgentInstance(id: string): Promise<AgentInstance> {
  return request<AgentInstance>(`/agents/${id}/instance`);
}

/**
 * Register a new agent.
 *
 * @param dto - Agent registration data
 * @returns The created agent configuration
 */
export async function registerAgent(
  dto: AgentRegistrationDTO
): Promise<AgentConfig> {
  return request<AgentConfig>("/agents", {
    method: "POST",
    body: JSON.stringify(dto),
  });
}

/**
 * Update an existing agent configuration.
 *
 * @param id - Agent configuration ID
 * @param dto - Fields to update (partial)
 * @returns The updated agent configuration
 */
export async function updateAgent(
  id: string,
  dto: AgentUpdateDTO
): Promise<AgentConfig> {
  return request<AgentConfig>(`/agents/${id}`, {
    method: "PATCH",
    body: JSON.stringify(dto),
  });
}

/**
 * Unregister (delete) an agent.
 *
 * @param id - Agent configuration ID
 */
export async function unregisterAgent(id: string): Promise<void> {
  return request<void>(`/agents/${id}`, {
    method: "DELETE",
  });
}

/**
 * Start an agent (transitions from Idle → Online).
 *
 * @param id - Agent configuration ID
 * @returns Updated agent config
 */
export async function startAgent(id: string): Promise<AgentConfig> {
  return request<AgentConfig>(`/agents/${id}/start`, {
    method: "POST",
  });
}

/**
 * Stop a running agent (transitions to Idle).
 *
 * @param id - Agent configuration ID
 */
export async function stopAgent(id: string): Promise<AgentConfig> {
  return request<AgentConfig>(`/agents/${id}/stop`, {
    method: "POST",
  });
}

/**
 * Pause a busy agent.
 *
 * @param id - Agent configuration ID
 */
export async function pauseAgent(id: string): Promise<AgentConfig> {
  return request<AgentConfig>(`/agents/${id}/pause`, {
    method: "POST",
  });
}

/**
 * Discover agents from connected MCP servers.
 *
 * @returns List of discovered agent configs
 */
export async function discoverAgents(): Promise<AgentConfig[]> {
  return request<AgentConfig[]>("/agents/discover", {
    method: "POST",
  });
}

/**
 * Get the health/status of an agent.
 *
 * @param id - Agent configuration ID
 * @returns Health check result
 */
export async function healthCheckAgent(
  id: string
): Promise<{ healthy: boolean; details: Record<string, unknown> }> {
  return request<{ healthy: boolean; details: Record<string, unknown> }>(
    `/agents/${id}/health`
  );
}
