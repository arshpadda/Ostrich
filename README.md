# Ostrich Monorepo
![alt text](image.png)
Welcome to the **Ostrich** monorepo. Ostrich is a modern, enterprise-grade, cloud-native GenAI platform. It is designed around a Zero-Trust Kubernetes architecture, separating the Control Plane (FastAPI) from isolated, dynamic AI Sandboxes (LangGraph).

## 🏗 Architecture Overview

Ostrich uses a microservice architecture deployed on Kubernetes:

1. **Backend (Control Plane)**: A robust `FastAPI` service that handles user authentication, PostgreSQL database operations (via `TortoiseORM`), and orchestrates the dynamic provisioning of sandbox environments for users.
2. **Frontend**: A lightning-fast, modern React application powered by `Vite`.
3. **Sandbox (Data Plane)**: Dynamic, ephemeral worker pods powered by `LangGraph` and `LiteLLM`. Each user gets their own isolated Sandbox pod to execute AI tasks.
4. **AI Gateway (Zero-Trust)**: A centralized `LiteLLM Proxy` running in the `ai-gateway` namespace. Sandboxes are physically blocked from the internet via strict `NetworkPolicies`. They route all LLM requests through this central gateway, ensuring API keys are never exposed to the sandbox environments.
5. **Observability**: A native Kubernetes `Prometheus` deployment scrapes metrics from both the Control Plane (`prometheus-fastapi-instrumentator`) and the Sandboxes (`opentelemetry`). 

## 📁 Repository Structure

```text
Ostrich/
├── .github/workflows/     # Automated CI/CD Pipelines (Ruff, Pytest)
├── backend/               # FastAPI Control Plane
│   ├── src/               # Application source code
│   ├── scripts/           # Diagnostic and DB scripts
│   ├── pyproject.toml     # uv dependencies and ruff configuration
│   └── backend.Dockerfile
├── frontend/              # React / Vite Application
├── sandbox/               # LangGraph Agent logic
│   ├── main.py            # Async Pub/Sub LangGraph loop
│   ├── requirements.txt   # Dependencies
│   └── sandbox.Dockerfile
├── infrastructure/        # Infrastructure as Code & Kubernetes Manifests
│   ├── gcp/               # Prometheus, LiteLLM Proxy, and Network Policies
│   └── redis-k8s.yaml     # Redis system for Pub/Sub and Rate Limiting
└── .pre-commit-config.yaml # Local git hooks for PEP-8 compliance
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (for ultra-fast dependency management)
- Docker & Kubernetes (e.g., `kind`, `minikube`, or Docker Desktop)

### 1. Code Quality & Pre-commit Hooks

Ostrich strictly enforces PEP-8 standards using `ruff`. Before committing any code, ensure you have the git hooks installed:
```bash
uv tool install pre-commit
pre-commit install
```

### 2. Local Backend Setup

To run the FastAPI Control Plane locally:
```bash
cd backend
# Sync and create virtual environment
uv sync

# Run the application
uv run python -m src.main
```

### 3. Kubernetes Infrastructure

The Control Plane dynamically spawns Sandbox pods inside the `sandbox-chat` namespace. You must deploy the foundational infrastructure first:

```bash
# 1. Deploy Redis (Used for Pub/Sub between Control Plane and Sandboxes)
kubectl apply -f infrastructure/redis-k8s.yaml

# 2. Deploy the Zero-Trust AI Gateway
export $(grep -v '^#' .env | xargs)
kubectl create namespace ai-gateway
kubectl create secret generic litellm-secrets --from-literal=GEMINI_API_KEY=$GEMINI_API_KEY -n ai-gateway
kubectl apply -f infrastructure/gcp/litellm-proxy.yaml
kubectl apply -f infrastructure/gcp/sandbox-network-policy.yaml

# 3. Deploy Prometheus Observability
kubectl apply -f infrastructure/gcp/prometheus.yaml
```

## 🔌 API Documentation

The control plane exposes the following core endpoints. Interactive documentation is available at `http://localhost:8000/docs`.

### Websockets (Chat)
- `WS /ws/chat?token=<TOKEN>`: Opens a persistent WebSocket connection. The backend authenticates the user, orchestrates a new Sandbox Pod in Kubernetes, and bridges communication between the WebSocket and the Redis Pub/Sub channel.

### Users (Firebase Auth Required)
- `POST /users/`: Create a new PostgreSQL user profile. 
- `GET /users/me`: Retrieve the authenticated profile.
- `PUT /users/{user_id}`: Update a user profile.

### Metrics
- `GET /metrics`: Prometheus scraping endpoint for Control Plane metrics.
