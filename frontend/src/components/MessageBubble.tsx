import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { ChatMessage } from "../types";
import { ToolCallCard } from "./ToolCallCard";

function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="group relative my-2">
      <button
        onClick={copy}
        className="absolute right-2 top-2 z-10 rounded bg-white/10 px-2 py-0.5 text-[10px] text-zinc-300 opacity-0 transition group-hover:opacity-100"
      >
        {copied ? "Copied" : "Copy"}
      </button>
      <SyntaxHighlighter language={language} style={oneDark} PreTag="div" customStyle={{ margin: 0, borderRadius: 8, fontSize: 13 }}>
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

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
                      return <CodeBlock language={match[1]} value={String(children).replace(/\n$/, "")} />;
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
