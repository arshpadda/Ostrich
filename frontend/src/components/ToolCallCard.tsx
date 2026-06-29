import { useState } from "react";
import type { ToolCall } from "../types";

const TOOL_ICONS: Record<string, string> = {
  execute_bash: "▶",
  read_file: "📄",
  write_file: "✏️",
  save_workspace: "💾",
  get_weather: "🌤",
};

export function ToolCallCard({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false);
  const running = call.status === "running";

  return (
    <div className="my-1.5 overflow-hidden rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-panel-2)] text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-white/5"
      >
        <span>{TOOL_ICONS[call.tool] ?? "🔧"}</span>
        <span className="font-mono text-xs text-zinc-300">{call.tool}</span>
        <span
          className={`ml-auto rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
            running ? "bg-amber-400/15 text-amber-300" : "bg-emerald-400/15 text-emerald-300"
          }`}
        >
          {running ? "running" : "done"}
        </span>
      </button>
      {open && (
        <div className="border-t border-[var(--color-border-soft)] px-3 py-2 text-xs text-zinc-400">
          {call.args != null && (
            <pre className="mb-1 whitespace-pre-wrap break-words font-mono">{JSON.stringify(call.args, null, 2)}</pre>
          )}
          {call.resultPreview && (
            <pre className="whitespace-pre-wrap break-words font-mono text-zinc-500">{call.resultPreview}</pre>
          )}
        </div>
      )}
    </div>
  );
}
