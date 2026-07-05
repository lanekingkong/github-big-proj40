/**
 * useForge - Forge 画布状态管理 Hook
 * 封装 React Flow 节点/边操作 + 历史栈（撤销/重做）
 */
import { useState, useCallback, useRef } from 'react';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from '@xyflow/react';
import type { ForgeNode } from '../types/forge';

interface HistoryEntry { nodes: Node[]; edges: Edge[] }

interface UseForgeReturn {
  nodes: Node[];
  edges: Edge[];
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: Node) => void;
  removeNode: (id: string) => void;
  updateNode: (id: string, data: Partial<Node['data']>) => void;
  clear: () => void;
  undo: () => void;
  redo: () => void;
  save: () => void;
  exportJSON: () => string;
  importJSON: (json: string) => void;
  canUndo: boolean;
  canRedo: boolean;
}

const MAX_HISTORY = 50;

export function useForge(initialNodes: Node[] = [], initialEdges: Edge[] = []): UseForgeReturn {
  const [nodes, setNodesState] = useState<Node[]>(initialNodes);
  const [edges, setEdgesState] = useState<Edge[]>(initialEdges);
  const historyRef = useRef<HistoryEntry[]>([{ nodes: initialNodes, edges: initialEdges }]);
  const historyIdxRef = useRef(0);
  const canUndo = historyIdxRef.current > 0;
  const canRedo = historyIdxRef.current < historyRef.current.length - 1;

  const pushHistory = useCallback((n: Node[], e: Edge[]) => {
    historyRef.current = [...historyRef.current.slice(0, historyIdxRef.current + 1), { nodes: n, edges: e }].slice(-MAX_HISTORY);
    historyIdxRef.current = historyRef.current.length - 1;
  }, []);

  const setNodes = useCallback((n: Node[]) => { setNodesState(n); pushHistory(n, edges); }, [edges, pushHistory]);

  const setEdges = useCallback((e: Edge[]) => { setEdgesState(e); pushHistory(nodes, e); }, [nodes, pushHistory]);

  const onNodesChange: any = useCallback((changes: NodeChange[]) => {
    setNodesState((nds) => {
      let result = nds;
      changes.forEach((ch) => {
        if (ch.type === 'remove' && ch.id) result = result.filter((n) => n.id !== ch.id);
      });
      return result;
    });
  }, []);

  const onEdgesChange: any = useCallback((changes: EdgeChange[]) => {
    setEdgesState((eds) => {
      let result = eds;
      changes.forEach((ch) => {
        if (ch.type === 'remove' && ch.id) result = result.filter((e) => e.id !== ch.id);
      });
      return result;
    });
  }, []);

  const onConnect = useCallback((conn: Connection) => {
    const id = `edge_${Date.now()}`;
    setEdgesState((eds) => [...eds, { id, source: conn.source, target: conn.target, sourceHandle: conn.sourceHandle, targetHandle: conn.targetHandle, animated: true, style: { stroke: '#f59e0b80', strokeWidth: 2 } }]);
  }, []);

  const addNode = useCallback((node: Node) => { setNodesState((nds) => [...nds, node]); pushHistory([...nodes, node], edges); }, [nodes, edges, pushHistory]);

  const removeNode = useCallback((id: string) => {
    setNodesState((nds) => nds.filter((n) => n.id !== id));
    setEdgesState((eds) => eds.filter((e) => e.source !== id && e.target !== id));
  }, []);

  const updateNode = useCallback((id: string, data: Partial<Node['data']>) => {
    setNodesState((nds) => nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...data } } : n)));
  }, []);

  const clear = useCallback(() => { setNodesState([]); setEdgesState([]); pushHistory([], []); }, [pushHistory]);

  const undo = useCallback(() => {
    if (historyIdxRef.current > 0) {
      historyIdxRef.current--;
      const entry = historyRef.current[historyIdxRef.current];
      setNodesState(entry.nodes); setEdgesState(entry.edges);
    }
  }, []);

  const redo = useCallback(() => {
    if (historyIdxRef.current < historyRef.current.length - 1) {
      historyIdxRef.current++;
      const entry = historyRef.current[historyIdxRef.current];
      setNodesState(entry.nodes); setEdgesState(entry.edges);
    }
  }, []);

  const save = useCallback(() => window.dispatchEvent(new CustomEvent('forge:save', { detail: { nodes, edges } })), [nodes, edges]);

  const exportJSON = useCallback(() => JSON.stringify({ version: 1, nodes, edges }, null, 2), [nodes, edges]);

  const importJSON = useCallback((json: string) => {
    const data = JSON.parse(json);
    if (data.nodes) { setNodesState(data.nodes); setEdgesState(data.edges || []); pushHistory(data.nodes, data.edges || []); }
  }, [pushHistory]);

  return { nodes, edges, setNodes, setEdges, onNodesChange, onEdgesChange, onConnect, addNode, removeNode, updateNode, clear, undo, redo, save, exportJSON, importJSON, canUndo, canRedo };
}
