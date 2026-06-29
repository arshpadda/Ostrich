"""Mapping from LangGraph ``astream_events`` events to the WebSocket wire protocol.

The frames produced here are published to Redis and relayed verbatim by the
control plane to the browser. See ``system_design/08_frontend_streaming.md`` for
the protocol definition. Keeping this mapping pure (no I/O) makes it unit-testable.
"""

from typing import Any

# Tool result previews are truncated so a noisy tool (e.g. a long bash dump)
# never floods the channel; the full result still reaches the model.
RESULT_PREVIEW_LIMIT = 280


def _tool_output_preview(output: Any) -> str:
    """Best-effort short string preview of a tool's return value."""
    content = getattr(output, "content", output)
    text = content if isinstance(content, str) else str(content)
    return text[:RESULT_PREVIEW_LIMIT]


def event_to_frames(event: dict, message_id: str) -> list[dict]:
    """Translate a single astream_events event into zero or more wire frames.

    - ``on_chat_model_stream`` with non-empty content -> a ``token`` frame.
    - ``on_tool_start`` -> a ``tool_call`` frame with ``status: running``.
    - ``on_tool_end`` -> a ``tool_call`` frame with ``status: done`` + preview.
    Everything else yields no frames.
    """
    kind = event.get("event")
    data = event.get("data", {})

    if kind == "on_chat_model_stream":
        chunk = data.get("chunk")
        delta = getattr(chunk, "content", "") or ""
        if delta:
            return [{"type": "token", "message_id": message_id, "delta": delta}]
        return []

    if kind == "on_tool_start":
        return [
            {
                "type": "tool_call",
                "message_id": message_id,
                "tool": event.get("name"),
                "args": data.get("input"),
                "status": "running",
            }
        ]

    if kind == "on_tool_end":
        return [
            {
                "type": "tool_call",
                "message_id": message_id,
                "tool": event.get("name"),
                "status": "done",
                "result_preview": _tool_output_preview(data.get("output")),
            }
        ]

    return []


def final_state_from_event(event: dict) -> dict | None:
    """Return the graph's final state if this event carries it, else None.

    The outermost graph emits an ``on_chain_end`` whose output is the full
    ``{"messages": [...]}`` state. Callers keep the last such state seen in a turn,
    which is authoritative for both persistence and the next turn's context.
    """
    if event.get("event") != "on_chain_end":
        return None
    output = event.get("data", {}).get("output")
    if isinstance(output, dict) and isinstance(output.get("messages"), list):
        return output
    return None
