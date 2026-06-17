FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Create workspace dir for the agent
RUN mkdir -p /workspace && chown 1337:1337 /workspace

WORKDIR /app

# Install python dependencies using uv
COPY sandbox/pyproject.toml .
COPY sandbox/uv.lock .
COPY sandbox/README.md .
RUN uv sync --frozen

# Copy the agent harness and CLI
COPY sandbox/src ./src
COPY sandbox/cli.py .
COPY sandbox/system_prompt.txt .

# Run the harness by default
CMD ["uv", "run", "python", "-m", "src.main"]
