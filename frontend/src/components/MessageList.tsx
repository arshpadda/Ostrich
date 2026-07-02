import { useEffect, useRef, memo } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

// Performance Note (Bolt ⚡):
// Wrapping MessageList in React.memo() prevents it from re-rendering and
// performing unnecessary layout/diff checks when sibling state in ChatView
// (like status, error, or streaming flags) changes while messages remain the same.
export const MessageList = memo(function MessageList({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
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
});
