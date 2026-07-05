/**
 * TaskTimeline - 任务时间线组件
 * 以甘特图风格展示流水线中每个任务/Agent的执行时序和耗时
 */
import React, { useMemo } from 'react';

interface TaskEvent {
  id: string;
  agentName: string;
  agentId: string;
  task: string;
  startTime: Date;
  endTime?: Date;
  status: 'pending' | 'running' | 'completed' | 'failed';
  toolCalls: number;
  tokensUsed: number;
}

interface Props {
  events: TaskEvent[];
  totalDuration?: number; // ms
  compact?: boolean;
  onSelect?: (event: TaskEvent) => void;
}

const TaskTimeline: React.FC<Props> = ({ events, totalDuration: propDuration, compact = false, onSelect }) => {
  const totalDuration = useMemo(() =>
    propDuration || Math.max(...events.map((e) => (e.endTime || new Date()).getTime() - e.startTime.getTime()), 1),
  [events, propDuration]);

  const sorted = useMemo(() => [...events].sort((a, b) => a.startTime.getTime() - b.startTime.getTime()), [events]);

  const colors: Record<string, string> = {
    completed: 'bg-emerald-400/80', running: 'bg-blue-400/80', failed: 'bg-red-400/80', pending: 'bg-slate-600/50',
  };
  const statusText: Record<string, string> = {
    completed: '完成', running: '执行中', failed: '失败', pending: '等待',
  };
  const statusColor: Record<string, string> = {
    completed: 'text-emerald-400', running: 'text-blue-400', failed: 'text-red-400', pending: 'text-slate-500',
  };

  if (events.length === 0) {
    return <div className="flex items-center justify-center h-full text-slate-600 text-sm">暂无任务记录</div>;
  }

  return (
    <div className={`${compact ? 'text-xs' : 'text-sm'} h-full overflow-auto custom-scrollbar`}>
      {sorted.map((ev, i) => {
        const offset = ((ev.startTime.getTime() - sorted[0].startTime.getTime()) / totalDuration) * 100;
        const width = Math.max(((ev.endTime || new Date()).getTime() - ev.startTime.getTime()) / totalDuration * 100, 2);
        const dur = ev.endTime ? ((ev.endTime.getTime() - ev.startTime.getTime()) / 1000).toFixed(1) + 's' : '进行中';

        return (
          <div key={ev.id} className="group border-b border-white/[0.03] last:border-0" onClick={() => onSelect?.(ev)}>
            <div className={`flex items-center gap-3 px-4 py-2.5 ${onSelect ? 'cursor-pointer hover:bg-white/[0.03]' : ''}`}>
              {/* Agent名称 + 状态 */}
              <div className="w-28 shrink-0">
                <div className="font-medium text-slate-200 truncate">{ev.agentName}</div>
                <span className={`text-xs ${statusColor[ev.status]}`}>{statusText[ev.status]}</span>
              </div>

              {/* 甘特条 */}
              <div className="flex-1 h-7 bg-slate-900/60 rounded-full relative overflow-hidden border border-white/5">
                {/* 网格线 */}
                {Array.from({ length: 10 }).map((_, gi) => (
                  <div key={gi} className="absolute top-0 bottom-0 w-px bg-white/[0.04]" style={{ left: `${gi * 10}%` }}/>
                ))}
                {/* 任务条 */}
                <div className="absolute top-1 bottom-1 rounded-full transition-all" style={{ left: `${offset}%`, width: `${width}%` }}>
                  <div className={`h-full rounded-full ${colors[ev.status]} group-hover:brightness-110 transition-all`} style={{ minWidth: 4 }}/>
                </div>
              </div>

              {/* 指标 */}
              <div className="flex items-center gap-4 text-xs text-slate-500 shrink-0">
                <span className="tabular-nums">{dur}</span>
                <span title="工具调用次数">{ev.toolCalls} 调用</span>
                <span title="Token消耗">{ev.tokensUsed.toLocaleString()} tokens</span>
              </div>
            </div>

            {/* 展开详情 */}
            {!compact && (
              <div className="px-4 pb-2.5 pl-36">
                <p className="text-xs text-slate-500 truncate">{ev.task}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TaskTimeline;
