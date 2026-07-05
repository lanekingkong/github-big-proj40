/**
 * AgentList - Agent 列表面板
 * 可搜索、筛选、排序；支持拖拽到 Forge 画布
 */
import React, { useMemo, useState, useCallback } from 'react';
import type { AgentConfig } from '../../types/agent';

interface Props {
  agents: AgentConfig[];
  selectedId?: string;
  onSelect: (agent: AgentConfig) => void;
  onDelete: (id: string) => void;
  onDuplicate: (agent: AgentConfig) => void;
  onCreate: () => void;
  onDragStart?: (e: React.DragEvent, agent: AgentConfig) => void;
}

type SortKey = 'name' | 'role' | 'model' | 'created';

const AgentList: React.FC<Props> = ({ agents, selectedId, onSelect, onDelete, onDuplicate, onCreate, onDragStart }) => {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<SortKey>('name');

  const filtered = useMemo(() => {
    let list = agents;
    if (search) { const q = search.toLowerCase(); list = list.filter((a) => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)); }
    if (roleFilter !== 'all') list = list.filter((a) => a.role === roleFilter);
    list = [...list].sort((a, b) => {
      if (sortKey === 'name') return a.name.localeCompare(b.name);
      if (sortKey === 'role') return a.role.localeCompare(b.role);
      if (sortKey === 'model') return (a.model || '').localeCompare(b.model || '');
      return 0;
    });
    return list;
  }, [agents, search, roleFilter, sortKey]);

  const roles = useMemo(() => [...new Set(agents.map((a) => a.role))], [agents]);

  const roleBadgeColor = (role: string) => {
    const map: Record<string, string> = { orchestrator: 'bg-purple-500/20 text-purple-300', assistant: 'bg-blue-500/20 text-blue-300', executor: 'bg-emerald-500/20 text-emerald-300', reviewer: 'bg-amber-500/20 text-amber-300', custom: 'bg-slate-500/20 text-slate-300' };
    return map[role] || map.custom;
  };

  return (
    <div className="flex flex-col h-full">
      {/* 搜索 + 操作 */}
      <div className="p-3 border-b border-white/5 space-y-2.5">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <input className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-900/60 border border-white/10 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-400/50" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索Agent..." />
          </div>
          <button onClick={onCreate} className="shrink-0 w-9 h-9 rounded-lg bg-amber-400 text-slate-900 hover:bg-amber-300 flex items-center justify-center transition-colors" title="创建Agent">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
          </button>
        </div>
        <div className="flex gap-1.5">
          <select className="flex-1 px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-white/10 text-xs text-slate-400" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="all">全部角色</option>
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select className="flex-1 px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-white/10 text-xs text-slate-400" value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
            <option value="name">按名称</option>
            <option value="role">按角色</option>
            <option value="model">按模型</option>
          </select>
        </div>
      </div>

      {/* 列表 */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-600">
            <svg className="w-10 h-10 mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            <p className="text-sm">{search ? '没有匹配的Agent' : '暂无Agent'}</p>
            <p className="text-xs mt-1">{search ? '试试其他关键词' : '点击 + 创建第一个'}</p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filtered.map((agent) => (
              <div key={agent.id} draggable onDragStart={(e) => onDragStart?.(e, agent)} onClick={() => onSelect(agent)} className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition-all ${
                selectedId === agent.id ? 'border-amber-400/40 bg-amber-400/5' : 'border-transparent hover:border-white/10 hover:bg-white/5'
              }`}>
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold uppercase ${roleBadgeColor(agent.role)}`}>
                  {agent.name.slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200 truncate">{agent.name}</span>
                    <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium ${roleBadgeColor(agent.role)}`}>{agent.role}</span>
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-0.5">{agent.description}</p>
                  <div className="flex items-center gap-1.5 mt-1.5">
                    <span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">{agent.model}</span>
                    {agent.capabilities.length > 0 && <span className="text-[10px] text-slate-600">{agent.capabilities.length} 能力</span>}
                  </div>
                </div>
                <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={(e) => { e.stopPropagation(); onDuplicate(agent); }} className="w-7 h-7 rounded hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white" title="复制"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button>
                  <button onClick={(e) => { e.stopPropagation(); if (window.confirm(`删除 "${agent.name}"？`)) onDelete(agent.id); }} className="w-7 h-7 rounded hover:bg-red-500/20 flex items-center justify-center text-slate-400 hover:text-red-400" title="删除"><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M6 18L18 6M6 6l12 12"/></svg></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentList;
