"""The sandbox reply callback: auth, idempotency, and persist-before-push."""

import json
import uuid
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tortoise.exceptions import IntegrityError

from src.controlplane.core import delivery_token
from src.controlplane.routers import sandbox_callback as cb
from src.controlplane.server import app

SECRET = "test-secret"


def _call(*, token_ok=True, user_msg="found", session_sandbox="sb-1", create_side_effect=None):
    mid = uuid.uuid4()
    token = delivery_token.mint(SECRET if token_ok else "wrong", "sb-1", str(mid), 60)
    msg = (
        SimpleNamespace(id=mid, user_id=uuid.uuid4(), sandbox_session_id=uuid.uuid4()) if user_msg == "found" else None
    )
    session = SimpleNamespace(sandbox_name=session_sandbox)
    create = AsyncMock(side_effect=create_side_effect)
    fake_redis = MagicMock(publish=AsyncMock())
    patches = [
        patch.object(cb.settings, "CALLBACK_SIGNING_SECRET", SECRET),
        patch.object(cb.ChatMessage, "get_or_none", AsyncMock(return_value=msg)),
        patch.object(cb.SandboxSession, "get_or_none", AsyncMock(return_value=session)),
        patch.object(cb.ChatMessage, "create", create),
        patch.object(cb.redis, "Redis", MagicMock(return_value=fake_redis)),
    ]
    body = {
        "message_id": str(mid),
        "sandbox_name": "sb-1",
        "stream_message_id": "stream-1",
        "content": "the answer",
        "token": token,
    }
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with TestClient(app) as client:
            resp = client.post("/internal/sandbox/reply", json=body)
    return resp, create, fake_redis


def test_valid_reply_is_persisted_then_pushed_live():
    resp, create, redis_client = _call()
    assert resp.status_code == 200
    kwargs = create.await_args.kwargs
    assert kwargs["is_bot"] is True and kwargs["content"] == "the answer"
    channel, data = redis_client.publish.await_args.args
    assert channel == "channel:sandbox:sb-1"
    assert json.loads(data) == {
        "type": "message",
        "message_id": "stream-1",
        "role": "bot",
        "content": "the answer",
        "done": True,
    }


def test_bad_token_rejected_and_nothing_written():
    resp, create, redis_client = _call(token_ok=False)
    assert resp.status_code == 401
    create.assert_not_awaited()
    redis_client.publish.assert_not_awaited()


def test_unknown_message_or_wrong_sandbox_rejected():
    assert _call(user_msg="missing")[0].status_code == 404
    assert _call(session_sandbox="other-sb")[0].status_code == 404


def test_retried_callback_is_idempotent_and_not_pushed_twice():
    resp, create, redis_client = _call(create_side_effect=IntegrityError("dup"))
    assert resp.status_code == 200 and resp.json()["status"] == "duplicate"
    redis_client.publish.assert_not_awaited()
