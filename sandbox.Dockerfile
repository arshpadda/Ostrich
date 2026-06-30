FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Flush stdout/stderr so JSON logs appear in real time (no block buffering).
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Create workspace dir for the agent, owned by the non-root runtime user
RUN mkdir -p /workspace && chown 1337:1337 /workspace

WORKDIR /app

# Install python dependencies using uv
COPY sandbox/pyproject.toml .
COPY sandbox/uv.lock .
COPY sandbox/README.md .
RUN uv sync --frozen --no-dev

# Copy the agent harness and CLI
COPY sandbox/src ./src
COPY sandbox/cli.py .
COPY sandbox/system_prompt.txt .

# Drop root: the agent executes LLM-generated code, so run it unprivileged
# (defense-in-depth alongside gVisor).
USER 1337

# Run the harness directly via the baked virtualenv — NOT `uv run`, which
# re-syncs on every start and adds seconds to warm-pool cold starts.
CMD ["/app/.venv/bin/python", "-m", "src.main"]
