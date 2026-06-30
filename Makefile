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
SANDBOX_VERSION ?= v0.5.0

.PHONY: deploy help dev-cluster dev-redis dev-backend dev-frontend

help:
	@echo "Available commands:"
	@echo "  make deploy        - Deploys the controlplane to GCP Cloud Run"
	@echo "  make dev-cluster   - Bring up the local minikube 'ostrich' profile + agent-sandbox + warm pool"
	@echo "  make dev-redis     - Port-forward in-cluster Redis to localhost:6380"
	@echo "  make dev-backend   - Run the control plane locally against the ostrich cluster"
	@echo "  make dev-frontend  - Run the Vite frontend"

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
