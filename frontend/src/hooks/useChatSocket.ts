import { useCallback, useEffect, useRef, useState } from "react";
import { auth } from "../firebase";
import { WS_URL } from "../config";
import type { ChatMessage, ConnectionStatus, ServerFrame, ToolCall } from "../types";

interface UseChatSocket {
  status: ConnectionStatus;
  messages: ChatMessage[];
  error: string | null;
  send: (content: string) => void;
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
    const token = await auth.currentUser?.getIdToken();
    if (!token) return;

    setStatus((s) => (s === "idle" ? "provisioning" : "reconnecting"));
    const ws = new WebSocket(`${WS_URL}/ws/chat?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

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
      reconnectRef.current = setTimeout(() => void connect(), 1500);
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

  const setHistory = useCallback((msgs: ChatMessage[]) => setMessages(msgs), []);

  return { status, messages, error, send, setHistory };
}
