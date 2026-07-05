/**
 * ForgeToolbar - Forge 编排编辑器顶部工具栏
 * 提供保存/运行/撤销/重做/自动布局/清空/导入导出/缩放控制
 */
import React, { useState, useCallback } from 'react';
import { useReactFlow } from '@xyflow/react';
import dagre from 'dagre';
import RunDialog from './RunDialog';
import { useForgeStore } from '../../stores/forgeStore';
import type { ForgeNode } from '../../types/forge';

interface Props { projectName?: string }

const ForgeToolbar: React.FC<Props> = ({ projectName = 'Unnamed' }) => {
  const { fitView, zoomIn, zoomOut, zoomTo, getZoom } = useReactFlow();
  const { nodes, edges } = useForgeStore((s) => ({ nodes: s.nodes, edges: s.edges }));
  const [showRunDialog, setShowRunDialog] = useState(false);

  const handleAutoLayout = useCallback(() => {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 120 });
    nodes.forEach((n: any) => g.setNode(n.id, { width: 220, height: 100 }));
    edges.forEach((e: any) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    const layouted = nodes.map((n: any) => {
      const pos = g.node(n.id);
      return { ...n, position: { x: pos.x - 110, y: pos.y - 50 } };
    });
    useForgeStore.getState().setNodes(layouted);
    fitView({ duration: 400 });
  }, [nodes, edges, fitView]);

  const handleClear = () => { if (window.confirm('清空画布将删除所有节点和连线，确认？')) useForgeStore.getState().clear(); };

  const handleImport = () => {
    const input = document.createElement('input'); input.type = 'file'; input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const r = new FileReader();
      r.onload = () => { try { useForgeStore.getState().importJSON(r.result as string); } catch { alert('导入失败'); } };
      r.readAsText(file);
    };
    input.click();
  };

  const handleExport = () => {
    const json = useForgeStore.getState().exportJSON();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${projectName}-forge.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const btn = 'flex items-center justify-center w-9 h-9 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors';

  return (<>
    <div className="flex items-center gap-1 px-3 py-2 bg-slate-900/95 border-b border-white/5">
      <button title="保存 (Ctrl+S)" className={btn} onClick={() => useForgeStore.getState().save()}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg></button>
      <button title="运行流水线" className={`${btn} text-emerald-400 hover:text-emerald-300`} onClick={() => setShowRunDialog(true)}><svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>
      <div className="w-px h-6 bg-white/10 mx-1"/>
      <button title="撤销" className={btn} onClick={() => useForgeStore.getState().undo()}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg></button>
      <button title="重做" className={btn} onClick={() => useForgeStore.getState().redo()}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6"/></svg></button>
      <div className="w-px h-6 bg-white/10 mx-1"/>
      <button title="自动布局" className={btn} onClick={handleAutoLayout}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg></button>
      <button title="清空画布" className={`${btn} text-red-400 hover:text-red-300`} onClick={handleClear}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
      <div className="w-px h-6 bg-white/10 mx-1"/>
      <button title="导入JSON" className={btn} onClick={handleImport}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg></button>
      <button title="导出JSON" className={btn} onClick={handleExport}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"/></svg></button>
      <div className="flex-1"/>
      <button title="缩小" className={btn} onClick={() => zoomOut({ duration: 200 })}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><path d="M8 12h8"/></svg></button>
      <span className="text-xs text-slate-400 w-10 text-center tabular-nums">{Math.round(getZoom() * 100)}%</span>
      <button title="放大" className={btn} onClick={() => zoomIn({ duration: 200 })}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg></button>
      <button title="适应视图" className={btn} onClick={() => fitView({ duration: 300 })}><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg></button>
    </div>
    {showRunDialog && <RunDialog projectName={projectName} nodes={nodes} onClose={() => setShowRunDialog(false)} onConfirm={() => { setShowRunDialog(false); }} />}
  </>);
};

export default ForgeToolbar;
