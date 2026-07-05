/**
 * useAgents - Agent CRUD + 搜索/筛选 Hook
 */
import { useState, useCallback, useMemo } from 'react';
import type { AgentConfig } from '../types/agent';

interface UseAgentsReturn {
  agents: AgentConfig[];
  addAgent: (agent: AgentConfig) => void;
  updateAgent: (id: string, partial: Partial<AgentConfig>) => void;
  removeAgent: (id: string) => void;
  duplicateAgent: (agent: AgentConfig) => void;
  getAgent: (id: string) => AgentConfig | undefined;
  filteredAgents: (query: string, role?: string) => AgentConfig[];
}

export function useAgents(initial: AgentConfig[] = []): UseAgentsReturn {
  const [agents, setAgents] = useState<AgentConfig[]>(initial);

  const addAgent = useCallback((agent: AgentConfig) => setAgents((prev) => [...prev, agent]), []);
  const updateAgent = useCallback((id: string, partial: Partial<AgentConfig>) =>
    setAgents((prev) => prev.map((a) => (a.id === id ? { ...a, ...partial } : a))), []);
  const removeAgent = useCallback((id: string) => setAgents((prev) => prev.filter((a) => a.id !== id)), []);
  const duplicateAgent = useCallback((agent: AgentConfig) => {
    setAgents((prev) => [...prev, { ...agent, id: crypto.randomUUID(), name: `${agent.name} (Copy)` }]);
  }, []);
  const getAgent = useCallback((id: string) => agents.find((a) => a.id === id), [agents]);

  const filteredAgents = useCallback((query: string, role?: string) => {
    let result = agents;
    if (query) { const q = query.toLowerCase(); result = result.filter((a) => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)); }
    if (role) result = result.filter((a) => a.role === role);
    return result;
  }, [agents]);

  return { agents, addAgent, updateAgent, removeAgent, duplicateAgent, getAgent, filteredAgents };
}
