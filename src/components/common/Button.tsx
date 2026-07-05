/**
 * Button
 * ======
 * Versatile button component with multiple variants, sizes, and states.
 *
 * Variants:
 * - primary   : Solid amber fill
 * - secondary : Slate fill
 * - outline   : Transparent with border
 * - ghost     : Transparent, shows background on hover
 * - danger    : Red-tinted fill
 *
 * Sizes:
 * - sm : Compact (h-7, text-[11px])
 * - md : Default (h-9, text-xs)
 * - lg : Large   (h-11, text-sm)
 *
 * States: loading, disabled, focus ring, active press
 *
 * Design: All states handled with Tailwind. Loading spinner replaces
 * children when loading=true. Supports iconBefore/iconAfter props.
 */

import React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant */
  variant?: ButtonVariant;
  /** Button size */
  size?: ButtonSize;
  /** Show loading spinner and disable interaction */
  loading?: boolean;
  /** Optional icon rendered before children */
  iconBefore?: React.ReactNode;
  /** Optional icon rendered after children */
  iconAfter?: React.ReactNode;
}

// ---------------------------------------------------------------------------
// Style Maps
// ---------------------------------------------------------------------------

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-amber-500 text-slate-950 hover:bg-amber-400 focus-visible:ring-amber-500/50 active:bg-amber-600",
  secondary:
    "bg-slate-800 text-slate-200 hover:bg-slate-700 focus-visible:ring-slate-600/50 active:bg-slate-700",
  outline:
    "border border-slate-700 bg-transparent text-slate-300 hover:border-slate-600 hover:bg-slate-900 focus-visible:ring-slate-600/50 active:bg-slate-800",
  ghost:
    "bg-transparent text-slate-400 hover:bg-slate-900 hover:text-slate-200 focus-visible:ring-slate-600/50 active:bg-slate-800",
  danger:
    "bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40 focus-visible:ring-red-500/30 active:bg-red-500/30",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-[11px] gap-1.5 rounded-md",
  md: "h-9 px-3.5 text-xs gap-2 rounded-lg",
  lg: "h-11 px-5 text-sm gap-2.5 rounded-lg",
};

const ICON_SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-5 w-5",
};

const SPINNER_SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-3 w-3",
  md: "h-3.5 w-3.5",
  lg: "h-4 w-4",
};

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------

const SpinnerSVG: React.FC<{ className?: string }> = ({ className = "" }) => (
  <svg
    className={`animate-spin ${className}`}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="3"
      className="opacity-25"
    />
    <path
      d="M4 12a8 8 0 018-8"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      className="opacity-75"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Button component.
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md" loading={false} onClick={handler}>
 *   Submit
 * </Button>
 * ```
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled = false,
      iconBefore,
      iconAfter,
      children,
      className = "",
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    const baseClasses =
      "inline-flex items-center justify-center font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950 select-none";

    const stateClasses = isDisabled
      ? "opacity-40 cursor-not-allowed"
      : "cursor-pointer active:scale-[0.97]";

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`${baseClasses} ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${stateClasses} ${className}`}
        {...rest}
      >
        {loading ? (
          <SpinnerSVG className={SPINNER_SIZE_CLASSES[size]} />
        ) : iconBefore ? (
          <span className={ICON_SIZE_CLASSES[size]}>{iconBefore}</span>
        ) : null}
        {children}
        {!loading && iconAfter && (
          <span className={ICON_SIZE_CLASSES[size]}>{iconAfter}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
