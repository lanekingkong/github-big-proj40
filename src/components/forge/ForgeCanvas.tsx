/**
 * ForgeCanvas
 * ===========
 * ReactFlow-based canvas for visual agent orchestration.
 *
 * Features:
 * - Custom node type: AgentNode
 * - Custom edge type: AnimatedEdge
 * - Background dots grid pattern
 * - Minimap (bottom-right)
 * - Zoom controls (fitted into toolbar, but scale indicator here)
 * - Snap-to-grid (16px grid)
 * - Connection line styling
 *
 * This component renders the ReactFlow instance with all custom types
 * registered. It receives node/edge state and callbacks from ForgeEditor.
 */

import React, { useMemo, useCallback } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  MiniMap,
  Controls,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type ConnectionLineComponentProps,
  MarkerType,
  Panel,
} from "reactflow";
import AgentNode from "./AgentNode";
import AnimatedEdge from "./AnimatedEdge";
import type { CollaborationMode } from "./ForgeEditor";

// ---------------------------------------------------------------------------
// Custom Node/Edge Types (memoized)
// ---------------------------------------------------------------------------

const nodeTypes = { agentNode: AgentNode };
const edgeTypes = { animated: AnimatedEdge };

// ---------------------------------------------------------------------------
// Default Edge Options (per collaboration mode)
// ---------------------------------------------------------------------------

const MODE_EDGE_COLORS: Record<CollaborationMode, string> = {
  sequential: "#3b82f6",   // blue-500
  parallel: "#10b981",     // emerald-500
  review_loop: "#f59e0b",  // amber-500
  committee: "#8b5cf6",    // violet-500
};

// ---------------------------------------------------------------------------
// MiniMap Styles
// ---------------------------------------------------------------------------

const minimapStyle: React.CSSProperties = {
  height: 120,
  borderRadius: 8,
  border: "1px solid rgb(30 41 59)",
  backgroundColor: "rgb(15 23 42)",
};

// ---------------------------------------------------------------------------
// Connection Line (drawing while connecting)
// ---------------------------------------------------------------------------

const ConnectionLine: React.FC<ConnectionLineComponentProps> = ({
  fromX,
  fromY,
  toX,
  toY,
}) => {
  return (
    <g>
      <path
        fill="none"
        stroke="rgb(245 158 11)"
        strokeWidth={1.5}
        strokeDasharray="5 4"
        className="animate-pulse"
        d={`M${fromX},${fromY} C ${fromX + 50},${fromY} ${toX - 50},${toY} ${toX},${toY}`}
      />
      <circle
        cx={toX}
        cy={toY}
        r={4}
        fill="rgb(245 158 11)"
        className="animate-pulse"
      />
    </g>
  );
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ForgeCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  mode: CollaborationMode;
}

/**
 * ReactFlow canvas component for the Forge editor.
 */
const ForgeCanvas: React.FC<ForgeCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  mode,
}) => {
  const strokeColor = MODE_EDGE_COLORS[mode] || MODE_EDGE_COLORS.sequential;

  const defaultEdgeOptions = useMemo(
    () => ({
      type: "animated",
      animated: true,
      style: { stroke: strokeColor, strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: strokeColor,
        width: 16,
        height: 16,
      },
    }),
    [strokeColor]
  );

  // Snap-to-grid
  const snapGrid: [number, number] = [16, 16];

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      defaultEdgeOptions={defaultEdgeOptions}
      connectionLineComponent={ConnectionLine}
      snapToGrid={true}
      snapGrid={snapGrid}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      deleteKeyCode={["Delete", "Backspace"]}
      multiSelectionKeyCode="Shift"
      selectionKeyCode="Shift"
      panOnScroll
      minZoom={0.1}
      maxZoom={4}
      className="bg-slate-950"
      proOptions={{ hideAttribution: true }}
    >
      {/* ---- Background Grid ---- */}
      <Background
        variant={BackgroundVariant.Dots}
        gap={20}
        size={1}
        color="rgb(30 41 59)"
      />

      {/* ---- MiniMap ---- */}
      <MiniMap
        style={minimapStyle}
        nodeColor={(n) => {
          const status = (n.data as any)?.status;
          switch (status) {
            case "online": return "rgb(16 185 129)";
            case "busy": return "rgb(245 158 11)";
            case "error": return "rgb(239 68 68)";
            default: return "rgb(100 116 139)";
          }
        }}
        maskColor="rgb(15 23 42 / 0.8)"
      />

      {/* ---- Controls ---- */}
      <Controls
        className="[&>button]:bg-slate-900 [&>button]:border-slate-700 [&>button]:text-slate-400 [&>button]:fill-slate-400 [&>button:hover]:bg-slate-800 [&>button:hover]:text-slate-200"
        position="bottom-right"
        showInteractive={false}
      />

      {/* ---- Zoom indicator ---- */}
      <Panel position="bottom-left" className="m-0">
        <span className="select-none rounded-md bg-slate-900/80 px-2 py-1 text-[10px] font-mono text-slate-600 backdrop-blur">
          {/* Zoom level would be read from ReactFlow instance */}
          {nodes.length} agents · {edges.length} connections
        </span>
      </Panel>

      {/* ---- Empty State ---- */}
      {nodes.length === 0 && (
        <Panel position="top-center" className="pointer-events-none mt-16">
          <div className="text-center">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgb(71 85 105)"
              strokeWidth={0.8}
              className="mx-auto mb-3 h-12 w-12"
            >
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <path d="M8 12h8M12 8v8" />
            </svg>
            <p className="text-xs text-slate-600">
              Drag agents from the left panel onto this canvas
            </p>
            <p className="mt-1 text-[10px] text-slate-700">
              Connect them to build your collaboration pipeline
            </p>
          </div>
        </Panel>
      )}
    </ReactFlow>
  );
};

export default ForgeCanvas;
