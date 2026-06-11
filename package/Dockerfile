# Stage 1: Build the virtual environment using uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation and disable linking to speed up builds
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency configuration files first to cache layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy project configuration and application source files
COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src

# Synchronize the project (installs ostrich-app itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Final runtime container
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy sync virtual environment from builder stage
COPY --from=builder /app /app

# Add virtual environment binaries to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the API port
EXPOSE 8000

# Run the FastAPI application using uvicorn (which is in the virtual env)
CMD ["python", "-m", "src.main"]
