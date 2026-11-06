import json
from types import SimpleNamespace

import requests

from src.dispatch import handle

BODY = {
    "message_id": "m-1",
    "user_id": "u-1",
    "sandbox_name": "sb-1",
    "content": "hi",
    "trace_context": {},
    "callback_url": "http://cp/internal/sandbox/reply",
}
ATTRS = {"message_id": "m-1", "user_id": "u-1", "sandbox_name": "sb-1"}


def _run(*, body=BODY, attrs=ATTRS, active=True, resp=202, post_exc=None, lookup_exc=None):
    sent = []

    def is_active(user_id, sandbox_name):
        if lookup_exc:
            raise lookup_exc
        sent.append(("lookup", user_id, sandbox_name))
        return active

    def post(url, json, timeout):  # noqa: A002
        if post_exc:
            raise post_exc
        sent.append(("post", url, json))
        return SimpleNamespace(status_code=resp)

    data = body if isinstance(body, bytes) else json_dumps(body)
    decision = handle(
        data,
        attrs,
        is_active=is_active,
        sandbox_url_template="http://{sandbox_name}.ns:8080/deliver",
        secret="s3cret",
        token_ttl=60,
        post=post,
    )
    return decision, sent


def json_dumps(o):
    return json.dumps(o).encode()


def test_delivers_to_the_users_sandbox_and_acks():
    decision, sent = _run()
    assert decision == "ack"
    _, url, payload = sent[-1]
    assert url == "http://sb-1.ns:8080/deliver"
    assert payload["callback_token"] and "user_id" not in payload
    assert payload["content"] == "hi"


def test_inactive_session_is_dropped_without_delivery():
    decision, sent = _run(active=False)
    assert decision == "ack"
    assert not any(s[0] == "post" for s in sent)


def test_mismatched_attributes_never_route():
    decision, sent = _run(attrs={**ATTRS, "sandbox_name": "someone-elses"})
    assert decision == "nack" and sent == []


def test_malformed_body_is_nacked_for_dlq():
    assert _run(body=b"not json")[0] == "nack"
    assert _run(body={"message_id": "m-1"})[0] == "nack"


def test_sandbox_unreachable_or_refusing_is_nacked_for_retry():
    assert _run(post_exc=requests.ConnectionError("down"))[0] == "nack"
    assert _run(resp=503)[0] == "nack"
    assert _run(resp=409)[0] == "nack"


def test_db_failure_is_nacked():
    assert _run(lookup_exc=RuntimeError("db down"))[0] == "nack"
