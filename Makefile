# Makefile for Ostrich deployment and local management

# Load environment variables from .env file if it exists
-include .env

# Deployment Variables
PROJECT_ID ?= ostr-499118
REGION ?= us-central1
SERVICE_NAME ?= ostrich-controlplane

# Database Variables
INSTANCE_NAME ?= my-postgres-instance
DB_USER ?= postgres
DB_PASSWORD ?= postgres
DB_NAME ?= ostrich

# Construct the Cloud SQL connection string and socket name
CLOUDSQL_CONNECTION_NAME = $(PROJECT_ID):$(REGION):$(INSTANCE_NAME)
DATABASE_URL = "postgres://$(DB_USER):$(DB_PASSWORD)@/$(DB_NAME)?host=/cloudsql/$(CLOUDSQL_CONNECTION_NAME)"

# Local dev (agent-sandbox on minikube) Variables
PROFILE ?= ostrich
PUBSUB_EMULATOR_HOST ?= localhost:8085
DEV_CALLBACK_SECRET ?= dev-only-secret
SANDBOX_VERSION ?= v0.5.0

.PHONY: deploy help dev-cluster dev-redis dev-backend dev-frontend dev-pubsub dev-pubsub-init dev-kube-proxy dev-dispatcher

help:
	@echo "Available commands:"
	@echo "  make deploy        - Deploys the controlplane to GCP Cloud Run"
	@echo "  make dev-cluster   - Bring up the local minikube 'ostrich' profile + agent-sandbox + warm pool"
	@echo "  make dev-redis     - Port-forward in-cluster Redis to localhost:6380"
	@echo "  make dev-backend   - Run the control plane locally against the ostrich cluster"
	@echo "  make dev-frontend  - Run the Vite frontend"
	@echo "  make dev-pubsub    - Run the local Pub/Sub emulator (then 'make dev-pubsub-init' once)"
	@echo "  make dev-kube-proxy - kubectl proxy so the local dispatcher can reach sandbox pods"
	@echo "  make dev-dispatcher - Run the dispatcher locally (emulator + kube proxy)"

# One-shot local cluster: gVisor-capable minikube + agent-sandbox controller +
# the ostrich worker image, Redis, and the warm pool. Requires GEMINI_API_KEY.
dev-cluster:
	minikube start -p $(PROFILE) --driver=docker --container-runtime=containerd
	minikube addons enable gvisor -p $(PROFILE)
	kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/$(SANDBOX_VERSION)/manifest.yaml
	kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/$(SANDBOX_VERSION)/extensions.yaml
	docker build -f sandbox.Dockerfile -t ostrich-sandbox:latest .
	minikube image load ostrich-sandbox:latest -p $(PROFILE)
	kubectl create namespace redis-system --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f infrastructure/redis-k8s.yaml
	kubectl create namespace sandbox-chat --dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic ostrich-llm --from-literal=GEMINI_API_KEY=$(GEMINI_API_KEY) -n sandbox-chat --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f infrastructure/gcp/sandbox-warmpool.yaml
	@echo "Cluster ready. Run 'make dev-redis' (separate shell), then 'make dev-backend' and 'make dev-frontend'."

dev-redis:
	kubectl port-forward -n redis-system svc/redis 6380:6379 --context $(PROFILE)

dev-backend:
	cd backend && DATABASE_URL="sqlite://ostrich_local.db" GENERATE_SCHEMAS=true \
		PROJECT_ID=$(PROJECT_ID) REDIS_URL="redis://localhost:6380" SANDBOX_KUBE_CONTEXT=$(PROFILE) \
		PUBSUB_EMULATOR_HOST=$(PUBSUB_EMULATOR_HOST) CALLBACK_SIGNING_SECRET=$(DEV_CALLBACK_SECRET) \
		CONTROLPLANE_PUBLIC_URL=http://host.minikube.internal:8001 \
		uv run uvicorn src.controlplane.server:app --port 8001

dev-frontend:
	cd frontend && VITE_API_URL=http://localhost:8001 npm run dev -- --port 5173 --strictPort

deploy:
	@echo "Deploying $(SERVICE_NAME) to Cloud Run in $(PROJECT_ID)..."
	gcloud run deploy $(SERVICE_NAME) \
		--source ./backend \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--port 8000 \
		--add-cloudsql-instances="$(CLOUDSQL_CONNECTION_NAME)" \
		--set-env-vars="DATABASE_URL=$(DATABASE_URL)"

dev-pubsub:
	gcloud beta emulators pubsub start --project=$(PROJECT_ID) --host-port=$(PUBSUB_EMULATOR_HOST)

dev-pubsub-init:
	cd dispatcher && PUBSUB_EMULATOR_HOST=$(PUBSUB_EMULATOR_HOST) PROJECT_ID=$(PROJECT_ID) uv run python scripts/init_emulator.py

# The API-server pod proxy lets the host-run dispatcher reach a sandbox by name.
dev-kube-proxy:
	kubectl proxy --port=8002 --context $(PROFILE)

dev-dispatcher:
	cd dispatcher && PUBSUB_EMULATOR_HOST=$(PUBSUB_EMULATOR_HOST) PROJECT_ID=$(PROJECT_ID) \
		DATABASE_URL="sqlite://$(CURDIR)/backend/ostrich_local.db" CALLBACK_SIGNING_SECRET=$(DEV_CALLBACK_SECRET) \
		SANDBOX_URL_TEMPLATE="http://localhost:8002/api/v1/namespaces/sandbox-chat/pods/{sandbox_name}:8080/proxy/deliver" \
		uv run python -m src.main
