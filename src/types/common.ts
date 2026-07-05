/**
 * Common Type Definitions
 * =======================
 * Shared types used across the entire AgentForge frontend.
 *
 * Includes API response wrappers, pagination, logging, metrics,
 * theme configuration, and utility generics.
 */

// ---------------------------------------------------------------------------
// API Response
// ---------------------------------------------------------------------------

/**
 * Standard API response wrapper from the Python FastAPI backend.
 * All endpoints return this structure for consistency.
 *
 * @template T — The payload type
 */
export interface ApiResponse<T = unknown> {
  /** Whether the request was successful */
  success: boolean;

  /** Response payload (present on success) */
  data?: T;

  /** Error message (present on failure) */
  error?: string;

  /** Error code for programmatic handling */
  errorCode?: string;

  /** Request tracing ID for debugging */
  traceId?: string;

  /** Response timestamp (ISO 8601) */
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

/**
 * Pagination parameters for list endpoints.
 * Used as query parameters in GET requests.
 */
export interface PaginationParams {
  /** Page number (1-based) */
  page: number;

  /** Number of items per page */
  pageSize: number;

  /** Field to sort by */
  sortBy?: string;

  /** Sort direction */
  sortOrder?: "asc" | "desc";
}

/**
 * Paginated response metadata, returned alongside list data.
 */
export interface PaginationMeta {
  /** Current page number */
  page: number;

  /** Number of items per page */
  pageSize: number;

  /** Total number of items across all pages */
  totalItems: number;

  /** Total number of pages */
  totalPages: number;

  /** Whether there is a next page */
  hasNext: boolean;

  /** Whether there is a previous page */
  hasPrev: boolean;
}

/**
 * Generic paginated response wrapper.
 *
 * @template T — Item type
 */
export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

/**
 * Log severity levels.
 */
export enum LogLevel {
  Debug = "debug",
  Info = "info",
  Warn = "warn",
  Error = "error",
  Fatal = "fatal",
}

/**
 * A single log entry from the backend or agent execution.
 */
export interface LogEntry {
  /** Unique log entry ID */
  id: string;

  /** Timestamp (ISO 8601) */
  timestamp: string;

  /** Severity level */
  level: LogLevel;

  /** Log message content */
  message: string;

  /** Source component or agent name */
  source: string;

  /** Optional structured metadata */
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// WebSocket Events
// ---------------------------------------------------------------------------

/**
 * WebSocket event types emitted by the backend.
 */
export enum WsEventType {
  /** Agent status changed */
  AgentStatus = "agent:status",

  /** Task status changed */
  TaskStatus = "task:status",

  /** Pipeline stage started/completed */
  PipelineStage = "pipeline:stage",

  /** New log entry */
  Log = "log:entry",

  /** Performance metric update */
  Metric = "metric:update",

  /** Heartbeat/ping */
  Heartbeat = "heartbeat",
}

/**
 * Generic WebSocket event envelope.
 *
 * @template P — Event payload type
 */
export interface WsEvent<P = unknown> {
  /** Event type identifier */
  type: WsEventType;

  /** Event payload */
  payload: P;

  /** Event timestamp (ISO 8601) */
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Performance Metrics
// ---------------------------------------------------------------------------

/**
 * A single performance metric data point.
 */
export interface MetricData {
  /** Metric name (e.g., "tokens_per_second", "task_latency_ms") */
  name: string;

  /** Numeric value */
  value: number;

  /** Unit of measurement */
  unit: string;

  /** Labels for categorization */
  labels: Record<string, string>;

  /** Timestamp of the measurement (ISO 8601) */
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Theme Configuration
// ---------------------------------------------------------------------------

/**
 * Theme mode options.
 */
export type ThemeMode = "light" | "dark" | "system";

/**
 * Persistent theme configuration.
 */
export interface ThemeConfig {
  /** Active theme mode */
  mode: ThemeMode;

  /** Primary color hue (0-360) */
  primaryHue: number;

  /** UI density preference */
  density: "compact" | "comfortable";

  /** Font size scale */
  fontSizeScale: number;
}

// ---------------------------------------------------------------------------
// Utility Types
// ---------------------------------------------------------------------------

/**
 * Makes all properties of T optional deeply (recursive partial).
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Extracts the resolved value type from a Promise.
 */
export type Awaited<T> = T extends Promise<infer U> ? U : T;

/**
 * A discriminated union key-value pair for filter controls.
 */
export interface FilterOption {
  key: string;
  value: string;
  label: string;
}

// ---------------------------------------------------------------------------
// Toast / Notification
// ---------------------------------------------------------------------------

/**
 * Toast notification types for the UI.
 */
export enum ToastType {
  Success = "success",
  Error = "error",
  Warning = "warning",
  Info = "info",
}

/**
 * A single toast notification.
 */
export interface Toast {
  /** Unique identifier */
  id: string;

  /** Toast type (controls color/icon) */
  type: ToastType;

  /** Title text */
  title: string;

  /** Optional body text */
  message?: string;

  /** Auto-dismiss duration in milliseconds (0 = manual dismiss only) */
  duration: number;

  /** Creation timestamp */
  createdAt: number;
}
