"""Integration tests for the /ws/chat WebSocket relay.

The endpoint wires together auth, sandbox claiming, the Redis pub/sub bridge, and
persistence. We mock the external edges (Firebase, the orchestrator, Redis, and the
ORM) so the test exercises the relay logic deterministically without a cluster or
real Redis.
"""

import asyncio
import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.controlplane.routers import ws as ws_module
from src.controlplane.server import app


class FakePubSub:
    def __init__(self, frames):
        self._frames = list(frames)

    async def subscribe(self, channel):
        self.channel = channel

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        if self._frames:
            return {"type": "message", "data": self._frames.pop(0)}
        await asyncio.sleep(0.02)
        return None

    async def unsubscribe(self, channel):
        pass

    async def close(self):
        pass


class FakeRedis:
    def __init__(self, frames=()):
        self._pubsub = FakePubSub(frames)
        self.published = []

    def pubsub(self):
        return self._pubsub

    async def publish(self, channel, data):
        self.published.append((channel, data))


def _patches(fake_redis, *, user=SimpleNamespace(id=uuid.uuid4()), token_uid="u1"):
    return [
        patch.object(ws_module.auth, "verify_id_token", MagicMock(return_value={"uid": token_uid})),
        patch.object(ws_module.User, "get_or_none", AsyncMock(return_value=user)),
        patch.object(ws_module.ChatMessage, "create", AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))),
        patch.object(ws_module, "claim_sandbox", MagicMock(return_value="test-sb")),
        patch.object(ws_module, "release_sandbox", MagicMock()),
        patch.object(ws_module.redis, "Redis", MagicMock(return_value=fake_redis)),
    ]


def test_ws_auth_failure_closes():
    fake_redis = FakeRedis()
    ps = _patches(fake_redis)
    # Override verify to reject the token.
    ps[0] = patch.object(ws_module.auth, "verify_id_token", MagicMock(side_effect=Exception("bad token")))
    with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], TestClient(app) as client:
        with client.websocket_connect("/ws/chat?token=bad") as wsconn:
            frame = json.loads(wsconn.receive_text())
            assert frame["type"] == "error"


def test_ws_connect_claims_and_releases():
    fake_redis = FakeRedis()
    claim = MagicMock(return_value="test-sb")
    release = MagicMock()
    ps = _patches(fake_redis)
    ps[3] = patch.object(ws_module, "claim_sandbox", claim)
    ps[4] = patch.object(ws_module, "release_sandbox", release)
    with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], TestClient(app) as client:
        with client.websocket_connect("/ws/chat?token=ok") as wsconn:
            assert json.loads(wsconn.receive_text())["event"] == "sandbox_provisioning"
            assert json.loads(wsconn.receive_text())["event"] == "connected"
    assert claim.called
    assert release.called


def test_ws_forwards_and_persists_bot_message():
    bot_frame = json.dumps({"type": "message", "message_id": "m1", "role": "bot", "content": "hi there", "done": True})
    fake_redis = FakeRedis(frames=[bot_frame])
    create = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    ps = _patches(fake_redis)
    ps[2] = patch.object(ws_module.ChatMessage, "create", create)
    with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5], TestClient(app) as client:
        with client.websocket_connect("/ws/chat?token=ok") as wsconn:
            json.loads(wsconn.receive_text())  # provisioning
            json.loads(wsconn.receive_text())  # connected
            forwarded = json.loads(wsconn.receive_text())  # the bot frame
            assert forwarded["type"] == "message"
            assert forwarded["content"] == "hi there"
    # The final message frame was persisted as a bot message.
    assert create.await_count >= 1
    assert create.await_args.kwargs.get("is_bot") is True
