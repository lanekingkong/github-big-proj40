/**
 * useProject - 项目管理 Hook
 * CRUD + 本地持久化（localStorage） + 导入导出
 */
import { useState, useEffect, useCallback } from 'react';
import type { ProjectConfig } from '../types/project';

const STORAGE_KEY = 'agentforge_projects';

interface UseProjectReturn {
  projects: ProjectConfig[];
  currentProject: ProjectConfig | null;
  createProject: (name: string, description?: string) => ProjectConfig;
  updateProject: (id: string, partial: Partial<ProjectConfig>) => void;
  deleteProject: (id: string) => void;
  selectProject: (id: string) => void;
  duplicateProject: (id: string) => void;
  exportProject: (id: string) => string;
  importProject: (json: string) => ProjectConfig;
  recentProjects: ProjectConfig[];
}

export function useProject(): UseProjectReturn {
  const [projects, setProjects] = useState<ProjectConfig[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  });
  const [currentId, setCurrentId] = useState<string | null>(() => projects[0]?.id || null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
  }, [projects]);

  const currentProject = projects.find((p) => p.id === currentId) || null;

  const createProject = useCallback((name: string, description = '') => {
    const p: ProjectConfig = {
      id: crypto.randomUUID(),
      name,
      description,
      forgeData: { nodes: [], edges: [] },
      agents: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      tags: [],
    };
    setProjects((prev) => [p, ...prev]);
    setCurrentId(p.id);
    return p;
  }, []);

  const updateProject = useCallback((id: string, partial: Partial<ProjectConfig>) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, ...partial, updatedAt: new Date().toISOString() } : p)));
  }, []);

  const deleteProject = useCallback((id: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
    if (currentId === id) setCurrentId(null);
  }, [currentId]);

  const selectProject = useCallback((id: string) => setCurrentId(id), []);

  const duplicateProject = useCallback((id: string) => {
    const src = projects.find((p) => p.id === id);
    if (!src) return;
    createProject(`${src.name} (Copy)`, src.description);
  }, [projects, createProject]);

  const exportProject = useCallback((id: string) => {
    const p = projects.find((p2) => p2.id === id);
    return p ? JSON.stringify({ format: 'agentforge/project', version: 1, project: p }, null, 2) : '{}';
  }, [projects]);

  const importProject = useCallback((json: string) => {
    const data = JSON.parse(json);
    if (data.format !== 'agentforge/project') throw new Error('无效的项目文件格式');
    const p = { ...data.project, id: crypto.randomUUID(), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
    setProjects((prev) => [p, ...prev]);
    return p;
  }, []);

  const recentProjects = [...projects].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()).slice(0, 5);

  return { projects, currentProject, createProject, updateProject, deleteProject, selectProject, duplicateProject, exportProject, importProject, recentProjects };
}
