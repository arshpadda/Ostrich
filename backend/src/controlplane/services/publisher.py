"""Publish user messages to the durable Cloud Pub/Sub inbound topic.

Ordering key = sandbox name, so a sandbox sees its messages in send order and a
nack/retry on one message does not reorder it relative to the next. The client is
created lazily (first publish) so importing the app, and running tests, needs no
GCP credentials.
"""

import asyncio
import json
import logging

from fastapi import FastAPI

from ..core.config import settings

logger = logging.getLogger(__name__)


def _get_client(app: FastAPI):
    client = getattr(app.state, "pubsub_publisher", None)
    if client is None:
        from google.cloud import pubsub_v1

        client = pubsub_v1.PublisherClient(
            publisher_options=pubsub_v1.types.PublisherOptions(enable_message_ordering=True)
        )
        app.state.pubsub_publisher = client
    return client


async def publish_user_message(app: FastAPI, *, sandbox_name: str, user_id: str, message_id: str, body: dict) -> str:
    """Publish and wait for the server ack. Raises on failure (caller tells the user)."""
    client = _get_client(app)
    topic_path = client.topic_path(settings.PROJECT_ID, settings.PUBSUB_TOPIC)
    future = client.publish(
        topic_path,
        json.dumps(body).encode(),
        ordering_key=sandbox_name,
        user_id=user_id,
        sandbox_name=sandbox_name,
        message_id=message_id,
    )
    try:
        return await asyncio.wrap_future(future)
    except Exception:
        # A failed publish pauses the ordering key until explicitly resumed.
        client.resume_publish(topic_path, sandbox_name)
        raise
