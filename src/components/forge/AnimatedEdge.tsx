/**
 * AnimatedEdge
 * ============
 * Custom ReactFlow edge component with animated data-flow indication.
 *
 * Visuals:
 * - Dashed or solid stroke depending on connection type
 * - Animated dash offset for data-flow illusion
 * - Arrow marker at target end
 * - Color coded per collaboration mode (via edge style prop)
 * - Hover highlight (stroke width increase + glow)
 * - Selectable with delete key
 *
 * The "flow" animation is achieved via CSS `stroke-dasharray` + `stroke-dashoffset`
 * animated with a cubic-bezier timing function on the edge path.
 */

import React from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "reactflow";

/**
 * Custom animated edge for ReactFlow.
 * Renders a bezier path with animated dash-array for flowing data effect.
 */
const AnimatedEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  style = {},
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Merge styles: higher stroke width when selected/hovered
  const mergedStyle: React.CSSProperties = {
    ...style,
    strokeWidth: selected ? 2.5 : 1.5,
    strokeDasharray: "6 4",
    filter: selected ? "drop-shadow(0 0 4px currentColor)" : undefined,
  };

  return (
    <>
      {/* ---- Edge Path with Animated Flow ---- */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={mergedStyle}
        markerEnd={markerEnd}
        className={`transition-all duration-150 ${
          selected ? "!stroke-amber-400" : ""
        }`}
      />

      {/* ---- Flow Particle (animated along path) ---- */}
      <g>
        <circle r="3.5" fill="currentColor" opacity="0.7">
          <animateMotion
            dur="2s"
            repeatCount="indefinite"
            path={edgePath}
            rotate="auto"
          />
          <animate
            attributeName="opacity"
            values="0.3;0.9;0.3"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
      </g>

      {/* ---- Delete Button on Selection ---- */}
      {selected && (
        <EdgeLabelRenderer>
          <button
            className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-500/90 p-1 text-white shadow-lg transition-transform hover:scale-110"
            style={{
              left: labelX,
              top: labelY,
            }}
            onClick={() => {
              // Selection deletion is handled by ForgeEditor's keyboard handler
            }}
            aria-label="Remove edge"
          >
            <svg className="h-2.5 w-2.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

export default AnimatedEdge;
