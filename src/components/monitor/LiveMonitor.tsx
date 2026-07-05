/**
 * LiveMonitor - 流水线实时监控面板
 * 展示正在运行流水线的实时日志、Agent状态、进度指标
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  agentName: string;
  message: string;
}

interface AgentStatus {
  agentId: string;
  agentName: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  startTime?: string;
  elapsed?: number;
}

interface Props {
  runId: string;
  projectName: string;
  onClose: () => void;
  onAbort: () => void;
}

const LiveMonitor: React.FC<Props> = ({ runId, projectName, onClose, onAbort }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [globalProgress, setGlobalProgress] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState<'running' | 'completed' | 'failed'>('running');
  const logEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const { connected, send } = useWebSocket({
    url: `ws://localhost:8899/ws/pipeline/${runId}`,
    onMessage: useCallback((data: any) => {
      if (data.type === 'log') {
        setLogs((prev) => [...prev.slice(-499), { timestamp: new Date().toISOString(), ...data.payload }]);
      } else if (data.type === 'agent_status') {
        setAgents((prev) => {
          const idx = prev.findIndex((a) => a.agentId === data.payload.agentId);
          if (idx >= 0) { const next = [...prev]; next[idx] = { ...next[idx], ...data.payload }; return next; }
          return [...prev, data.payload];
        });
      } else if (data.type === 'progress') {
        setGlobalProgress(data.payload.progress);
      } else if (data.type === 'complete') {
        setStatus(data.payload.success ? 'completed' : 'failed');
        setGlobalProgress(1);
      }
    }, []),
  });

  useEffect(() => { const t = setInterval(() => setElapsed((p) => p + 1), 1000); return () => clearInterval(t); }, []);

  useEffect(() => { if (autoScroll) logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs, autoScroll]);

  const levelStyle = (level: string) => ({
    info: 'text-slate-300', warn: 'text-amber-400', error: 'text-red-400', debug: 'text-slate-500',
  }[level] || 'text-slate-300');

  const statusColor = (s: string) => ({ idle: 'text-slate-500', running: 'text-blue-400', completed: 'text-emerald-400', failed: 'text-red-400' }[s] || 'text-slate-500');

  const formatElapsed = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-slate-800 border border-white/10 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/5">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold text-white">{projectName}</h2>
            <span className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${status === 'running' ? 'bg-blue-400 animate-pulse' : status === 'completed' ? 'bg-emerald-400' : 'bg-red-400'}`}/>
              <span className="text-xs text-slate-400">{status === 'running' ? '运行中' : status === 'completed' ? '已完成' : '失败'}</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 tabular-nums">{connected ? '已连接' : '断开'}</span>
            <span className="text-xs text-slate-500">{formatElapsed(elapsed)}</span>
            <div className="w-px h-5 bg-white/10"/>
            {status === 'running' && <button onClick={onAbort} className="px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 text-xs font-medium transition-colors">中止</button>}
            <button onClick={onClose} className="text-slate-400 hover:text-white"><svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M6 18L18 6M6 6l12 12"/></svg></button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-1 bg-slate-900">
          <div className={`h-full transition-all duration-500 rounded-r ${status === 'completed' ? 'bg-emerald-400' : status === 'failed' ? 'bg-red-400' : 'bg-amber-400'}`} style={{ width: `${Math.round(globalProgress * 100)}%` }}/>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Agent Status Panel */}
          <div className="w-64 border-r border-white/5 p-3 space-y-2 overflow-y-auto custom-scrollbar">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Agent 状态</h3>
            {agents.length === 0 && <p className="text-xs text-slate-600 text-center py-4">等待启动...</p>}
            {agents.map((a) => (
              <div key={a.agentId} className="p-2.5 rounded-lg bg-slate-900/40 border border-white/5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-slate-300 truncate">{a.agentName}</span>
                  <span className={`text-[10px] font-medium ${statusColor(a.status)}`}>{a.status}</span>
                </div>
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-300 ${a.status === 'completed' ? 'bg-emerald-400' : a.status === 'failed' ? 'bg-red-400' : 'bg-blue-400'}`} style={{ width: `${Math.round(a.progress * 100)}%` }}/>
                </div>
              </div>
            ))}
          </div>

          {/* Log Panel */}
          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">运行日志</h3>
              <div className="flex items-center gap-2">
                <button onClick={() => setAutoScroll(!autoScroll)} className={`px-2 py-1 rounded text-[10px] ${autoScroll ? 'bg-amber-400/10 text-amber-400' : 'bg-slate-800 text-slate-500'} transition-colors`}>自动滚动</button>
                <button onClick={() => setLogs([])} className="px-2 py-1 rounded text-[10px] bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors">清屏</button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto font-mono text-xs p-3 space-y-0.5 custom-scrollbar" style={{ lineHeight: '1.6' }}>
              {logs.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <span className="text-slate-600">等待日志输出...</span>
                </div>
              )}
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2 hover:bg-white/[0.02] px-1 py-0.5 rounded">
                  <span className="text-slate-600 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`shrink-0 w-10 ${levelStyle(log.level)}`}>[{log.level.toUpperCase()}]</span>
                  <span className="text-amber-400 shrink-0">[{log.agentName}]</span>
                  <span className={levelStyle(log.level)}>{log.message}</span>
                </div>
              ))}
              <div ref={logEndRef}/>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveMonitor;
