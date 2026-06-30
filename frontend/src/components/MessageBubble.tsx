import { lazy, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";
import { ToolCallCard } from "./ToolCallCard";

// Split the syntax highlighter into its own chunk, loaded only when a code
// block actually renders.
const CodeBlock = lazy(() => import("./CodeBlock"));

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] ${isUser ? "" : "w-full"}`}>
        {message.tools.map((call, i) => (
          <ToolCallCard key={`${call.tool}-${i}`} call={call} />
        ))}
        <div
          className={`rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${
            isUser
              ? "bg-[var(--color-accent)] text-white"
              : "border border-[var(--color-border-soft)] bg-[var(--color-panel)] text-zinc-100"
          }`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap break-words">{message.content}</span>
          ) : (
            <div className="prose-chat space-y-2">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    if (match) {
                      return (
                        <Suspense fallback={<pre className="my-2 rounded bg-black/30 p-3 text-xs">{String(children)}</pre>}>
                          <CodeBlock language={match[1]} value={String(children).replace(/\n$/, "")} />
                        </Suspense>
                      );
                    }
                    return (
                      <code className="rounded bg-white/10 px-1 py-0.5 font-mono text-[0.85em]" {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.streaming && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-zinc-400 align-middle" />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
