"""Integration tests for the /ws/chat WebSocket relay.

The endpoint wires together auth, sandbox claiming, the Redis pub/sub bridge, the
SandboxSession audit record, and persistence. We mock the external edges
(Firebase, the orchestrator, Redis, the ORM) so the test exercises the relay
logic deterministically without a cluster or real Redis.
"""

import asyncio
import json
import uuid
from contextlib import ExitStack
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


def _base_patches(fake_redis, *, verify=None, chat_create=None, claim=None, release=None, session=None):
    """Patches for the external edges; override specific ones per test."""
    user = SimpleNamespace(id=uuid.uuid4())
    fake_session = session or MagicMock(save=AsyncMock())
    return [
        patch.object(ws_module.auth, "verify_id_token", verify or MagicMock(return_value={"uid": "u1"})),
        patch.object(ws_module.User, "get_or_none", AsyncMock(return_value=user)),
        patch.object(
            ws_module.ChatMessage,
            "create",
            chat_create or AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch.object(ws_module.SandboxSession, "create", AsyncMock(return_value=fake_session)),
        patch.object(ws_module, "claim_sandbox", claim or MagicMock(return_value="test-sb")),
        patch.object(ws_module, "release_sandbox", release or MagicMock()),
        patch.object(ws_module.redis, "Redis", MagicMock(return_value=fake_redis)),
    ]


def test_ws_auth_failure_closes():
    fake_redis = FakeRedis()
    patches = _base_patches(fake_redis, verify=MagicMock(side_effect=Exception("bad token")))
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with TestClient(app) as client, client.websocket_connect("/ws/chat?token=bad") as wsconn:
            assert json.loads(wsconn.receive_text())["type"] == "error"


def test_ws_connect_claims_and_releases():
    fake_redis = FakeRedis()
    claim = MagicMock(return_value="test-sb")
    release = MagicMock()
    patches = _base_patches(fake_redis, claim=claim, release=release)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with TestClient(app) as client, client.websocket_connect("/ws/chat?token=ok") as wsconn:
            assert json.loads(wsconn.receive_text())["event"] == "sandbox_provisioning"
            assert json.loads(wsconn.receive_text())["event"] == "connected"
    assert claim.called
    assert release.called


def test_ws_forwards_and_persists_bot_message():
    bot_frame = json.dumps({"type": "message", "message_id": "m1", "role": "bot", "content": "hi there", "done": True})
    fake_redis = FakeRedis(frames=[bot_frame])
    create = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    patches = _base_patches(fake_redis, chat_create=create)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with TestClient(app) as client, client.websocket_connect("/ws/chat?token=ok") as wsconn:
            json.loads(wsconn.receive_text())  # provisioning
            json.loads(wsconn.receive_text())  # connected
            forwarded = json.loads(wsconn.receive_text())  # the bot frame
            assert forwarded["type"] == "message"
            assert forwarded["content"] == "hi there"
    assert create.await_count >= 1
    assert create.await_args.kwargs.get("is_bot") is True


def test_ws_records_and_releases_sandbox_session():
    fake_redis = FakeRedis()
    fake_session = MagicMock(save=AsyncMock())
    session_create = AsyncMock(return_value=fake_session)
    user = SimpleNamespace(id=uuid.uuid4())
    patches = [
        patch.object(ws_module.auth, "verify_id_token", MagicMock(return_value={"uid": "u1"})),
        patch.object(ws_module.User, "get_or_none", AsyncMock(return_value=user)),
        patch.object(ws_module.ChatMessage, "create", AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))),
        patch.object(ws_module.SandboxSession, "create", session_create),
        patch.object(ws_module, "claim_sandbox", MagicMock(return_value="sb-42")),
        patch.object(ws_module, "release_sandbox", MagicMock()),
        patch.object(ws_module.redis, "Redis", MagicMock(return_value=fake_redis)),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with TestClient(app) as client, client.websocket_connect("/ws/chat?token=ok") as wsconn:
            json.loads(wsconn.receive_text())  # provisioning
            json.loads(wsconn.receive_text())  # connected

    # Recorded active with the resolved sandbox name, then released on disconnect.
    assert session_create.await_args.kwargs["status"] == "active"
    assert session_create.await_args.kwargs["sandbox_name"] == "sb-42"
    assert fake_session.status == "released"
    fake_session.save.assert_awaited()
