import uuid

from fastapi.testclient import TestClient

from src.controlplane.auth import get_current_user
from src.controlplane.server import app

# Mock Firebase Auth dependency
mock_uid = uuid.uuid4().hex
mock_email = f"test_{mock_uid}@example.com"


async def mock_get_current_user():
    return {"uid": mock_uid, "email": mock_email}


app.dependency_overrides[get_current_user] = mock_get_current_user


def test_user_crud():
    with TestClient(app) as client:
        # 1. Create a user
        response = client.post("/users/", json={"email": "test@example.com", "first_name": "John", "last_name": "Doe"})
        assert response.status_code == 201
        user = response.json()
        assert user["email"] == mock_email
        user_id = user["id"]

        # 2. Read the user
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

        # 3. Update the user
        response = client.put(f"/users/{user_id}", json={"first_name": "Jane"})
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"
        assert response.json()["last_name"] == "Doe"

        # 4. Get current user profile
        response = client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

        # 5. Delete the user
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # 6. Verify deletion
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 404
