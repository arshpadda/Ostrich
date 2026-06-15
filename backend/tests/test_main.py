from fastapi.testclient import TestClient

from src.controlplane.server import app

client = TestClient(app)


def test_health_check() -> None:
    """Test that the /health endpoint returns 200 OK and correct JSON payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
