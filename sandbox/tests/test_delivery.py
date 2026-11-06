"""HTTP intake (dispatcher -> sandbox) and the retrying reply callback (sandbox -> control plane)."""

import asyncio

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from src.delivery import make_intake_app, post_reply

GOOD = {
    "message_id": "m-1",
    "sandbox_name": "sb-1",
    "content": "hello",
    "callback_url": "http://cp/internal/sandbox/reply",
    "callback_token": "tok",
}


def _intake(body, *, queue=None, sandbox_id="sb-1", repeat=1):
    queue = queue if queue is not None else asyncio.Queue()

    async def run():
        async with TestClient(TestServer(make_intake_app(sandbox_id, queue))) as client:
            results = []
            for _ in range(repeat):
                resp = await client.post("/deliver", json=body)
                results.append((resp.status, await resp.json()))
            return results

    return asyncio.run(run()), queue


def test_accepts_and_queues():
    [(status, body)], queue = _intake(GOOD)
    assert status == 202 and body["status"] == "accepted"
    assert queue.get_nowait()["message_id"] == "m-1"


def test_redelivery_is_deduped():
    results, queue = _intake(GOOD, repeat=2)
    assert [r[0] for r in results] == [202, 202]
    assert results[1][1]["status"] == "duplicate"
    assert queue.qsize() == 1  # the turn is not run twice


def test_wrong_sandbox_rejected():
    [(status, _)], queue = _intake(GOOD, sandbox_id="other")
    assert status == 409 and queue.empty()


def test_missing_fields_rejected():
    [(status, _)], queue = _intake({**GOOD, "callback_token": ""})
    assert status == 400 and queue.empty()


def _reply_server(statuses):
    """Control-plane stub answering with each status in turn; returns (run, calls)."""
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.Response(status=statuses[min(len(calls) - 1, len(statuses) - 1)])

    async def run(**kwargs):
        app = web.Application()
        app.add_routes([web.post("/reply", handler)])
        async with TestServer(app) as server:

            async def no_sleep(_):
                pass

            return await post_reply(str(server.make_url("/reply")), {"k": "v"}, sleep=no_sleep, **kwargs)

    return run, calls


def test_reply_retries_transient_then_succeeds():
    run, calls = _reply_server([503, 502, 200])
    assert asyncio.run(run()) is True
    assert len(calls) == 3


def test_reply_gives_up_on_permanent_rejection():
    run, calls = _reply_server([401])
    assert asyncio.run(run()) is False
    assert len(calls) == 1  # no pointless retries


def test_reply_gives_up_after_attempts():
    run, calls = _reply_server([500])
    assert asyncio.run(run(attempts=3)) is False
    assert len(calls) == 3
