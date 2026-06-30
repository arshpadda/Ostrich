from contextlib import asynccontextmanager
from typing import Dict

import redis.asyncio as redis
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from tortoise import connections
from tortoise.contrib.fastapi import register_tortoise

from .core.auth import init_firebase
from .core.config import TORTOISE_ORM, settings
from .core.logging_config import logging_middleware, setup_logging
from .routers import chat, users

# Configure structured JSON logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK and the shared Redis pool. Owning these in the
    # app lifespan (rather than deprecated router on_event hooks + module globals)
    # gives deterministic startup/shutdown and clean per-app state in tests.
    init_firebase()
    app.state.redis_pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True, health_check_interval=30
    )
    try:
        yield
    finally:
        await app.state.redis_pool.disconnect()


# Instantiate FastAPI application
app = FastAPI(
    title="Ostrich Chatbot API",
    description="Backend services for the Ostrich Chatbot platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Register logging middleware
app.middleware("http")(logging_middleware)

# Auto-instrument FastAPI for OpenTelemetry tracing
FastAPIInstrumentor.instrument_app(app)

# Instrument FastAPI with Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://ostr-499118.web.app", "https://ostr-499118.firebaseapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/livez", status_code=200)
async def livez() -> Dict[str, str]:
    """Liveness: the process is up and the event loop is responsive. No I/O —
    a failure here means Kubernetes should restart the pod."""
    return {"status": "alive"}


@app.get("/readyz")
async def readyz(response: Response) -> Dict[str, object]:
    """Readiness: dependencies are reachable. A failure here means Kubernetes
    should stop routing traffic to this pod (but not restart it)."""
    checks: Dict[str, str] = {}
    ok = True

    # Database round-trip.
    try:
        await connections.get("default").execute_query("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        ok = False

    # Redis round-trip via the shared pool.
    try:
        client = redis.Redis(connection_pool=app.state.redis_pool)
        await client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        ok = False

    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "not_ready", "checks": checks}


# Back-compat alias for existing probes/tests.
@app.get("/health", status_code=200)
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


app.include_router(users.router)
app.include_router(chat.router)
from .routers import ws

app.include_router(ws.router)

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=settings.GENERATE_SCHEMAS,
    add_exception_handlers=True,
)
