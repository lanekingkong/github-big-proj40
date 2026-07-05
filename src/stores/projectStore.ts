/**
 * Project State Store
 * ===================
 * Zustand store for project CRUD operations and local state management.
 *
 * Manages:
 * - Project list (fetched from backend or local cache)
 * - Currently selected/active project
 * - Project CRUD operations with optimistic updates
 * - Loading and error states
 */

import { create } from "zustand";
import type { Project, ProjectCreateDTO, ProjectUpdateDTO, ProjectStatus } from "../types/project";

// ---------------------------------------------------------------------------
// Store State
// ---------------------------------------------------------------------------

interface ProjectState {
  // ---- Data ----
  /** All projects loaded from the backend */
  projects: Project[];

  /** Currently selected project (for the Forge Editor or Monitor) */
  selectedProject: Project | null;

  // ---- UI State ----
  /** Whether the project list is being fetched */
  isLoading: boolean;

  /** Whether a create/update/delete operation is in progress */
  isSaving: boolean;

  /** Error message from the last failed operation, or null */
  error: string | null;

  // ---- Actions ----
  /** Fetch all projects from the backend */
  fetchProjects: () => Promise<void>;

  /** Create a new project */
  createProject: (dto: ProjectCreateDTO) => Promise<Project>;

  /** Update an existing project */
  updateProject: (id: string, dto: ProjectUpdateDTO) => Promise<Project>;

  /** Delete a project by ID */
  deleteProject: (id: string) => Promise<void>;

  /** Select a project and load full details */
  selectProject: (project: Project | null) => void;

  /** Update the status of the selected project (optimistic) */
  updateProjectStatus: (status: ProjectStatus) => void;

  /** Clear any error state */
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Helper: Get backend URL
// ---------------------------------------------------------------------------

function getBackendUrl(): string {
  // In Electron, the preload exposes getBackendUrl via IPC
  // For browser dev mode, fall back to localhost
  if (typeof window !== "undefined" && window.electronAPI?.getBackendUrl) {
    return "http://127.0.0.1:18090"; // Will be wrapped by service layer
  }
  return "http://127.0.0.1:18090";
}

// ---------------------------------------------------------------------------
// Store Implementation
// ---------------------------------------------------------------------------

/**
 * Zustand store hook for project state management.
 *
 * @example
 * ```tsx
 * const { projects, fetchProjects } = useProjectStore();
 * useEffect(() => { fetchProjects(); }, []);
 * ```
 */
export const useProjectStore = create<ProjectState>((set, get) => ({
  // ---- Initial State ----
  projects: [],
  selectedProject: null,
  isLoading: false,
  isSaving: false,
  error: null,

  // ---- Fetch Projects ----
  fetchProjects: async () => {
    set({ isLoading: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/projects`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const projects: Project[] = data.data ?? data;
      set({ projects, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to fetch projects",
        isLoading: false,
      });
    }
  },

  // ---- Create Project ----
  createProject: async (dto: ProjectCreateDTO): Promise<Project> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dto),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const project: Project = data.data ?? data;
      set((state) => ({
        projects: [project, ...state.projects],
        selectedProject: project,
        isSaving: false,
      }));
      return project;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to create project",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Update Project ----
  updateProject: async (id: string, dto: ProjectUpdateDTO): Promise<Project> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/projects/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dto),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const project: Project = data.data ?? data;
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? project : p)),
        selectedProject:
          state.selectedProject?.id === id ? project : state.selectedProject,
        isSaving: false,
      }));
      return project;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to update project",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Delete Project ----
  deleteProject: async (id: string): Promise<void> => {
    set({ isSaving: true, error: null });
    try {
      const baseUrl = getBackendUrl();
      const response = await fetch(`${baseUrl}/api/v1/projects/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        selectedProject:
          state.selectedProject?.id === id ? null : state.selectedProject,
        isSaving: false,
      }));
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to delete project",
        isSaving: false,
      });
      throw err;
    }
  },

  // ---- Select Project ----
  selectProject: (project: Project | null) => {
    set({ selectedProject: project });
  },

  // ---- Update Status (Optimistic) ----
  updateProjectStatus: (status: ProjectStatus) => {
    set((state) => {
      if (!state.selectedProject) return state;
      return {
        selectedProject: { ...state.selectedProject, status },
        projects: state.projects.map((p) =>
          p.id === state.selectedProject!.id ? { ...p, status } : p
        ),
      };
    });
  },

  // ---- Clear Error ----
  clearError: () => set({ error: null }),
}));
