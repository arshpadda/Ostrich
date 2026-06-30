from fastapi.testclient import TestClient

from src.controlplane.server import app


def test_health_check() -> None:
    """The back-compat /health endpoint returns 200 OK."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_livez() -> None:
    """Liveness is a pure process check (no dependencies)."""
    with TestClient(app) as client:
        response = client.get("/livez")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


def test_readyz_reports_dependency_checks() -> None:
    """Readiness pings DB + Redis and reports each check. Under the test client
    the in-memory DB is up; Redis may be down — either way the payload lists both
    checks and the status code reflects overall readiness (200 or 503)."""
    with TestClient(app) as client:
        response = client.get("/readyz")
        assert response.status_code in (200, 503)
        body = response.json()
        assert "database" in body["checks"]
        assert "redis" in body["checks"]
