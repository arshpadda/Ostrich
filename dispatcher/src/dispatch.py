"""Core decision logic: validate one queued message and hand it to its sandbox."""

import json
import logging
from typing import Callable, Literal

import requests

from .tokens import mint

logger = logging.getLogger("dispatcher")

Decision = Literal["ack", "nack"]
# Fields forwarded to the sandbox. user_id stays here: the sandbox has no use for it.
FORWARDED = ("message_id", "sandbox_name", "content", "trace_context", "callback_url")


def handle(
    data: bytes,
    attrs: dict,
    *,
    is_active: Callable[[str, str], bool],
    sandbox_url_template: str,
    secret: str,
    token_ttl: int,
    timeout: float = 10,
    post=requests.post,
) -> Decision:
    """Return "ack" when the message is done with (delivered or deliberately dropped),
    "nack" to have Pub/Sub redeliver it (and dead-letter it after repeated failures)."""
    try:
        body = json.loads(data)
        user_id, sandbox_name, message_id = body["user_id"], body["sandbox_name"], body["message_id"]
    except (ValueError, KeyError, TypeError):
        logger.error("Malformed message; leaving for the dead-letter topic")
        return "nack"

    # The attributes are set by the publisher beside the body. A mismatch means
    # something is wrong upstream; never route on it.
    if (attrs.get("user_id"), attrs.get("sandbox_name"), attrs.get("message_id")) != (
        user_id,
        sandbox_name,
        message_id,
    ):
        logger.error("Attribute/body mismatch for %s; leaving for the dead-letter topic", message_id)
        return "nack"

    try:
        active = is_active(user_id, sandbox_name)
    except Exception:
        logger.error("Session lookup failed for %s", message_id, exc_info=True)
        return "nack"
    if not active:
        # Released, failed, or not this user's sandbox. The message is already saved
        # in Postgres; there is nothing left to deliver it to.
        logger.warning("Dropping %s: no active session for user %s on %s", message_id, user_id, sandbox_name)
        return "ack"

    payload = {k: body[k] for k in FORWARDED if k in body}
    payload["callback_token"] = mint(secret, sandbox_name, message_id, token_ttl)
    try:
        resp = post(sandbox_url_template.format(sandbox_name=sandbox_name), json=payload, timeout=timeout)
    except requests.RequestException as e:
        logger.warning("Sandbox %s unreachable for %s: %s", sandbox_name, message_id, e)
        return "nack"
    if resp.status_code == 202:
        return "ack"
    logger.warning("Sandbox %s answered %s for %s", sandbox_name, resp.status_code, message_id)
    return "nack"
