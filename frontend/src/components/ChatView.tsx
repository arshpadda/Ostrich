import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { useChatSocket } from "../hooks/useChatSocket";
import { ensureUserProfile, fetchHistory } from "../api";
import type { ChatMessage } from "../types";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import { StatusBar } from "./StatusBar";

export function ChatView() {
  const { user, logout } = useAuth();
  const { status, messages, error, send, setHistory } = useChatSocket(true);

  const { data: history } = useQuery({
    queryKey: ["history", user?.uid],
    queryFn: async (): Promise<ChatMessage[]> => {
      if (user?.email) await ensureUserProfile(user.email);
      const rows = await fetchHistory();
      return rows.map((r) => ({
        id: r.id,
        role: r.is_bot ? "bot" : "user",
        content: r.content,
        tools: [],
        streaming: false,
      }));
    },
    enabled: !!user,
    staleTime: Infinity,
  });

  // Seed the socket's message buffer with persisted history once it loads.
  useEffect(() => {
    if (history) setHistory(history);
  }, [history, setHistory]);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-[var(--color-border-soft)] bg-[var(--color-panel)] px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-accent)] text-sm font-bold">
            O
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">Ostrich Sandbox</div>
            <StatusBar status={status} />
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span className="hidden sm:inline">{user?.email}</span>
          <button onClick={() => void logout()} className="rounded-md border border-[var(--color-border-soft)] px-2.5 py-1 hover:bg-white/5">
            Sign out
          </button>
        </div>
      </header>

      {error && (
        <div className="bg-red-500/10 px-4 py-2 text-center text-sm text-red-300">{error}</div>
      )}

      <main className="min-h-0 flex-1">
        <MessageList messages={messages} />
      </main>

      <Composer onSend={send} disabled={status === "error"} />
    </div>
  );
}
