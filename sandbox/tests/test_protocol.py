from langchain_core.messages import AIMessage, ToolMessage

from src.protocol import event_to_frames, final_state_from_event


class _Chunk:
    def __init__(self, content):
        self.content = content


def test_non_empty_token_stream_becomes_token_frame():
    ev = {"event": "on_chat_model_stream", "data": {"chunk": _Chunk("Hello")}}
    assert event_to_frames(ev, "m1") == [{"type": "token", "message_id": "m1", "delta": "Hello"}]


def test_empty_token_stream_yields_nothing():
    ev = {"event": "on_chat_model_stream", "data": {"chunk": _Chunk("")}}
    assert event_to_frames(ev, "m1") == []


def test_tool_start_frame():
    ev = {"event": "on_tool_start", "name": "get_weather", "data": {"input": {"location": "Paris"}}}
    frames = event_to_frames(ev, "m1")
    assert frames == [
        {
            "type": "tool_call",
            "message_id": "m1",
            "tool": "get_weather",
            "args": {"location": "Paris"},
            "status": "running",
        }
    ]


def test_tool_end_frame_previews_and_truncates_output():
    long_output = ToolMessage(content="x" * 500, tool_call_id="t1")
    ev = {"event": "on_tool_end", "name": "execute_bash", "data": {"output": long_output}}
    frames = event_to_frames(ev, "m1")
    assert frames[0]["type"] == "tool_call"
    assert frames[0]["status"] == "done"
    assert frames[0]["tool"] == "execute_bash"
    assert len(frames[0]["result_preview"]) == 280  # RESULT_PREVIEW_LIMIT


def test_unrelated_event_yields_nothing():
    assert event_to_frames({"event": "on_chain_start", "data": {}}, "m1") == []


def test_final_state_extracted_from_chain_end():
    state = {"messages": [AIMessage(content="done")]}
    ev = {"event": "on_chain_end", "name": "LangGraph", "data": {"output": state}}
    assert final_state_from_event(ev) is state


def test_final_state_none_for_non_state_output():
    ev = {"event": "on_chain_end", "name": "tools", "data": {"output": "not a state"}}
    assert final_state_from_event(ev) is None
