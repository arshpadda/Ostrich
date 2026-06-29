import type { ConnectionStatus } from "../types";

const LABELS: Record<ConnectionStatus, { text: string; color: string; pulse?: boolean }> = {
  idle: { text: "Idle", color: "bg-zinc-500" },
  provisioning: { text: "Spinning up sandbox…", color: "bg-amber-400", pulse: true },
  connected: { text: "Connected", color: "bg-emerald-400" },
  reconnecting: { text: "Reconnecting…", color: "bg-amber-400", pulse: true },
  error: { text: "Connection error", color: "bg-red-500" },
};

export function StatusBar({ status }: { status: ConnectionStatus }) {
  const s = LABELS[status];
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-400">
      <span className={`h-2 w-2 rounded-full ${s.color} ${s.pulse ? "animate-pulse" : ""}`} />
      {s.text}
    </div>
  );
}
