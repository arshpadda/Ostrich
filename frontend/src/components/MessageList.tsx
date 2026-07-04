import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  // Performance Note (Bolt ⚡):
  // Throttle scroll events during high-frequency token streaming to prevent
  // browser layout thrashing and CPU spikes. When actively streaming, we use
  // 'auto' scrolling to avoid overlapping animation queues.
  const lastScrollTime = useRef(0);

  useEffect(() => {
    const isStreaming = messages.some((m) => m.role === "bot" && m.streaming);
    const now = Date.now();

    if (isStreaming && now - lastScrollTime.current < 100) {
      return;
    }

    lastScrollTime.current = now;
    endRef.current?.scrollIntoView({ behavior: isStreaming ? "auto" : "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-500">
        Start by asking the agent to write or run some code.
      </div>
    );
  }

  return (
    <div className="scroll-thin h-full overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
