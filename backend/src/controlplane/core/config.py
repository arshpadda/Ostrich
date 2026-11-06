import urllib.parse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgres://postgres:postgres@localhost:5433/ostrich"
    REDIS_URL: str = "redis://localhost:6380"
    GEMINI_API_KEY: str = ""
    # When True, Tortoise auto-creates/alters tables on startup. Keep False in
    # production so Aerich migrations own the schema; enable only for tests.
    GENERATE_SCHEMAS: bool = False
    # agent-sandbox provisioning: the control plane claims a pre-warmed sandbox
    # from this warm pool (see infrastructure/gcp/sandbox-warmpool.yaml).
    SANDBOX_NAMESPACE: str = "sandbox-chat"
    SANDBOX_WARMPOOL: str = "ostrich-warmpool"
    # Optional: pin the kube context for a locally-run control plane (e.g.
    # "ostrich"). Empty = in-cluster config, else the current kubeconfig context.
    SANDBOX_KUBE_CONTEXT: str = ""
    SANDBOX_CLAIM_TIMEOUT_SECONDS: int = 30
    # Per-request (connect, read) timeout for individual Kubernetes API calls, so a
    # slow/hung API server can't pin a threadpool worker indefinitely.
    SANDBOX_KUBE_REQUEST_TIMEOUT_SECONDS: int = 10

    # Durable inbound delivery (see system_design/12_durable_delivery.md). User
    # messages are published to this Pub/Sub topic; a separate dispatcher validates
    # and hands them to the sandbox. PUBSUB_EMULATOR_HOST is honoured by the client
    # library for local dev.
    PROJECT_ID: str = ""
    PUBSUB_TOPIC: str = "user-messages"
    # Public base URL of this service. Sent with each delivery so the sandbox knows
    # where to POST the final reply (/internal/sandbox/reply).
    CONTROLPLANE_PUBLIC_URL: str = "http://localhost:8001"
    # HMAC key shared with the dispatcher only (never given to the sandbox). Signs
    # the short-lived per-delivery token the sandbox presents on its reply callback.
    CALLBACK_SIGNING_SECRET: str = ""

    model_config = {"env_file": "../.env", "extra": "ignore"}


settings = Settings()

connections = {"default": settings.DATABASE_URL}

parsed = urllib.parse.urlparse(settings.DATABASE_URL)
if parsed.query:
    query_params = urllib.parse.parse_qs(parsed.query)
    if "host" in query_params:
        connections["default"] = {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "user": parsed.username,
                "password": parsed.password,
                "database": parsed.path.lstrip("/"),
                "host": query_params["host"][0],
            },
        }

TORTOISE_ORM = {
    "connections": connections,
    "apps": {
        "models": {
            "models": ["src.controlplane.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
