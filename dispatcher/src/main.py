import logging
import os
import sys
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer

from google.cloud import pubsub_v1
from psycopg_pool import ConnectionPool

from .dispatch import handle

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("dispatcher")


def _serve_health(port: int, alive: threading.Event) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - name is fixed by BaseHTTPRequestHandler
            self.send_response(200 if alive.is_set() else 503)
            self.end_headers()

        def log_message(self, *args):
            pass

    threading.Thread(target=HTTPServer(("0.0.0.0", port), Handler).serve_forever, daemon=True).start()


def _session_checker(database_url: str):
    """Return is_active(user_id, sandbox_name) backed by Postgres (prod) or SQLite (local dev)."""
    if database_url.startswith("sqlite://"):
        import sqlite3

        path = database_url.removeprefix("sqlite://")

        def is_active(user_id: str, sandbox_name: str) -> bool:
            with closing(sqlite3.connect(path)) as conn:
                row = conn.execute(
                    "SELECT 1 FROM sandbox_sessions WHERE user_id = ? AND sandbox_name = ? AND status = 'active'",
                    (user_id, sandbox_name),
                ).fetchone()
            return row is not None

        return is_active

    pool = ConnectionPool(database_url, min_size=1, max_size=4, open=True)

    def is_active(user_id: str, sandbox_name: str) -> bool:
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sandbox_sessions WHERE user_id = %s AND sandbox_name = %s AND status = 'active'",
                (user_id, sandbox_name),
            ).fetchone()
        return row is not None

    return is_active


def main() -> None:
    project = os.environ["PROJECT_ID"]
    subscription = os.environ.get("PUBSUB_SUBSCRIPTION", "user-messages-dispatcher")
    secret = os.environ["CALLBACK_SIGNING_SECRET"]
    # {sandbox_name} resolves the pod; the namespace/port match sandbox-warmpool.yaml.
    url_template = os.environ.get(
        "SANDBOX_URL_TEMPLATE", "http://{sandbox_name}.sandbox-chat.svc.cluster.local:8080/deliver"
    )
    # Must outlive the longest agent turn plus reply retries.
    token_ttl = int(os.environ.get("TOKEN_TTL_SECONDS", "3600"))

    is_active = _session_checker(os.environ["DATABASE_URL"])

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        decision = handle(
            message.data,
            dict(message.attributes),
            is_active=is_active,
            sandbox_url_template=url_template,
            secret=secret,
            token_ttl=token_ttl,
        )
        message.ack() if decision == "ack" else message.nack()

    alive = threading.Event()
    _serve_health(int(os.environ.get("HEALTH_PORT", "8081")), alive)

    subscriber = pubsub_v1.SubscriberClient()
    path = subscriber.subscription_path(project, subscription)
    # Bound concurrency; ordering keys still serialise messages per sandbox.
    future = subscriber.subscribe(path, callback=callback, flow_control=pubsub_v1.types.FlowControl(max_messages=20))
    alive.set()
    logger.info("Dispatcher consuming %s", path)
    with subscriber:
        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
            future.result()


if __name__ == "__main__":
    main()
