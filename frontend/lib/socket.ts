"use client";

import { useEffect, useRef, useCallback } from "react";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(path: string, onMessage: (data: unknown) => void) {
  const ws = useRef<WebSocket | null>(null);
  const reconnect = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const socket = new WebSocket(`${WS_BASE}/ws${path}`);
    ws.current = socket;

    socket.onmessage = evt => {
      try { onMessage(JSON.parse(evt.data)); } catch { /* skip */ }
    };

    socket.onclose = () => {
      reconnect.current = setTimeout(connect, 3_000);
    };

    socket.onerror = () => socket.close();

    const ping = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 25_000);

    return () => {
      clearInterval(ping);
      socket.close();
    };
  }, [path, onMessage]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup();
      if (reconnect.current) clearTimeout(reconnect.current);
    };
  }, [connect]);
}
