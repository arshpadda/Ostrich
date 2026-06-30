import asyncio
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from firebase_admin import auth
from opentelemetry.propagate import inject

from ..database.models import ChatMessage, SandboxSession, User
from ..services.orchestrator import claim_sandbox, release_sandbox

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def verify_ws_token(token: str = Query(...)):
    """Verify Firebase ID token from WebSocket query parameter."""
    try:
        # Performance Note (Bolt ⚡):
        # auth.verify_id_token is a synchronous blocking call.
        # Calling it directly in an async route blocks the entire FastAPI event loop,
        # freezing other requests. Offloading it to a threadpool via asyncio.to_thread fixes this.
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token)
        return decoded_token
    except Exception as e:
        logger.warning("WebSocket token verification failed: %s", e)
        return None


@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()

    # 1. Authenticate User
    decoded_token = await verify_ws_token(token)
    if not decoded_token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Authentication failed"}))
        await websocket.close(code=1008)
        return

    firebase_uid = decoded_token.get("uid")
    user_obj = await User.get_or_none(firebase_uid=firebase_uid)
    if not user_obj:
        await websocket.send_text(json.dumps({"type": "error", "message": "User profile not found"}))
        await websocket.close(code=1008)
        return

    # 2. Claim a warm sandbox from the pool (once per session). The claim
    # resolves to a sandbox whose stable name is the Redis channel key.
    # claim_sandbox is a blocking kubernetes call, so offload it to a thread.
    await websocket.send_text(json.dumps({"type": "system", "event": "sandbox_provisioning"}))
    claim_name = f"claim-{user_obj.id}"
    sandbox_name = await asyncio.to_thread(claim_sandbox, user_obj.id)
    if not sandbox_name:
        # Record the failed claim for audit/debugging, then bail.
        await SandboxSession.create(
            user_id=user_obj.id, claim_name=claim_name, status="failed", error="claim did not resolve"
        )
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Could not provision a sandbox. Please retry."})
        )
        await websocket.close(code=1011)
        return

    # Safety net: reconcile any orphaned "active" sessions for this user (e.g. an
    # unclean disconnect where the release never ran). A user has one logical
    # sandbox at a time, so prior actives are stale.
    await SandboxSession.filter(user_id=user_obj.id, status="active").update(
        status="released", released_at=datetime.now(timezone.utc)
    )

    # Durable record of which sandbox served this session (see SandboxSession).
    session = await SandboxSession.create(
        user_id=user_obj.id, claim_name=claim_name, sandbox_name=sandbox_name, status="active"
    )

    # 3. Setup Redis Channel (keyed by the claimed sandbox's stable name)
    redis_client = redis.Redis(connection_pool=websocket.app.state.redis_pool)
    pubsub = redis_client.pubsub()
    channel_name = f"channel:sandbox:{sandbox_name}"
    await pubsub.subscribe(channel_name)

    # Signal the client that the sandbox channel is ready.
    await websocket.send_text(json.dumps({"type": "system", "event": "connected"}))

    # 3. Read from Redis and forward to WebSocket.
    # Poll with get_message(timeout=...): it returns None when idle (no spurious
    # "loop crashed" churn that the listen() generator produced on read timeouts).
    async def listen_to_redis():
        logger.info("Backend listening to Redis channel: %s", channel_name)
        try:
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                except redis.RedisError as e:
                    logger.warning("Redis read error on %s: %s; retrying", channel_name, e)
                    await asyncio.sleep(1)
                    continue
                if not message or message.get("type") != "message":
                    continue
                payload_str = message["data"]
                try:
                    # Forward the frame to the frontend.
                    await websocket.send_text(payload_str)
                    # Persist only the final assembled reply. token/tool_call frames
                    # are transport-only (see system_design/08_frontend_streaming.md).
                    payload_json = json.loads(payload_str)
                    if payload_json.get("type") == "message":
                        await ChatMessage.create(
                            user_id=user_obj.id,
                            content=payload_json.get("content", ""),
                            is_bot=True,
                            sandbox_session=session,
                        )
                except Exception as e:
                    logger.error("Error forwarding/persisting frame: %s", e)
        except asyncio.CancelledError:
            logger.info("listen_to_redis task cancelled")

    redis_task = asyncio.create_task(listen_to_redis())

    # 4. Read from WebSocket and publish to Redis
    try:
        while True:
            data = await websocket.receive_text()

            try:
                parsed = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                parsed = None

            # Stop button: relay a cancel to the sandbox worker (no persistence).
            if isinstance(parsed, dict) and parsed.get("type") == "cancel":
                await redis_client.publish(channel_name, json.dumps({"type": "cancel"}))
                continue

            # Accept the structured {"type": "user_message", "content": ...} frame,
            # falling back to raw text for backward compatibility.
            if isinstance(parsed, dict) and parsed.get("type") == "user_message":
                content = parsed["content"]
            else:
                content = data

            # Save the message to DB
            msg_obj = await ChatMessage.create(
                user_id=user_obj.id, content=content, is_bot=False, sandbox_session=session
            )

            # Publish to Sandbox with OpenTelemetry trace context
            trace_ctx = {}
            inject(trace_ctx)
            payload = {"message_id": str(msg_obj.id), "role": "user", "content": content, "trace_context": trace_ctx}
            await redis_client.publish(channel_name, json.dumps(payload))

    except WebSocketDisconnect:
        pass
    finally:
        redis_task.cancel()
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
        # Mark the session released for the audit trail.
        session.status = "released"
        session.released_at = datetime.now(timezone.utc)
        await session.save()
        # Release the sandbox (deletes the claim -> tears down the pod), once per
        # session. Fixes the prior "pod lingers until TTL" leak.
        await asyncio.to_thread(release_sandbox, user_obj.id)
