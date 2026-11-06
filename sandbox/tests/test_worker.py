import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from src import main as m
from src.main import MAX_HISTORY_MESSAGES, _trim_history


class _BlockingAgent:
    """astream_events that appends nothing and blocks until cancelled."""

    def __init__(self, gate):
        self._gate = gate

    async def astream_events(self, state, version):
        await self._gate.wait()
        yield {}  # never reached before cancellation


class _FakeRedis:
    def __init__(self):
        self.published = []

    async def publish(self, channel, data):
        self.published.append(data)


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


def test_process_turn_rolls_back_on_cancel():
    """Cancelling an in-flight turn drops the unanswered prompt from history."""

    async def scenario():
        gate = asyncio.Event()
        state = {"messages": []}
        task = asyncio.create_task(m.process_turn(_BlockingAgent(gate), _FakeRedis(), state, "hello", "mid-1"))
        await asyncio.sleep(0.05)  # let it append the HumanMessage and start streaming
        assert len(state["messages"]) == 1
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return state

    state = asyncio.run(scenario())
    assert state["messages"] == []  # rolled back, no dangling prompt


def test_process_turn_uses_on_final_instead_of_redis_for_reply():
    """With a durable callback the final reply must not also be published as a live frame."""

    class _OneShotAgent:
        async def astream_events(self, state, version):
            yield {
                "event": "on_chain_end",
                "data": {"output": {"messages": [AIMessage(content="the answer")]}},
            }

    async def scenario():
        redis_client, got = _FakeRedis(), []

        async def on_final(content):
            got.append(content)

        await m.process_turn(_OneShotAgent(), redis_client, {"messages": []}, "q", "mid-1", on_final=on_final)
        return redis_client.published, got

    published, got = asyncio.run(scenario())
    assert got == ["the answer"]
    assert published == []
