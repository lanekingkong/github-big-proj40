/**
 * useWebSocket - WebSocket 连接管理 Hook
 * 自动重连、心跳保活、消息分发
 */
import { useEffect, useRef, useState, useCallback } from 'react';

interface WSOptions {
  url: string;
  protocols?: string | string[];
  reconnectInterval?: number;
  maxReconnects?: number;
  pingInterval?: number;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (err: Event) => void;
}

interface UseWebSocketReturn {
  connected: boolean;
  send: (data: any) => void;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: WSOptions): UseWebSocketReturn {
  const { url, protocols, reconnectInterval = 3000, maxReconnects = 10, pingInterval = 15000, onMessage, onOpen, onClose, onError } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const pingTimerRef = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    try {
      const ws = new WebSocket(url, protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        reconnectCount.current = 0;
        onOpen?.();
        // 心跳
        if (pingInterval > 0) {
          pingTimerRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
          }, pingInterval);
        }
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try { onMessage?.(JSON.parse(event.data)); }
        catch { onMessage?.(event.data); }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        setConnected(false);
        clearInterval(pingTimerRef.current);
        onClose?.();
        if (reconnectCount.current < maxReconnects) {
          reconnectCount.current++;
          setTimeout(connect, reconnectInterval * reconnectCount.current);
        }
      };

      ws.onerror = (err) => {
        onError?.(err);
        ws.close();
      };
    } catch {
      if (reconnectCount.current < maxReconnects) {
        reconnectCount.current++;
        setTimeout(connect, reconnectInterval);
      }
    }
  }, [url, protocols, reconnectInterval, maxReconnects, pingInterval, onMessage, onOpen, onClose, onError]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearInterval(pingTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    reconnectCount.current = 0;
    connect();
  }, [connect]);

  const disconnect = useCallback(() => {
    reconnectCount.current = maxReconnects + 1;
    wsRef.current?.close();
  }, [maxReconnects]);

  return { connected, send, reconnect, disconnect };
}
