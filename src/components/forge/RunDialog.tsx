/**
 * RunDialog - 流水线运行确认对话框
 * 展示运行前摘要、模式选择、Agent节点预览
 */
import React, { useMemo, useState } from 'react';
import type { ForgeNode } from '../../types/forge';

interface Props {
  projectName: string;
  nodes: ForgeNode[];
  onClose: () => void;
  onConfirm: (config: { mode: string; selectedAgents: string[] }) => void;
}

const RunDialog: React.FC<Props> = ({ projectName, nodes, onClose, onConfirm }) => {
  const [mode, setMode] = useState<string>('sequential');
  const [selectedSet, setSelectedSet] = useState<Set<string>>(new Set(nodes.map((n) => n.id)));

  const toggle = (id: string) => setSelectedSet((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const modes = [
    { value: 'sequential', label: '顺序执行', desc: '按连线拓扑依次执行' },
    { value: 'parallel', label: '并行执行', desc: '所有Agent同时启动' },
    { value: 'conditional', label: '条件分支', desc: '根据上一步输出决定下一步' },
    { value: 'iterative', label: '循环迭代', desc: '循环直到满足终止条件' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-slate-800 border border-white/10 rounded-xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <h2 className="text-lg font-semibold text-white">运行流水线</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors"><svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>

        <div className="p-5 space-y-5">
          {/* 运行摘要 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">项目</div>
              <div className="text-sm text-white font-medium truncate">{projectName}</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">Agent 数量</div>
              <div className="text-sm text-amber-400 font-medium">{nodes.length} 个</div>
            </div>
          </div>

          {/* 模式选择 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">运行模式</label>
            <div className="grid grid-cols-2 gap-2">
              {modes.map((m) => (
                <button key={m.value} onClick={() => setMode(m.value)} className={`p-3 rounded-lg text-left border transition-all ${mode === m.value ? 'border-amber-400/60 bg-amber-400/10 text-white' : 'border-white/5 bg-slate-900/30 text-slate-400 hover:border-white/15'}`}>
                  <div className="text-sm font-medium">{m.label}</div>
                  <div className="text-xs mt-0.5 opacity-70">{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Agent选择 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">参与Agent</label>
            <div className="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar">
              {nodes.map((n) => (
                <label key={n.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-900/30 hover:bg-slate-900/50 cursor-pointer border border-white/5">
                  <input type="checkbox" checked={selectedSet.has(n.id)} onChange={() => toggle(n.id)} className="w-4 h-4 accent-amber-400 rounded" />
                  <span className="text-sm text-slate-300">{n.data.label}</span>
                  <span className="ml-auto text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{n.data.agentType}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2.5 p-4 border-t border-white/5">
          <button onClick={onClose} className="flex-1 px-4 py-2.5 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 transition-colors text-sm font-medium">取消</button>
          <button onClick={() => onConfirm({ mode, selectedAgents: [...selectedSet] })} className="flex-1 px-4 py-2.5 rounded-lg bg-amber-400 text-slate-900 hover:bg-amber-300 transition-colors text-sm font-semibold">开始运行</button>
        </div>
      </div>
    </div>
  );
};

export default RunDialog;
