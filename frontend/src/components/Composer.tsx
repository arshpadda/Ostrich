import { useState, type KeyboardEvent } from "react";

export function Composer({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim()) return;
    onSend(text);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-[var(--color-border-soft)] bg-[var(--color-panel)] p-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Ask the agent to build something…"
          className="max-h-40 flex-1 resize-none rounded-xl border border-[var(--color-border-soft)] bg-[var(--color-panel-2)] px-4 py-3 text-[15px] text-zinc-100 placeholder:text-zinc-500 focus:border-[var(--color-accent)] focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="rounded-xl bg-[var(--color-accent)] px-4 py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}
