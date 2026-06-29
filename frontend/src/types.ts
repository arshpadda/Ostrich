// Wire protocol — mirrors system_design/08_frontend_streaming.md.

export type ServerFrame =
  | { type: "system"; event: "sandbox_provisioning" | "connected" | "sandbox_expired" }
  | { type: "token"; message_id: string; delta: string }
  | {
      type: "tool_call";
      message_id: string;
      tool: string;
      args?: unknown;
      status: "running" | "done";
      result_preview?: string;
    }
  | { type: "message"; message_id: string; role: "bot"; content: string; done: true }
  | { type: "error"; message: string };

export interface ToolCall {
  tool: string;
  args?: unknown;
  status: "running" | "done";
  resultPreview?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "bot";
  content: string;
  tools: ToolCall[];
  streaming: boolean;
}

export type ConnectionStatus =
  | "idle"
  | "provisioning"
  | "connected"
  | "reconnecting"
  | "error";
