import asyncio
import json

import redis.asyncio as redis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from firebase_admin import auth

from ..core.config import settings
from ..database.models import ChatMessage, User
from ..services.orchestrator import provision_sandbox_pod

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Shared Redis pool across the router
redis_pool = None


@router.on_event("startup")
async def startup_event():
    global redis_pool
    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True, health_check_interval=30)


@router.on_event("shutdown")
async def shutdown_event():
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()


async def verify_ws_token(token: str = Query(...)):
    """Verify Firebase ID token from WebSocket query parameter."""
    try:
        # Performance Note (Bolt ⚡):
        # auth.verify_id_token is a synchronous blocking call.
        # Calling it directly in an async route blocks the entire FastAPI event loop,
        # freezing other requests. Offloading it to a threadpool via asyncio.to_thread fixes this.
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token)
        return decoded_token
    except Exception:
        import traceback

        traceback.print_exc()
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

    # 2. Provision Sandbox Pod
    # Performance Note (Bolt ⚡):
    # provision_sandbox_pod is a synchronous blocking call (uses subprocess.Popen or kubernetes client).
    # Calling it directly in this async route blocks the entire FastAPI event loop, freezing other requests.
    # Offloading it to a threadpool via asyncio.to_thread fixes this bottleneck.
    await asyncio.to_thread(provision_sandbox_pod, user_obj.id)

    # 2. Setup Redis Channel
    redis_client = redis.Redis(connection_pool=redis_pool)
    pubsub = redis_client.pubsub()
    channel_name = f"channel:sandbox:{user_obj.id}"
    await pubsub.subscribe(channel_name)

    # Send a confirmation to the client
    await websocket.send_text(json.dumps({"type": "system", "message": "Connected to Control Plane Sandbox Channel"}))

    # 3. Read from Redis and forward to WebSocket
    async def listen_to_redis():
        try:
            print(f"Backend listening to Redis channel: {channel_name}")
            # Performance Note (Bolt ⚡):
            # Using async for pubsub.listen() instead of a while loop with get_message() and asyncio.sleep().
            # This completely avoids unnecessary polling and CPU wakeups, drastically reducing overhead
            # and minimizing latency for incoming pubsub messages.
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    try:
                        # Forward sandbox messages back to the frontend
                        payload_str = message["data"]
                        await websocket.send_text(payload_str)
                        print("Backend successfully forwarded message to WebSocket")

                        # Persist sandbox reply to PostgreSQL
                        try:
                            payload_json = json.loads(payload_str)
                            if payload_json.get("role") == "bot":
                                await ChatMessage.create(
                                    user_id=user_obj.id, content=payload_json.get("content", ""), is_bot=True
                                )
                        except Exception as e:
                            print(f"Error saving bot message to DB: {e}")
                    except Exception as e:
                        print(f"Error sending to WebSocket: {e}")
        except asyncio.CancelledError:
            print("listen_to_redis task cancelled")

    redis_task = asyncio.create_task(listen_to_redis())

    # 4. Read from WebSocket and publish to Redis
    try:
        while True:
            data = await websocket.receive_text()

            # Ensure the sandbox is actually running before sending the message!
            # If it was killed by TTL or manual deletion, this spins it back up.
            # Performance Note (Bolt ⚡):
            # provision_sandbox_pod is a synchronous blocking call. Calling it directly here
            # inside the while loop blocks the main event loop. We use asyncio.to_thread
            # to offload it and prevent freezing concurrent WebSocket and API requests.
            await asyncio.to_thread(provision_sandbox_pod, user_obj.id)

            # Save the message to DB
            msg_obj = await ChatMessage.create(user_id=user_obj.id, content=data, is_bot=False)

            # Publish to Sandbox
            payload = {"message_id": str(msg_obj.id), "role": "user", "content": data}
            await redis_client.publish(channel_name, json.dumps(payload))

    except WebSocketDisconnect:
        pass
    finally:
        redis_task.cancel()
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
