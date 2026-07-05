/**
 * Toast
 * =====
 * Auto-dismissing notification toast system.
 *
 * Features:
 * - Four types: success, error, warning, info
 * - Auto-dismiss after configurable duration (default 4s)
 * - Manual close button
 * - Stack multiple toasts (bottom-right)
 * - Animated entrance/exit
 *
 * Design: Dark panel with colored left border for type indication.
 * Uses a global toast store pattern for programmatic triggering.
 */

import React, {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

const ToastIcon: React.FC<{ type: ToastType; className?: string }> = ({
  type,
  className = "",
}) => {
  const paths: Record<ToastType, string> = {
    success:
      "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z",
    error:
      "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z",
    warning:
      "M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 012 0v4a1 1 0 11-2 0V9zm1 7a1 1 0 100-2 1 1 0 000 2z",
    info: "M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v4a1 1 0 102 0V7zm-1 7a1 1 0 100-2 1 1 0 000 2z",
  };

  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d={paths[type]} clipRule="evenodd" />
    </svg>
  );
};

const CloseSmallIcon: React.FC<{ className?: string }> = ({
  className = "",
}) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
      clipRule="evenodd"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ToastType = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  /** Optional description line */
  description?: string;
  /** Duration in ms before auto-dismiss (0 = manual only) */
  duration: number;
  /** Whether toast is exiting */
  exiting?: boolean;
}

interface ToastContextValue {
  addToast: (
    type: ToastType,
    message: string,
    description?: string,
    duration?: number
  ) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Hook to access the toast system from any component.
 *
 * @example
 * ```tsx
 * const { addToast } = useToast();
 * addToast("success", "Project created");
 * ```
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    // Fallback for outside provider: silent no-op
    return { addToast: () => {} };
  }
  return context;
}

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const TYPE_STYLES: Record<
  ToastType,
  { border: string; iconColor: string }
> = {
  success: { border: "border-l-emerald-500", iconColor: "text-emerald-400" },
  error: { border: "border-l-red-500", iconColor: "text-red-400" },
  warning: { border: "border-l-amber-500", iconColor: "text-amber-400" },
  info: { border: "border-l-blue-500", iconColor: "text-blue-400" },
};

// ---------------------------------------------------------------------------
// Toast Container
// ---------------------------------------------------------------------------

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onDismiss,
}) => {
  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col-reverse gap-2" aria-live="polite">
      {toasts.map((toast) => {
        const style = TYPE_STYLES[toast.type];

        return (
          <div
            key={toast.id}
            className={`flex w-80 items-start gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 shadow-2xl shadow-black/50 ${style.border} ${
              toast.exiting
                ? "animate-out fade-out slide-out-to-right duration-200"
                : "animate-in fade-in slide-in-from-right duration-200"
            }`}
            role="alert"
          >
            <ToastIcon type={toast.type} className={`mt-0.5 h-4 w-4 shrink-0 ${style.iconColor}`} />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-slate-200">
                {toast.message}
              </p>
              {toast.description && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">
                  {toast.description}
                </p>
              )}
            </div>
            <button
              onClick={() => onDismiss(toast.id)}
              className="shrink-0 rounded p-0.5 text-slate-600 transition-colors hover:text-slate-400"
              aria-label="Dismiss"
            >
              <CloseSmallIcon className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>,
    document.body
  );
};

// ---------------------------------------------------------------------------
// Toast Provider
// ---------------------------------------------------------------------------

let toastIdCounter = 0;

interface ToastProviderProps {
  children: React.ReactNode;
}

/**
 * Toast provider component. Wrap your app to enable toast notifications.
 *
 * @example
 * ```tsx
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 * ```
 */
export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback(
    (
      type: ToastType,
      message: string,
      description?: string,
      duration: number = 4000
    ) => {
      const id = `toast-${++toastIdCounter}`;

      setToasts((prev) => [
        ...prev,
        { id, type, message, description, duration },
      ]);

      if (duration > 0) {
        setTimeout(() => dismissToast(id), duration);
      }
    },
    []
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
    );
    // Remove from DOM after animation
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 250);
  }, []);

  const contextValue: ToastContextValue = { addToast };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
};

export default ToastProvider;
