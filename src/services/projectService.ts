/**
 * Project API Service
 * ===================
 * HTTP service layer for Project CRUD and pipeline execution operations.
 *
 * Encapsulates all communication with the Python FastAPI backend's
 * Project endpoints (/api/v1/projects).
 */

import type {
  Project,
  ProjectCreateDTO,
  ProjectUpdateDTO,
  Task,
} from "../types/project";
import type {
  ApiResponse,
  PaginationParams,
  PaginatedResponse,
} from "../types/common";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

let BASE_URL = "http://127.0.0.1:18090/api/v1";

/**
 * Update the base URL for API requests.
 */
export function setProjectServiceBaseUrl(url: string): void {
  BASE_URL = url.replace(/\/$/, "");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Standard request wrapper for project API calls.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const body: ApiResponse = await response.json();
      errorMessage = body.error || errorMessage;
    } catch {
      /* body is not JSON */
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
// Project API Methods
// ---------------------------------------------------------------------------

/**
 * Fetch a paginated list of projects.
 *
 * @param params - Pagination and sorting parameters
 * @returns Paginated project list
 */
export async function getProjects(
  params?: Partial<PaginationParams>
): Promise<PaginatedResponse<Project>> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.pageSize) query.set("page_size", String(params.pageSize));
  if (params?.sortBy) query.set("sort_by", params.sortBy);
  if (params?.sortOrder) query.set("sort_order", params.sortOrder);
  const qs = query.toString();
  return request<PaginatedResponse<Project>>(
    `/projects${qs ? `?${qs}` : ""}`
  );
}

/**
 * Get a single project by ID.
 *
 * @param id - Project ID
 * @returns The project detail
 */
export async function getProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${id}`);
}

/**
 * Create a new project.
 *
 * @param dto - Project creation data
 * @returns The created project
 */
export async function createProject(
  dto: ProjectCreateDTO
): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(dto),
  });
}

/**
 * Update an existing project.
 *
 * @param id - Project ID
 * @param dto - Fields to update
 * @returns The updated project
 */
export async function updateProject(
  id: string,
  dto: ProjectUpdateDTO
): Promise<Project> {
  return request<Project>(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(dto),
  });
}

/**
 * Delete a project.
 *
 * @param id - Project ID
 */
export async function deleteProject(id: string): Promise<void> {
  return request<void>(`/projects/${id}`, {
    method: "DELETE",
  });
}

/**
 * Execute a project's pipeline.
 * This triggers the full pipeline run on the backend.
 *
 * @param id - Project ID
 * @returns The run ID
 */
export async function executeProject(
  id: string
): Promise<{ runId: string }> {
  return request<{ runId: string }>(`/projects/${id}/execute`, {
    method: "POST",
  });
}

/**
 * Stop/cancel an active pipeline run.
 *
 * @param projectId - Project ID
 * @param runId - Run ID
 */
export async function cancelExecution(
  projectId: string,
  runId: string
): Promise<void> {
  return request<void>(`/projects/${projectId}/executions/${runId}/cancel`, {
    method: "POST",
  });
}

/**
 * Get all tasks for a project's current pipeline run.
 *
 * @param projectId - Project ID
 * @param runId - Run ID
 * @returns Array of tasks
 */
export async function getProjectTasks(
  projectId: string,
  runId: string
): Promise<Task[]> {
  return request<Task[]>(
    `/projects/${projectId}/executions/${runId}/tasks`
  );
}

/**
 * Get a specific task detail.
 *
 * @param projectId - Project ID
 * @param runId - Run ID
 * @param taskId - Task ID
 */
export async function getTask(
  projectId: string,
  runId: string,
  taskId: string
): Promise<Task> {
  return request<Task>(
    `/projects/${projectId}/executions/${runId}/tasks/${taskId}`
  );
}

/**
 * Get execution history for a project.
 *
 * @param projectId - Project ID
 * @returns List of past runs with status
 */
export async function getExecutionHistory(
  projectId: string
): Promise<
  { runId: string; status: string; startedAt: string; completedAt: string | null }[]
> {
  return request<
    { runId: string; status: string; startedAt: string; completedAt: string | null }[]
  >(`/projects/${projectId}/executions`);
}

/**
 * Validate a project's pipeline configuration.
 *
 * @param id - Project ID
 * @returns Validation result with errors and warnings
 */
export async function validateProject(
  id: string
): Promise<{ valid: boolean; errors: string[]; warnings: string[] }> {
  return request<{ valid: boolean; errors: string[]; warnings: string[] }>(
    `/projects/${id}/validate`,
    { method: "POST" }
  );
}
