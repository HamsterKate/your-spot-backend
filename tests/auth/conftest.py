import pytest
import pytest_asyncio

PASSWORD = "StrongPass123!"


@pytest.fixture
def register_payload() -> dict:
    return {
        "display_name": "Test User",
        "email": "user@example.com",
        "password": PASSWORD,
    }


@pytest_asyncio.fixture
async def registered_user(client, register_payload) -> dict:
    response = await client.post("/auth/register", json=register_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest_asyncio.fixture
async def tokens(client, registered_user, register_payload) -> dict:
    response = await client.post(
        "/auth/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def auth_headers(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
