# Durable Message Delivery

## Why
Redis pub/sub keeps nothing and Memorystore is in-memory.
A message published before the sandbox subscribed, during a Redis restart or failover, or a reply produced while no control plane replica was listening, was silently lost.
User messages and final bot replies must never be lost, so those two now travel over durable paths.
High-volume, disposable traffic (token and tool_call frames, cancel) stays on Redis.

## Overview
```
 Browser ──WS──► Control Plane (Cloud Run)
                   │ 1. save ChatMessage (Postgres)
                   │ 2. publish (ordering key = sandbox name)
                   ▼
              Cloud Pub/Sub  topic user-messages
                   ▼  pull subscription (ordered, DLQ after 10 attempts)
              Dispatcher (GKE, separate deployment)
                   │ 3. is there an ACTIVE SandboxSession for (user_id, sandbox_name)?
                   │ 4. mint per-delivery token, POST http://<sandbox>:8080/deliver
                   ▼  202 = ack, anything else = nack (retry, then DLQ)
              Sandbox pod: queue message, run agent turn
                   │ tokens / tool_calls ───────────► Redis ──► Control Plane ──► WS   (best effort)
                   │ 5. final reply: POST /internal/sandbox/reply (retried, token-authenticated)
                   ▼
              Control Plane: write ChatMessage (Postgres), then push the frame to Redis ──► WS
```
Cancel does not use the queue.
The control plane publishes `{"type":"cancel"}` straight to `channel:sandbox:<name>` so it can interrupt a running turn instead of waiting behind it.

## Guarantees
- **Inbound is at-least-once.**
  Pub/Sub retries until the sandbox answers 202.
  The sandbox dedupes on `message_id`, so a redelivery never runs a turn twice.
- **Per-sandbox ordering.**
  The ordering key is the sandbox name, and the sandbox starts queued messages strictly in order.
- **The reply is durable before it is visible.**
  `POST /internal/sandbox/reply` writes to Postgres first, then pushes live.
  If the user is offline the reply is already in history on reconnect.
- **Replies are idempotent.**
  `ChatMessage.in_reply_to` is unique, so a retried callback cannot store the reply twice and does not re-push it.

## Security
- The sandbox runs user-driven code, so it holds no GCP credentials and no long-lived secret.
- Only the dispatcher may reach the intake port (`sandbox-ingress-policy` in `infrastructure/gcp/sandbox-network-policy.yaml`).
- Each delivery carries `callback_token`, an HMAC over `(sandbox_name, message_id, expiry)` signed with `CALLBACK_SIGNING_SECRET` (known to the dispatcher and control plane only).
  The sandbox can answer only the message it was given, only until the token expires (default 1 hour).
  The control plane additionally checks the message belongs to that sandbox's session.
- The sandbox rejects (409) any message addressed to a different sandbox name.
- The dispatcher is the validation point: it drops messages whose user has no active session on the target sandbox, and refuses to route when the Pub/Sub attributes disagree with the body.

## Failure behaviour
| Failure | Result |
|---|---|
| Pub/Sub publish fails | User gets an error frame, message stays in Postgres. |
| Sandbox not up yet / unreachable | Dispatcher nacks, Pub/Sub retries with backoff (2s to 60s), dead-letters after 10 attempts to `user-messages-dlq`. |
| Session released while queued | Dispatcher acks and drops (the message is in Postgres, nothing to deliver it to). |
| Reply callback fails | Sandbox retries 6 times with backoff. If all fail it still sends a live frame, logs an error, and the reply is not in history. |
| Cancel arrives while a message is still queued | Known gap: the queued message will still start after the cancel. |
| Redis down | Streaming stops, but messages and final replies still flow and persist. |

## Components
| Component | Path |
|---|---|
| Publisher | `backend/src/controlplane/services/publisher.py` |
| Reply callback | `backend/src/controlplane/routers/sandbox_callback.py` |
| Token (control plane side) | `backend/src/controlplane/core/delivery_token.py` |
| Dispatcher | `dispatcher/` (`dispatcher.Dockerfile`, `infrastructure/gcp/dispatcher.yaml`) |
| Sandbox intake and reply | `sandbox/src/delivery.py`, wired in `sandbox/src/main.py` |
| Pub/Sub, IAM, DLQ | `infrastructure/gcp/main.tf` |

## Configuration
| Variable | Used by | Meaning |
|---|---|---|
| `PUBSUB_TOPIC`, `PROJECT_ID` | control plane | Inbound topic. |
| `CONTROLPLANE_PUBLIC_URL` | control plane | Base URL the sandbox posts replies to. |
| `CALLBACK_SIGNING_SECRET` | control plane, dispatcher | HMAC key. Unset means every callback is rejected. |
| `SANDBOX_URL_TEMPLATE` | dispatcher | How to reach a pod, default `http://{sandbox_name}.sandbox-chat.svc.cluster.local:8080/deliver`. |
| `INTAKE_PORT` | sandbox | Intake port, default 8080. |

## Local development
1. `make dev-pubsub` and `make dev-pubsub-init` (needs the gcloud Pub/Sub emulator component).
2. `make dev-kube-proxy` so the host-run dispatcher can reach pods through the API server.
3. `make dev-dispatcher`, `make dev-backend`, `make dev-frontend` as before.

## Open items
- The in-cluster DNS name for a claimed sandbox (`<sandbox_name>.sandbox-chat.svc.cluster.local`) has not been confirmed against agent-sandbox; adjust `SANDBOX_URL_TEMPLATE` if the controller exposes it differently.
- The control plane's Cloud Run host must be added to `infrastructure/gcp/istio-egress-policy.yaml` so sandboxes can post replies in production.
- A `/readyz` check for Pub/Sub reachability is not implemented yet.
