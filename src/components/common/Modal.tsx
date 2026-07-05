/**
 * Modal
 * =====
 * Accessible modal dialog with backdrop overlay and keyboard support.
 *
 * Features:
 * - ESC to close
 * - Click outside (backdrop) to close
 * - Focus trap (basic: focus first focusable element)
 * - Animated entrance/exit (fade + scale)
 * - Title, body content, and action footer slots
 *
 * Design: Dark backdrop blur, slate-900 panel with border, centered.
 */

import React, { useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Inline Icon
// ---------------------------------------------------------------------------

const CloseIcon: React.FC<{ className?: string }> = ({ className = "" }) => (
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

interface ModalProps {
  /** Whether the modal is visible */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Modal title */
  title?: string;
  /** Optional description text below title */
  description?: string;
  /** Modal body content */
  children: React.ReactNode;
  /** Footer action buttons (e.g. Confirm / Cancel) */
  footer?: React.ReactNode;
  /** Max width class (default: max-w-md) */
  maxWidth?: string;
  /** Disable backdrop click to close */
  closeOnBackdrop?: boolean;
  /** Disable ESC to close */
  closeOnEsc?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Modal dialog component. Renders via React Portal to document.body.
 *
 * @example
 * ```tsx
 * <Modal isOpen={open} onClose={() => setOpen(false)} title="Confirm">
 *   <p>Are you sure?</p>
 *   {{ footer: <Button>Yes</Button> }}
 * </Modal>
 * ```
 */
const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = "max-w-md",
  closeOnBackdrop = true,
  closeOnEsc = true,
}) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // ESC handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && closeOnEsc) {
        onClose();
      }
    },
    [onClose, closeOnEsc]
  );

  // Lock body scroll & add ESC listener
  useEffect(() => {
    if (!isOpen) return;

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleKeyDown]);

  // Focus first focusable element inside panel on open
  useEffect(() => {
    if (!isOpen || !panelRef.current) return;

    const timer = setTimeout(() => {
      const focusable = panelRef.current?.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      focusable?.focus();
    }, 100);

    return () => clearTimeout(timer);
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      {/* ---- Backdrop ---- */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={closeOnBackdrop ? onClose : undefined}
      />

      {/* ---- Panel ---- */}
      <div
        ref={panelRef}
        className={`relative w-full ${maxWidth} rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl shadow-black/50 animate-in zoom-in-95 fade-in duration-200`}
      >
        {/* ---- Header ---- */}
        {(title || description) && (
          <div className="border-b border-slate-800 px-6 py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                {title && (
                  <h2
                    id="modal-title"
                    className="text-sm font-semibold text-slate-200"
                  >
                    {title}
                  </h2>
                )}
                {description && (
                  <p className="mt-1 text-xs text-slate-500">{description}</p>
                )}
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1 text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-300"
                aria-label="Close modal"
              >
                <CloseIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* ---- Body ---- */}
        <div className="px-6 py-4">{children}</div>

        {/* ---- Footer ---- */}
        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-slate-800 px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
