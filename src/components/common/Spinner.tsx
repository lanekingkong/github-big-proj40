/**
 * Spinner
 * =======
 * Minimal loading spinner with configurable size.
 *
 * Sizes:
 * - sm : 16x16 (inline, icon-sized)
 * - md : 24x24 (default, card/block)
 * - lg : 40x40 (full-page placeholder)
 *
 * Design: Custom SVG spinner with dual-ring effect.
 * Dark theme native (uses currentColor).
 */

import React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SpinnerSize = "sm" | "md" | "lg";

interface SpinnerProps {
  /** Spinner size */
  size?: SpinnerSize;
  /** Optional className */
  className?: string;
  /** Accessible label */
  label?: string;
}

// ---------------------------------------------------------------------------
// Size map
// ---------------------------------------------------------------------------

const SIZE_CLASSES: Record<SpinnerSize, string> = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-10 w-10",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Loading spinner component.
 *
 * @example
 * ```tsx
 * <Spinner size="md" label="Loading projects..." />
 * ```
 */
const Spinner: React.FC<SpinnerProps> = ({
  size = "md",
  className = "",
  label,
}) => {
  return (
    <div
      className={`inline-flex flex-col items-center gap-2 ${className}`}
      role="status"
      aria-label={label || "Loading"}
    >
      <svg
        className={`animate-spin ${SIZE_CLASSES[size]} text-slate-400`}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Outer ring */}
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="2.5"
          className="opacity-20"
        />
        {/* Spinning arc */}
        <path
          d="M12 2a10 10 0 019.95 9"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          className="origin-center"
        />
        {/* Inner counter-spin ring for visual depth */}
        <circle
          cx="12"
          cy="12"
          r="5"
          stroke="currentColor"
          strokeWidth="1.5"
          className="animate-[spin_0.8s_linear_reverse_infinite] opacity-30"
        />
      </svg>
      {label && (
        <span className="text-[11px] text-slate-500">{label}</span>
      )}
    </div>
  );
};

export default Spinner;
