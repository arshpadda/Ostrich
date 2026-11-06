"""Short-lived per-delivery token for the sandbox reply callback.

The dispatcher mints one for each message it hands to a sandbox, binding it to
(sandbox_name, message_id). The sandbox holds no long-lived secret: it can only
reply to the message it was given, and only until the token expires. The dispatcher
has an identical ``mint`` (dispatcher/src/tokens.py); the test vector in
tests/test_delivery_token.py keeps the two in sync.
"""

import hashlib
import hmac
import time


def _sign(secret: str, sandbox_name: str, message_id: str, exp: int) -> str:
    msg = f"{sandbox_name}|{message_id}|{exp}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def mint(secret: str, sandbox_name: str, message_id: str, ttl_seconds: int, now: float | None = None) -> str:
    exp = int((time.time() if now is None else now) + ttl_seconds)
    return f"{exp}.{_sign(secret, sandbox_name, message_id, exp)}"


def verify(secret: str, token: str, sandbox_name: str, message_id: str, now: float | None = None) -> bool:
    if not secret:
        return False  # fail closed when the signing secret is not configured
    try:
        exp_str, sig = token.split(".", 1)
        exp = int(exp_str)
    except ValueError:
        return False
    if (time.time() if now is None else now) > exp:
        return False
    return hmac.compare_digest(sig, _sign(secret, sandbox_name, message_id, exp))
