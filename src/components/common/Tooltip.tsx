/**
 * Tooltip
 * =======
 * Simple tooltip component that appears on hover/focus.
 *
 * Features:
 * - Four placements: top, bottom, left, right
 * - Configurable delay before showing
 * - Portal rendering to avoid overflow clipping
 * - Clean animation (fade + slight slide)
 *
 * Design: Dark slate-900 panel, small text, subtle border.
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TooltipPlacement = "top" | "bottom" | "left" | "right";

interface TooltipProps {
  /** Content shown inside the tooltip */
  content: React.ReactNode;
  /** Trigger element that activates the tooltip */
  children: React.ReactNode;
  /** Preferred placement */
  placement?: TooltipPlacement;
  /** Delay before showing (ms) */
  delay?: number;
  /** Optional className */
  className?: string;
  /** Whether the tooltip is disabled */
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Position calculation
// ---------------------------------------------------------------------------

const OFFSET = 8;

function computePosition(
  triggerRect: DOMRect,
  tooltipRect: DOMRect,
  placement: TooltipPlacement
): { top: number; left: number } {
  const { top, left, width, height } = triggerRect;

  switch (placement) {
    case "top":
      return {
        top: top - tooltipRect.height - OFFSET,
        left: left + width / 2 - tooltipRect.width / 2,
      };
    case "bottom":
      return {
        top: top + height + OFFSET,
        left: left + width / 2 - tooltipRect.width / 2,
      };
    case "left":
      return {
        top: top + height / 2 - tooltipRect.height / 2,
        left: left - tooltipRect.width - OFFSET,
      };
    case "right":
      return {
        top: top + height / 2 - tooltipRect.height / 2,
        left: left + width + OFFSET,
      };
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Tooltip component.
 *
 * @example
 * ```tsx
 * <Tooltip content="Delete file" placement="top">
 *   <button>🗑</button>
 * </Tooltip>
 * ```
 */
const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  placement = "top",
  delay = 400,
  className = "",
  disabled = false,
}) => {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const show = useCallback(() => {
    timerRef.current = setTimeout(() => {
      setVisible(true);
    }, delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = undefined;
    }
    setVisible(false);
  }, []);

  // Calculate position when visible
  useEffect(() => {
    if (!visible || !triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const pos = computePosition(triggerRect, tooltipRect, placement);

    // Clamp to viewport
    const clamped = {
      top: Math.max(4, Math.min(window.innerHeight - tooltipRect.height - 4, pos.top)),
      left: Math.max(4, Math.min(window.innerWidth - tooltipRect.width - 4, pos.left)),
    };

    setCoords(clamped);
  }, [visible, placement]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (disabled) return <>{children}</>;

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        className="inline-flex"
      >
        {children}
      </div>

      {visible &&
        createPortal(
          <div
            ref={tooltipRef}
            role="tooltip"
            className={`pointer-events-none fixed z-[100] animate-in fade-in slide-in-from-bottom-1 duration-150 ${className}`}
            style={{ top: coords.top, left: coords.left }}
          >
            <div className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 shadow-xl shadow-black/40">
              <span className="text-[11px] leading-none text-slate-300">
                {content}
              </span>
            </div>
          </div>,
          document.body
        )}
    </>
  );
};

export default Tooltip;
