"""Mint the per-delivery reply token. Must match backend/src/controlplane/core/delivery_token.py."""

import hashlib
import hmac
import time


def mint(secret: str, sandbox_name: str, message_id: str, ttl_seconds: int, now: float | None = None) -> str:
    exp = int((time.time() if now is None else now) + ttl_seconds)
    msg = f"{sandbox_name}|{message_id}|{exp}".encode()
    return f"{exp}.{hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()}"
