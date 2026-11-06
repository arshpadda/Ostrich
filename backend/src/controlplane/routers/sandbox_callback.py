"""Internal endpoint the sandbox calls with its final reply.

Durability: the reply is written to Postgres here (the system of record) before
anything is pushed live, so it survives the user being offline or the control
plane replica holding their WebSocket being gone. The sandbox retries until it gets
a 2xx; ``ChatMessage.in_reply_to`` is unique, so retries are idempotent.
"""

import json
import logging
import uuid

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError

from ..core import delivery_token
from ..core.config import settings
from ..database.models import ChatMessage, SandboxSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/sandbox", tags=["Internal"])


class SandboxReply(BaseModel):
    message_id: uuid.UUID  # the user message being answered (ChatMessage.id)
    sandbox_name: str
    stream_message_id: str  # id the browser saw on this turn's token frames
    content: str
    token: str


@router.post("/reply")
async def sandbox_reply(body: SandboxReply, request: Request) -> dict:
    mid = str(body.message_id)
    if not delivery_token.verify(settings.CALLBACK_SIGNING_SECRET, body.token, body.sandbox_name, mid):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_msg = await ChatMessage.get_or_none(id=body.message_id, is_bot=False)
    session = await SandboxSession.get_or_none(id=user_msg.sandbox_session_id) if user_msg else None
    # The token already binds sandbox_name+message_id; this also pins the message
    # to the session that sandbox actually served.
    if user_msg is None or session is None or session.sandbox_name != body.sandbox_name:
        raise HTTPException(status_code=404, detail="Unknown message")

    try:
        await ChatMessage.create(
            user_id=user_msg.user_id,
            content=body.content,
            is_bot=True,
            sandbox_session=session,
            in_reply_to=body.message_id,
        )
    except IntegrityError:
        # Already persisted by an earlier attempt whose response was lost. Don't
        # re-push: the browser may already have the frame and would show it twice.
        logger.info("Duplicate reply callback for %s ignored", mid)
        return {"status": "duplicate"}

    # Live push to whichever replica holds the user's WebSocket (it relays this
    # channel). Best-effort: the reply is already durable, history shows it on reconnect.
    frame = {
        "type": "message",
        "message_id": body.stream_message_id,
        "role": "bot",
        "content": body.content,
        "done": True,
    }
    try:
        client = redis.Redis(connection_pool=request.app.state.redis_pool)
        await client.publish(f"channel:sandbox:{body.sandbox_name}", json.dumps(frame))
    except redis.RedisError:
        logger.warning("Could not push live reply for %s; persisted only", mid, exc_info=True)
    return {"status": "ok"}
