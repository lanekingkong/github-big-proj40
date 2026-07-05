/**
 * WebSocket Service
 * =================
 * Manages a persistent WebSocket connection to the Python backend
 * for real-time event streaming.
 *
 * Features:
 * - Automatic connection with exponential backoff reconnection
 * - Event subscription management
 * - Heartbeat / ping-pong keep-alive
 * - Typed event dispatching
 *
 * Events received:
 * - agent:status — Agent lifecycle changes
 * - task:status  — Task progress updates
 * - pipeline:stage — Pipeline stage transitions
 * - log:entry — Real-time log entries
 * - metric:update — Performance metric data points
 * - heartbeat — Connection health check
 */

import type { WsEvent, WsEventType } from "../types/common";
import type { AgentStatus } from "../types/agent";
import type { TaskStatus } from "../types/project";

// ---------------------------------------------------------------------------
// Event Payload Types
// ---------------------------------------------------------------------------

/**
 * Payload for agent:status events.
 */
export interface AgentStatusPayload {
  agentId: string;
  status: AgentStatus;
  previousStatus: AgentStatus;
  timestamp: string;
}

/**
 * Payload for task:status events.
 */
export interface TaskStatusPayload {
  taskId: string;
  projectId: string;
  agentId: string;
  status: TaskStatus;
  progress: number;
  currentStep: string;
  timestamp: string;
}

/**
 * Payload for pipeline:stage events.
 */
export interface PipelineStagePayload {
  projectId: string;
  runId: string;
  stageId: string;
  stageName: string;
  event: "started" | "completed" | "failed";
  timestamp: string;
}

/**
 * Payload for log:entry events.
 */
export interface LogEntryPayload {
  id: string;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  source: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

/**
 * Payload for metric:update events.
 */
export interface MetricPayload {
  name: string;
  value: number;
  unit: string;
  labels: Record<string, string>;
  timestamp: string;
}

/**
 * Union of all possible WebSocket event payloads.
 */
export type WsPayloadMap = {
  "agent:status": AgentStatusPayload;
  "task:status": TaskStatusPayload;
  "pipeline:stage": PipelineStagePayload;
  "log:entry": LogEntryPayload;
  "metric:update": MetricPayload;
  heartbeat: { timestamp: string };
};

// ---------------------------------------------------------------------------
// Event Listener Types
// ---------------------------------------------------------------------------

/** Callback type for a specific event type */
type EventListener<T extends WsEventType> = (payload: WsPayloadMap[T]) => void;

/** Subscription entry in the listener registry */
interface Subscription {
  type: WsEventType | "*";
  callback: EventListener<WsEventType>;
  id: string;
}

// ---------------------------------------------------------------------------
// Connection State
// ---------------------------------------------------------------------------

enum ConnectionState {
  Disconnected = "disconnected",
  Connecting = "connecting",
  Connected = "connected",
  Reconnecting = "reconnecting",
}

// ---------------------------------------------------------------------------
// WebSocketService Class
// ---------------------------------------------------------------------------

/**
 * Singleton WebSocket service managing the connection lifecycle
 * and event dispatching.
 */
class WebSocketService {
  /** Underlying WebSocket instance */
  private ws: WebSocket | null = null;

  /** Backend WebSocket endpoint URL */
  private url: string = "ws://127.0.0.1:18090/ws";

  /** Current connection state */
  private state: ConnectionState = ConnectionState.Disconnected;

  /** Registered event listeners */
  private listeners: Subscription[] = [];

  /** Reconnection attempt counter */
  private reconnectAttempts: number = 0;

  /** Maximum reconnection attempts */
  private maxReconnectAttempts: number = 10;

  /** Base delay for exponential backoff (ms) */
  private baseReconnectDelay: number = 1000;

  /** Maximum reconnect delay cap (ms) */
  private maxReconnectDelay: number = 30000;

  /** Reconnect timer handle */
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  /** Heartbeat interval timer handle */
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  /** Heartbeat interval (ms) */
  private heartbeatInterval: number = 15000;

  /** Last pong received timestamp */
  private lastPong: number = 0;

  // ---- Public API ----

  /**
   * Set the WebSocket endpoint URL.
   * Must be called before `connect()`.
   */
  setUrl(url: string): void {
    this.url = url;
  }

  /**
   * Get the current connection state.
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if currently connected.
   */
  isConnected(): boolean {
    return this.state === ConnectionState.Connected;
  }

  /**
   * Establish the WebSocket connection.
   */
  connect(): void {
    if (this.state === ConnectionState.Connected || this.state === ConnectionState.Connecting) {
      return;
    }

    this.state = ConnectionState.Connecting;
    console.log(`[WS] Connecting to ${this.url}...`);

    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      console.error("[WS] Failed to create WebSocket:", err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.state = ConnectionState.Connected;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data: WsEvent = JSON.parse(event.data as string);
        this.dispatch(data.type, data.payload);
      } catch (err) {
        console.error("[WS] Failed to parse message:", err);
      }
    };

    this.ws.onerror = (event: Event) => {
      console.error("[WS] Connection error:", event);
    };

    this.ws.onclose = (event: CloseEvent) => {
      console.log(`[WS] Disconnected: code=${event.code}, reason=${event.reason}`);
      this.state = ConnectionState.Disconnected;
      this.stopHeartbeat();
      this.ws = null;

      if (event.code !== 1000) {
        // Abnormal closure — attempt reconnect
        this.scheduleReconnect();
      }
    };
  }

  /**
   * Gracefully disconnect from the WebSocket.
   */
  disconnect(): void {
    this.cancelReconnect();
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
    this.state = ConnectionState.Disconnected;
  }

  /**
   * Subscribe to a specific WebSocket event type.
   *
   * @param type - Event type or "*" for all events
   * @param callback - Handler function
   * @returns Unsubscribe function
   *
   * @example
   * ```ts
   * const unsub = wsService.on("agent:status", (payload) => {
   *   console.log(`${payload.agentId} → ${payload.status}`);
   * });
   * // Later: unsub();
   * ```
   */
  on<T extends WsEventType>(
    type: T | "*",
    callback: T extends "*" ? (event: WsEvent) => void : (payload: WsPayloadMap[T]) => void
  ): () => void {
    const id = `sub-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    this.listeners.push({ type, callback: callback as EventListener<WsEventType>, id });

    return () => {
      this.listeners = this.listeners.filter((l) => l.id !== id);
    };
  }

  /**
   * Subscribe to all event types.
   *
   * @param callback - Universal handler receiving full WsEvent
   * @returns Unsubscribe function
   */
  onAny(callback: (event: WsEvent) => void): () => void {
    return this.on("*", callback);
  }

  // ---- Private Methods ----

  /**
   * Dispatch an incoming event to registered listeners.
   */
  private dispatch(type: WsEventType, payload: unknown): void {
    // Handle heartbeat pong
    if (type === "heartbeat") {
      this.lastPong = Date.now();
    }

    for (const listener of this.listeners) {
      if (listener.type === "*" || listener.type === type) {
        try {
          listener.callback(payload as never);
        } catch (err) {
          console.error(`[WS] Listener error for ${type}:`, err);
        }
      }
    }
  }

  /**
   * Schedule a reconnection attempt with exponential backoff.
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(
        `[WS] Max reconnect attempts (${this.maxReconnectAttempts}) reached. Giving up.`
      );
      this.state = ConnectionState.Disconnected;
      return;
    }

    this.state = ConnectionState.Reconnecting;
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    const jitter = delay * (0.5 + Math.random() * 0.5); // 50-100% of delay for jitter

    console.log(
      `[WS] Reconnecting in ${Math.round(jitter)}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts += 1;
      this.connect();
    }, jitter);
  }

  /**
   * Cancel any pending reconnection.
   */
  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectAttempts = 0;
  }

  /**
   * Start the heartbeat interval.
   * Sends ping frames to keep the connection alive.
   */
  private startHeartbeat(): void {
    this.lastPong = Date.now();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "heartbeat" }));
      }

      // Check for missed pongs (connection might be stale)
      if (Date.now() - this.lastPong > this.heartbeatInterval * 2) {
        console.warn("[WS] Heartbeat timeout — reconnecting");
        this.ws?.close();
      }
    }, this.heartbeatInterval);
  }

  /**
   * Stop the heartbeat interval.
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

// ---------------------------------------------------------------------------
// Singleton instance
// ---------------------------------------------------------------------------

/**
 * The singleton WebSocket service instance.
 * Import this and use it throughout the app.
 */
export const wsService = new WebSocketService();

/**
 * Initialize the WebSocket service with a backend URL and connect.
 *
 * @param backendUrl - Base HTTP URL of the backend (ws:// derived from it)
 */
export function initializeWebSocket(backendUrl?: string): void {
  if (backendUrl) {
    // Derive WS URL from HTTP URL
    const wsUrl = backendUrl.replace(/^http/, "ws") + "/ws";
    wsService.setUrl(wsUrl);
  }
  wsService.connect();
}
