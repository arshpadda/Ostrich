from langchain_core.messages import AIMessage, HumanMessage

from src.main import MAX_HISTORY_MESSAGES, _trim_history


def test_trim_history_under_limit_is_unchanged():
    msgs = [HumanMessage(content="hi"), AIMessage(content="yo")]
    assert _trim_history(msgs) is msgs


def test_trim_history_caps_and_starts_at_human_boundary():
    msgs = []
    for i in range(MAX_HISTORY_MESSAGES + 10):
        msgs.append(HumanMessage(content=f"u{i}"))
        msgs.append(AIMessage(content=f"a{i}"))

    trimmed = _trim_history(msgs)
    assert len(trimmed) <= MAX_HISTORY_MESSAGES
    assert isinstance(trimmed[0], HumanMessage)  # never starts mid-sequence
