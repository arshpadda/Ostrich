"""Durable-delivery edges of the sandbox (see system_design/12_durable_delivery.md).

Inbound: the dispatcher POSTs each user message to ``/deliver``. We answer 202 only
once the message is queued for the agent, which is what lets the dispatcher ack it
in Pub/Sub. Redelivery is expected (at-least-once), so message ids are deduped.

Outbound: the final reply is POSTed to the control plane with retries, using the
per-delivery token the dispatcher minted. The sandbox holds no long-lived secret.
"""

import asyncio
import logging
from collections import OrderedDict
from typing import Awaitable, Callable

import aiohttp
from aiohttp import web

logger = logging.getLogger("sandbox-agent")

SEEN_LIMIT = 1000  # remembered message ids; far more than a session will ever send
REQUIRED_FIELDS = ("message_id", "content", "callback_url", "callback_token")


def make_intake_app(sandbox_id: str, queue: asyncio.Queue) -> web.Application:
    seen: OrderedDict[str, None] = OrderedDict()

    async def deliver(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)
        if not isinstance(data, dict) or any(not isinstance(data.get(f), str) or not data[f] for f in REQUIRED_FIELDS):
            return web.json_response({"error": "missing fields"}, status=400)
        # A message addressed to another sandbox must never be run here.
        if data.get("sandbox_name") != sandbox_id:
            return web.json_response({"error": "wrong sandbox"}, status=409)
        mid = data["message_id"]
        if mid in seen:
            return web.json_response({"status": "duplicate"}, status=202)
        seen[mid] = None
        if len(seen) > SEEN_LIMIT:
            seen.popitem(last=False)
        queue.put_nowait(data)
        return web.json_response({"status": "accepted"}, status=202)

    async def healthz(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    app.add_routes([web.post("/deliver", deliver), web.get("/healthz", healthz)])
    return app


async def post_reply(
    url: str,
    payload: dict,
    *,
    attempts: int = 6,
    base_delay: float = 1.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool:
    """POST the reply, retrying transient failures with capped exponential backoff.

    Returns True once the control plane answers 2xx. A 4xx (except 429) is a
    permanent rejection, so retrying would be pointless.
    """
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(attempts):
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status < 300:
                        return True
                    if 400 <= resp.status < 500 and resp.status != 429:
                        logger.error("Reply callback rejected with %s; not retrying", resp.status)
                        return False
                    logger.warning("Reply callback got %s (attempt %d)", resp.status, attempt + 1)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Reply callback failed (attempt %d): %s", attempt + 1, e)
            if attempt < attempts - 1:
                await sleep(min(base_delay * 2**attempt, 30))
    return False
