/**
 * AgentForm - Agent 创建/编辑表单
 * 支持基础信息、模型配置、系统提示词、工具绑定、角色权限
 */
import React, { useState, useEffect, useCallback } from 'react';
import type { AgentConfig, AgentRole, AgentCapability } from '../../types/agent';
import { AGENT_ROLES, AGENT_CAPABILITIES } from '../../utils/constants';

interface Props {
  initial?: Partial<AgentConfig>;
  onSave: (config: AgentConfig) => void;
  onCancel: () => void;
}

type Tab = 'basic' | 'model' | 'system' | 'tools';

const AgentForm: React.FC<Props> = ({ initial, onSave, onCancel }) => {
  const [tab, setTab] = useState<Tab>('basic');
  const [form, setForm] = useState<AgentConfig>({
    id: initial?.id || crypto.randomUUID(),
    name: initial?.name || '',
    description: initial?.description || '',
    role: initial?.role || 'assistant',
    model: initial?.model || 'gpt-4o',
    temperature: initial?.temperature ?? 0.7,
    maxTokens: initial?.maxTokens ?? 4096,
    systemPrompt: initial?.systemPrompt || '',
    capabilities: initial?.capabilities || [],
    retryConfig: initial?.retryConfig || { maxRetries: 2, backoffFactor: 1.5 },
    ...initial,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const update = useCallback(<K extends keyof AgentConfig>(k: K, v: AgentConfig[K]) => setForm((f) => ({ ...f, [k]: v })), []);

  const toggleCap = (cap: AgentCapability) => update('capabilities',
    form.capabilities.includes(cap) ? form.capabilities.filter((c) => c !== cap) : [...form.capabilities, cap]);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!form.name.trim()) errs.name = '名称必填';
    if (!form.description.trim()) errs.description = '描述必填';
    if (!form.systemPrompt.trim()) errs.systemPrompt = '系统提示词必填';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSave = () => { if (validate()) onSave(form); };

  const tabs: Tab[] = ['basic', 'model', 'system', 'tools'];
  const inputClass = 'w-full px-3 py-2 rounded-lg bg-slate-900/60 border border-white/10 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20';
  const labelClass = 'block text-xs font-medium text-slate-400 mb-1.5';

  return (
    <div className="flex flex-col h-full bg-slate-850">
      {/* Tabs */}
      <div className="flex bg-slate-900/50 border-b border-white/5">
        {tabs.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${tab === t ? 'border-amber-400 text-white' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>
            {({ basic: '基础信息', model: '模型配置', system: '系统提示', tools: '工具能力' })[t]}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
        {/* Basic */}
        {tab === 'basic' && (<>
          <div>
            <label className={labelClass}>名称</label>
            <input className={inputClass} value={form.name} onChange={(e) => update('name', e.target.value)} placeholder="如 CodeReviewer" />
            {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name}</p>}
          </div>
          <div>
            <label className={labelClass}>描述</label>
            <textarea className={`${inputClass} h-20 resize-none`} value={form.description} onChange={(e) => update('description', e.target.value)} placeholder="简述Agent的职责与定位" />
            {errors.description && <p className="text-xs text-red-400 mt-1">{errors.description}</p>}
          </div>
          <div>
            <label className={labelClass}>角色</label>
            <div className="grid grid-cols-2 gap-2">
              {AGENT_ROLES.map((r) => (
                <button key={r.value} type="button" onClick={() => update('role', r.value as AgentRole)} className={`p-2.5 rounded-lg text-xs text-left border transition-all ${form.role === r.value ? 'border-amber-400/60 bg-amber-400/10 text-amber-300' : 'border-white/5 bg-slate-900/30 text-slate-400 hover:border-white/15'}`}>
                  <div className="font-medium">{r.label}</div><div className="opacity-60 mt-0.5">{r.desc}</div>
                </button>
              ))}
            </div>
          </div>
        </>)}

        {/* Model */}
        {tab === 'model' && (<>
          <div>
            <label className={labelClass}>模型</label>
            <select className={inputClass} value={form.model} onChange={(e) => update('model', e.target.value)}>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="deepseek-v3">DeepSeek V3</option>
              <option value="qwen-max">Qwen Max</option>
              <option value="custom">自定义...</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Temperature ({form.temperature})</label>
              <input type="range" min="0" max="2" step="0.1" value={form.temperature} onChange={(e) => update('temperature', parseFloat(e.target.value))} className="w-full accent-amber-400" />
            </div>
            <div>
              <label className={labelClass}>Max Tokens</label>
              <select className={inputClass} value={form.maxTokens} onChange={(e) => update('maxTokens', parseInt(e.target.value))}>
                {[1024, 2048, 4096, 8192, 16384, 32768].map((v) => <option key={v} value={v}>{v.toLocaleString()}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className={labelClass}>重试配置</label>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2"><span className="text-xs text-slate-400">最多重试</span>
                <input type="number" min="0" max="10" value={form.retryConfig.maxRetries} onChange={(e) => update('retryConfig', { ...form.retryConfig, maxRetries: parseInt(e.target.value) || 0 })} className="w-16 px-2 py-1 rounded bg-slate-900/60 border border-white/10 text-sm text-center text-slate-200" />
              </div>
              <div className="flex items-center gap-2"><span className="text-xs text-slate-400">退避因子</span>
                <input type="number" min="1" max="5" step="0.5" value={form.retryConfig.backoffFactor} onChange={(e) => update('retryConfig', { ...form.retryConfig, backoffFactor: parseFloat(e.target.value) || 1 })} className="w-16 px-2 py-1 rounded bg-slate-900/60 border border-white/10 text-sm text-center text-slate-200" />
              </div>
            </div>
          </div>
        </>)}

        {/* System Prompt */}
        {tab === 'system' && (
          <div>
            <label className={labelClass}>系统提示词</label>
            <textarea className={`${inputClass} h-80 font-mono text-xs resize-none`} value={form.systemPrompt} onChange={(e) => update('systemPrompt', e.target.value)} placeholder={`你是一个专业的代码审查助手。你的职责包括：\n1. 审查代码质量与安全性\n2. 给出改进建议\n3. 生成代码审查报告`} />
            {errors.systemPrompt && <p className="text-xs text-red-400 mt-1">{errors.systemPrompt}</p>}
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-slate-500">快速模板：</span>
              {['代码审查', '任务规划', '执行器', '评估器'].map((t) => (
                <button key={t} type="button" onClick={() => update('systemPrompt', `你是${t}专家，专注于高效准确地完成${t}相关任务。`)} className="px-2.5 py-1 text-xs rounded-full bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-white/5 transition-colors">{t}</button>
              ))}
            </div>
          </div>
        )}

        {/* Tools */}
        {tab === 'tools' && (<>
          <div>
            <label className={labelClass}>能力（多选）</label>
            <div className="grid grid-cols-2 gap-2">
              {AGENT_CAPABILITIES.map((cap) => (
                <button key={cap.value} type="button" onClick={() => toggleCap(cap.value)} className={`p-2.5 rounded-lg text-xs text-left border transition-all ${form.capabilities.includes(cap.value) ? 'border-emerald-400/60 bg-emerald-400/10 text-emerald-300' : 'border-white/5 bg-slate-900/30 text-slate-500 hover:border-white/15'}`}>
                  <div className="font-medium">{cap.label}</div><div className="opacity-60 mt-0.5 text-[10px]">{cap.desc}</div>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className={labelClass}>自定义工具</label>
            <textarea className={`${inputClass} h-24 font-mono text-xs resize-none`} placeholder='[{"name": "my_tool", "description": "...", "parameters": {...}}]' />
          </div>
        </>)}
      </div>

      {/* Footer */}
      <div className="flex gap-2.5 px-5 py-3.5 border-t border-white/5 bg-slate-900/30">
        <button onClick={onCancel} className="flex-1 px-4 py-2 rounded-lg bg-white/5 text-slate-300 hover:bg-white/10 text-sm">取消</button>
        <button onClick={handleSave} className="flex-1 px-4 py-2 rounded-lg bg-amber-400 text-slate-900 hover:bg-amber-300 font-semibold text-sm">{initial?.name ? '保存修改' : '创建Agent'}</button>
      </div>
    </div>
  );
};

export default AgentForm;
