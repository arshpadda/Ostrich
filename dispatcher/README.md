# Ostrich dispatcher

Consumes the `user-messages` Cloud Pub/Sub subscription and delivers each message to the user's sandbox.
For every message it checks that the user owns an active sandbox session for the target sandbox, mints a short-lived reply token, and POSTs the message to the pod's `/deliver` endpoint.
It acks only when the sandbox answers 2xx, so anything undelivered is retried by Pub/Sub and eventually dead-lettered.
See `system_design/12_durable_delivery.md`.

Run locally: `uv run python -m src.main` (set `PUBSUB_EMULATOR_HOST`, `DATABASE_URL`, `CALLBACK_SIGNING_SECRET`, `SANDBOX_URL_TEMPLATE`).
