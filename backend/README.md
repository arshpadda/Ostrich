# Ostrich Application

Core Python application code for the Ostrich platform.

## Development

Use [uv](https://github.com/astral-sh/uv) to manage dependencies:

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest
```

## Docker Local Execution

To containerize and run the application locally:

### 1. Build the Docker Image
Navigate to the `package/` folder and run the build:
```bash
docker build -t ostrich-app .
```

### 2. Run the Container
Run the container forwarding port `8000`:
```bash
docker run -d --name ostrich-container -p 8000:8000 ostrich-app
```

### 3. Verify Endpoint
Test the container health API:
```bash
curl -i http://localhost:8000/health
```

### 4. Cleanup
Stop and remove the container:
```bash
docker stop ostrich-container
docker rm ostrich-container
```
