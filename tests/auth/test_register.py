import pytest
from sqlalchemy import func, select

from app.auth.security import verify_password
from app.users.models import UserModel


async def test_register_success(client, register_payload):
    response = await client.post("/auth/register", json=register_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == register_payload["email"]
    assert data["display_name"] == register_payload["display_name"]
    assert "id" in data


async def test_register_does_not_expose_password(client, register_payload):
    response = await client.post("/auth/register", json=register_payload)

    data = response.json()
    assert "password" not in data
    assert "password_hash" not in data


async def test_register_stores_password_hash(client, db_session, register_payload):
    await client.post("/auth/register", json=register_payload)

    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == register_payload["email"])
    )
    assert user is not None
    assert user.password_hash != register_payload["password"]
    assert verify_password(register_payload["password"], user.password_hash)
    assert user.is_active is True


async def test_register_duplicate_email_returns_409(
    client, registered_user, register_payload
):
    response = await client.post("/auth/register", json=register_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists"


async def test_register_duplicate_does_not_create_second_user(
    client, db_session, registered_user, register_payload
):
    await client.post("/auth/register", json=register_payload)

    count = await db_session.scalar(select(func.count()).select_from(UserModel))
    assert count == 1


async def test_register_invalid_email_returns_422(client, register_payload):
    register_payload["email"] = "not-an-email"

    response = await client.post("/auth/register", json=register_payload)

    assert response.status_code == 422


@pytest.mark.parametrize("missing_field", ["display_name", "email", "password"])
async def test_register_missing_field_returns_422(
    client, register_payload, missing_field
):
    register_payload.pop(missing_field)

    response = await client.post("/auth/register", json=register_payload)

    assert response.status_code == 422
