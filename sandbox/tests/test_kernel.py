"""Integration tests for the Jupyter kernel session backing execute_python.

These spin up a real ipykernel subprocess, so they exercise the full Jupyter
messaging path (ZMQ round-trips), not a mock. Each test gets its own fresh
session and tears it down, keeping state isolated between tests.
"""

import asyncio
import json

import pytest

from src.kernel import KernelSession


@pytest.fixture
async def session():
    s = KernelSession(execute_timeout=10.0)
    await s.start()
    try:
        yield s
    finally:
        await s.shutdown()


async def test_basic_execution(session):
    """stdout from a print is captured."""
    result = await session.execute("print('hello world')")
    assert result.status == "success"
    assert "hello world" in result.stdout
    assert result.error is None


async def test_last_expression_becomes_result(session):
    """The value of a trailing expression is returned as `result`, like a notebook cell."""
    result = await session.execute("40 + 2")
    assert result.status == "success"
    assert result.result == "42"


async def test_state_persists_across_calls(session):
    """A variable defined in one call is visible in the next - the whole point."""
    await session.execute("x = 123")
    result = await session.execute("print(x * 2)")
    assert result.status == "success"
    assert "246" in result.stdout


async def test_imports_persist_across_calls(session):
    await session.execute("import math")
    result = await session.execute("math.sqrt(16)")
    assert result.result == "4.0"


async def test_error_is_captured_not_raised(session):
    """An uncaught exception comes back as structured error, not a Python raise."""
    result = await session.execute("1 / 0")
    assert result.status == "error"
    assert result.error is not None
    assert result.error["ename"] == "ZeroDivisionError"
    assert "division by zero" in result.error["evalue"]
    # Traceback should be ANSI-stripped plain text.
    assert "\x1b[" not in result.error["traceback"]


async def test_state_survives_after_error(session):
    """An error in one cell must not wipe the namespace."""
    await session.execute("keep_me = 'survivor'")
    await session.execute("raise ValueError('boom')")
    result = await session.execute("print(keep_me)")
    assert "survivor" in result.stdout


async def test_timeout_interrupts_but_keeps_kernel_alive(session):
    """A runaway cell is interrupted; the kernel and its namespace survive."""
    await session.execute("marker = 'alive'")
    result = await session.execute("import time\nwhile True: time.sleep(0.1)")
    assert result.status == "error"
    assert result.error["ename"] == "TimeoutError"
    # Kernel should still respond and retain earlier state.
    follow_up = await session.execute("print(marker)")
    assert "alive" in follow_up.stdout


async def test_restart_resets_namespace(session):
    await session.execute("gone = 1")
    await session.restart()
    result = await session.execute("print('gone' in dir())")
    assert "False" in result.stdout


async def test_display_data_noted(session):
    """Rich (non-text) output is noted so the model knows a figure/HTML was produced."""
    code = "from IPython.display import HTML, display\ndisplay(HTML('<b>hi</b>'))"
    result = await session.execute(code)
    assert result.status == "success"
    assert any("rich output" in d for d in result.displays)


async def test_concurrent_executes_are_serialized(session):
    """Two concurrent executes must not interleave; the lock serializes them."""
    results = await asyncio.gather(
        session.execute("a = 1\nprint('first')"),
        session.execute("b = 2\nprint('second')"),
    )
    outputs = {r.stdout.strip() for r in results}
    assert outputs == {"first", "second"}


async def test_to_dict_shape():
    """The serialized payload has the exact keys the tool contract promises."""
    from src.kernel import ExecutionResult

    d = ExecutionResult().to_dict()
    assert set(d) == {"status", "stdout", "result", "displays", "error", "execution_count", "namespace_reset"}
    # Must be JSON-serializable for the tool wire format.
    json.loads(json.dumps(d))
