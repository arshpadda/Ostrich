import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.controlplane.auth import get_current_user
from src.controlplane.server import app

# Mock Firebase Auth dependency
mock_uid = uuid.uuid4().hex
mock_email = f"test_{mock_uid}@example.com"


async def mock_get_current_user():
    return {"uid": mock_uid, "email": mock_email}


app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest.mark.anyio
async def test_user_crud():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create a user
        response = await client.post(
            "/users/",
            json={
                "email": "test@example.com",
                "first_name": "John",
                "last_name": "Doe",
            },
        )
        assert response.status_code == 201
        user = response.json()
        assert user["email"] == mock_email
        user_id = user["id"]

        # 2. Read the user
        response = await client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

        # 3. Update the user
        response = await client.put(f"/users/{user_id}", json={"first_name": "Jane"})
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"
        assert response.json()["last_name"] == "Doe"

        # 4. Get current user profile
        response = await client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

        # 5. Delete the user
        response = await client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # 6. Verify deletion
        response = await client.get(f"/users/{user_id}")
        assert response.status_code == 404
