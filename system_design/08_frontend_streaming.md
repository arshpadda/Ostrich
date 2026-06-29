# Frontend Experience & Real-Time Streaming Protocol

This document defines the redesigned frontend and the WebSocket event protocol that
powers a real-time, agent-aware chat experience. It supersedes the original
"opaque whole-message" model, where the sandbox published a single complete bot
reply per turn.

## Goals

1. **Streaming** — render the agent's response token-by-token instead of a spinner
   followed by a wall of text.
2. **Tool-call visibility** — surface the agent's actions (running bash, reading and
   writing files, saving the workspace) inline in the conversation.
3. **Lifecycle transparency** — make sandbox provisioning, connection state, and the
   30-minute TTL expiry first-class UI, not silent failures.
4. **Robust auth** — Google sign-in with Firebase, and a fresh ID token minted before
   every (re)connection (tokens expire hourly and the WS authenticates via a query
   parameter).

## Frontend Stack

- **React + TypeScript + Vite** — typed contracts against this protocol.
- **Tailwind CSS + shadcn/ui** — accessible, dark-mode-ready components.
- **TanStack Query** — REST data fetching (`/users`, paginated `/chat` history).
- **react-markdown + Shiki** — markdown rendering with syntax-highlighted, copyable
  code blocks.

## WebSocket Event Protocol

All frames are JSON objects with a `type` discriminator. Events that belong to a
single agent turn share a `message_id` so the client can correlate streaming tokens
and tool calls with the final message.

### Server → Client

| `type`        | Fields                                              | Meaning |
|---------------|-----------------------------------------------------|---------|
| `system`      | `event` (`sandbox_provisioning` \| `connected` \| `sandbox_expired`) | Lifecycle signal |
| `token`       | `message_id`, `delta`                               | Incremental chunk of the bot reply |
| `tool_call`   | `message_id`, `tool`, `args`, `status` (`running` \| `done`), `result_preview` | Agent tool activity |
| `message`     | `message_id`, `role` (`bot`), `content`, `done: true` | Final assembled reply (this frame is persisted) |
| `error`       | `message`                                           | Friendly error (e.g. rate-limit, model unavailable) |

### Client → Server

| `type`         | Fields    | Meaning |
|----------------|-----------|---------|
| `user_message` | `content` | A user prompt |

### Persistence rule

Only the final `message` frame (and the originating user prompt) is written to
PostgreSQL. `token` and `tool_call` frames are transport-only; persisting them would
bloat history and break replay on reconnect.

### Ordering & correlation

Redis Pub/Sub preserves per-publisher order. The client buffers `token` deltas by
`message_id`, renders `tool_call` cards inline as they arrive, and reconciles the
buffer against the final `message.content` when `done` is received.

## Data Flow (streaming turn)

```
User prompt ──► WS (user_message) ──► Control Plane
  │ persist user msg
  ▼
Redis channel:sandbox:<user_id>
  ▼
Sandbox: agent.astream_events()
  ├─ tool start/end ──► tool_call events ──► Redis ──► Control Plane ──► WS
  ├─ LLM token deltas ─► token events ─────► Redis ──► Control Plane ──► WS
  └─ final answer ────► message event ─────► Redis ──► Control Plane
                                               │ persist bot msg
                                               ▼ WS ──► client reconciles
```

## Backend Changes Required

- **`sandbox/src/agent.py` / `main.py`**: replace `agent.invoke()` with
  `agent.astream_events()`; map LangGraph events to `token` / `tool_call` / `message`
  frames and publish each to Redis.
- **`backend/src/controlplane/routers/ws.py`**: relay every event type to the
  WebSocket; persist only the final `message`; emit `sandbox_provisioning` while the
  pod is being created.

## Open Questions / Assumptions

- Assumes `ChatLiteLLM` surfaces token deltas and tool start/end through
  `astream_events` over the LiteLLM proxy path — to be verified early in Phase 1.
- Firebase web config (`apiKey`, etc.) remains client-side; these are public
  identifiers, not secrets.
