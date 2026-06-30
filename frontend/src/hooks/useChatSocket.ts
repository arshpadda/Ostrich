import { useCallback, useEffect, useRef, useState } from "react";
import { auth } from "../firebase";
import { WS_URL } from "../config";
import type { ChatMessage, ConnectionStatus, ServerFrame, ToolCall } from "../types";

interface UseChatSocket {
  status: ConnectionStatus;
  messages: ChatMessage[];
  error: string | null;
  send: (content: string) => void;
  cancel: () => void;
  setHistory: (messages: ChatMessage[]) => void;
}

/**
 * Owns the live WebSocket to the control plane: mints a fresh Firebase token on
 * every (re)connect (tokens expire hourly), parses protocol frames, and assembles
 * streaming tokens + tool calls into renderable messages.
 */
export function useChatSocket(enabled: boolean): UseChatSocket {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedByUs = useRef(false);
  const attemptRef = useRef(0); // reconnect attempt count, for capped backoff
  const connectingRef = useRef(false); // a connect() is mid-flight (token fetch)

  // --- streaming assembly --------------------------------------------------
  const upsertBot = useCallback((id: string, update: (m: ChatMessage) => ChatMessage) => {
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === id && m.role === "bot");
      if (idx === -1) {
        const fresh: ChatMessage = { id, role: "bot", content: "", tools: [], streaming: true };
        return [...prev, update(fresh)];
      }
      const next = [...prev];
      next[idx] = update(next[idx]);
      return next;
    });
  }, []);

  const handleFrame = useCallback(
    (frame: ServerFrame) => {
      switch (frame.type) {
        case "system":
          if (frame.event === "sandbox_provisioning") setStatus("provisioning");
          else if (frame.event === "connected") {
            setStatus("connected");
            setError(null); // clear any transient error (e.g. first-sign-in profile race)
          }
          else if (frame.event === "sandbox_expired") setStatus("reconnecting");
          else if (frame.event === "cancelled" && frame.message_id) {
            // Stop the streaming cursor on the interrupted message.
            upsertBot(frame.message_id, (m) => ({ ...m, streaming: false }));
          }
          break;
        case "token":
          upsertBot(frame.message_id, (m) => ({ ...m, content: m.content + frame.delta, streaming: true }));
          break;
        case "tool_call":
          upsertBot(frame.message_id, (m) => {
            const tools = [...m.tools];
            if (frame.status === "running") {
              tools.push({ tool: frame.tool, args: frame.args, status: "running" });
            } else {
              const i = tools.findIndex((t) => t.tool === frame.tool && t.status === "running");
              const done: ToolCall = { tool: frame.tool, status: "done", resultPreview: frame.result_preview };
              if (i === -1) tools.push(done);
              else tools[i] = { ...tools[i], status: "done", resultPreview: frame.result_preview };
            }
            return { ...m, tools };
          });
          break;
        case "message":
          upsertBot(frame.message_id, (m) => ({ ...m, content: frame.content, streaming: false }));
          break;
        case "error":
          setError(frame.message);
          break;
      }
    },
    [upsertBot],
  );

  // --- connection lifecycle ------------------------------------------------
  const connect = useCallback(async () => {
    // Serialize connects across the async token fetch and never open a second
    // socket while one is connecting/open. Without this, React StrictMode's
    // mount→cleanup→remount (and overlapping reconnects) open duplicate sockets
    // during the await window — each claiming its own sandbox session.
    if (connectingRef.current) return;
    const existing = wsRef.current;
    if (existing && (existing.readyState === WebSocket.CONNECTING || existing.readyState === WebSocket.OPEN)) {
      return;
    }

    connectingRef.current = true;
    let token: string | undefined;
    try {
      token = await auth.currentUser?.getIdToken();
    } finally {
      connectingRef.current = false;
    }
    // Aborted (unmounted) during the token fetch, or no token / another socket won.
    if (!token || closedByUs.current) return;
    const racer = wsRef.current;
    if (racer && (racer.readyState === WebSocket.CONNECTING || racer.readyState === WebSocket.OPEN)) return;

    setStatus((s) => (s === "idle" ? "provisioning" : "reconnecting"));
    const ws = new WebSocket(`${WS_URL}/ws/chat?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;
    // Unmounted between creating the socket and now → close it immediately.
    if (closedByUs.current) {
      ws.close();
      wsRef.current = null;
      return;
    }

    ws.onopen = () => {
      attemptRef.current = 0; // reset backoff once connected
    };
    ws.onmessage = (ev) => {
      try {
        handleFrame(JSON.parse(ev.data) as ServerFrame);
      } catch {
        /* ignore malformed frame */
      }
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => {
      if (closedByUs.current) return;
      setStatus("reconnecting");
      // Capped exponential backoff with jitter: 1s, 2s, 4s … max 30s.
      const delay = Math.min(30000, 1000 * 2 ** attemptRef.current) + Math.random() * 500;
      attemptRef.current += 1;
      reconnectRef.current = setTimeout(() => void connect(), delay);
    };
  }, [handleFrame]);

  useEffect(() => {
    if (!enabled) return;
    closedByUs.current = false;
    void connect();
    return () => {
      closedByUs.current = true;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [enabled, connect]);

  const send = useCallback((content: string) => {
    const text = content.trim();
    if (!text) return;
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: text, tools: [], streaming: false },
    ]);
    wsRef.current?.send(JSON.stringify({ type: "user_message", content: text }));
  }, []);

  const cancel = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: "cancel" }));
  }, []);

  const setHistory = useCallback((msgs: ChatMessage[]) => setMessages(msgs), []);

  return { status, messages, error, send, cancel, setHistory };
}
