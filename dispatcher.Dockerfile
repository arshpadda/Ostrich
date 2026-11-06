FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY dispatcher/pyproject.toml dispatcher/uv.lock dispatcher/README.md /app/
RUN uv sync --frozen --no-install-project --no-dev
COPY dispatcher/src /app/src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER 1337
CMD ["python", "-m", "src.main"]
