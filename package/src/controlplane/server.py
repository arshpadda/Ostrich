import logging
import sys
from typing import Dict

from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from .db import TORTOISE_ORM
from .routers import users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("ostrich-controlplane")

from contextlib import asynccontextmanager
from .auth import init_firebase
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK
    init_firebase()
    yield

# Instantiate FastAPI application
app = FastAPI(
    title="Ostrich Chatbot API",
    description="Backend services for the Ostrich Chatbot platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=200)
async def health_check() -> Dict[str, str]:
    """Health check endpoint to verify that the service is running.

    Performance Note (Bolt ⚡):
    Defined as `async def` because there are no blocking I/O operations.
    FastAPI will run this directly on the main event loop rather than
    dispatching it to an external threadpool, reducing overhead and latency.

    Returns:
        A dictionary containing the status of the application.
    """
    logger.info("Health check endpoint hit")
    return {"status": "healthy"}

app.include_router(users.router)

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
