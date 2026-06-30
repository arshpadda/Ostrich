# Agent Sandbox Integration

Ostrich provisions per-user sandboxes through the **kubernetes-sigs
[agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox)** controller
instead of hand-building Pods. This gives us controller-managed lifecycle, stable
identity, persistent storage, gVisor isolation, warm pools (fast cold-start), and
hibernate — while keeping our existing Redis-streaming agent worker unchanged.

## Why a hybrid (CRDs for lifecycle, Redis for the data plane)
agent-sandbox's Python SDK is built around an **exec** model (`commands.run()`),
which is buffered (no token streaming) and capped at ~60s. That conflicts with our
live token/tool-call streaming. So we adopt agent-sandbox for **provisioning and
lifecycle** via its CRDs, and keep **Redis pub/sub** as the streaming data plane.
We create the CRs with the standard `kubernetes` client (no SDK dependency); the
SDK's connection configs are exec/port-forward oriented and unused here.

## Components
- **`SandboxWarmPool` + `SandboxTemplate`** (`infrastructure/gcp/sandbox-warmpool.yaml`):
  a pool of pre-initialized sandboxes running the `ostrich-sandbox` worker under
  `runtimeClassName: gvisor`, with a PVC mounted at `/workspace`.
- **Control plane** (`services/orchestrator.py`): `claim_sandbox(user)` creates a
  `SandboxClaim` (idempotent, named `claim-<user_id>`) and returns the assigned
  sandbox's name; `release_sandbox(user)` deletes the claim (tears the pod down).
- **Worker** (`sandbox/src/main.py`): keys its Redis channel off its own hostname
  (`channel:sandbox:<hostname>`). Warm pods are generic until claimed, so identity
  comes from the stable sandbox/pod name, not an injected `USER_ID`.

## Request flow
```
WS connect ─► control plane: claim_sandbox(user)
                 └─ SandboxClaim ─► controller binds a warm Sandbox
                      └─ status.sandbox.name = "ostrich-warmpool-xxxxx"
            ─► bridge WS ⇄ Redis channel:sandbox:<that name>
user msg ─► publish to channel ─► worker streams token/tool_call/message frames
WS disconnect ─► release_sandbox(user) ─► claim deleted ─► pod torn down
                 (warm pool auto-replenishes)
```

## Local development (minikube `ostrich` profile)
gVisor requires the **containerd** runtime, so local dev uses a dedicated profile:

```bash
# One-time cluster bring-up
minikube start -p ostrich --driver=docker --container-runtime=containerd
minikube addons enable gvisor -p ostrich
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/v0.5.0/manifest.yaml
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/v0.5.0/extensions.yaml

# Build + load the worker image, deploy Redis + the warm pool
docker build -f sandbox.Dockerfile -t ostrich-sandbox:latest .
minikube image load ostrich-sandbox:latest -p ostrich
kubectl create namespace redis-system; kubectl apply -f infrastructure/redis-k8s.yaml
kubectl create namespace sandbox-chat
kubectl create secret generic ostrich-llm --from-literal=GEMINI_API_KEY=$GEMINI_API_KEY -n sandbox-chat
kubectl apply -f infrastructure/gcp/sandbox-warmpool.yaml

# Run the app (see `make dev-backend` / `make dev-frontend`)
kubectl port-forward -n redis-system svc/redis 6380:6379   # control plane -> in-cluster Redis
```

The control plane runs **locally** against the cluster via kubeconfig
(`SANDBOX_KUBE_CONTEXT=ostrich`) and reaches the in-cluster Redis through the
port-forward; the worker reaches the same Redis via cluster DNS.

## Production notes (not yet done)
- **RBAC**: an in-cluster control plane needs a Role/RoleBinding to create/delete
  `sandboxclaims` in `sandbox-chat`.
- **Egress lockdown**: the `SandboxTemplate` currently sets
  `networkPolicyManagement: Unmanaged`; the zero-trust egress allowlist is a
  separate hardening task.
- **State on hibernate**: conversation history is in-memory in the worker; surviving
  hibernate/restart would require persisting LangGraph state to the PVC/DB.
