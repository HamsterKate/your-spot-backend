from uuid import UUID

import pytest
from sqlalchemy import select

from app.auth.models import AccessTokenModel, RefreshTokenModel
from app.auth.security import TokenType, decode_token
from app.users.models import UserModel

from tests.conftest import PASSWORD


async def _login(client, email, password):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_login_success_returns_tokens(client, registered_user, register_payload):
    response = await _login(client, register_payload["email"], PASSWORD)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["access_token"], str) and data["access_token"]
    assert isinstance(data["refresh_token"], str) and data["refresh_token"]
    assert data["access_token"] != data["refresh_token"]


async def test_login_tokens_are_valid_and_typed(
    client, registered_user, register_payload
):
    response = await _login(client, register_payload["email"], PASSWORD)
    data = response.json()

    access_payload = decode_token(
        data["access_token"], expected_token_type=TokenType.ACCESS
    )
    refresh_payload = decode_token(
        data["refresh_token"], expected_token_type=TokenType.REFRESH
    )

    assert access_payload["sub"] == registered_user["id"]
    assert refresh_payload["sub"] == registered_user["id"]


async def test_login_stores_token_records(
    client, db_session, registered_user, register_payload
):
    await _login(client, register_payload["email"], PASSWORD)

    user_id = UUID(registered_user["id"])
    access_rows = (
        await db_session.scalars(
            select(AccessTokenModel).where(AccessTokenModel.user_id == user_id)
        )
    ).all()
    refresh_rows = (
        await db_session.scalars(
            select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
        )
    ).all()

    assert len(access_rows) == 1
    assert len(refresh_rows) == 1


async def test_login_wrong_password_returns_401(
    client, registered_user, register_payload
):
    response = await _login(client, register_payload["email"], "WrongPassword1!")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_unknown_email_returns_401(client):
    response = await _login(client, "nobody@example.com", PASSWORD)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_login_error_is_identical_for_unknown_email_and_wrong_password(
    client, registered_user, register_payload
):
    """The API must not reveal which emails are registered."""
    wrong_password = await _login(client, register_payload["email"], "WrongPassword1!")
    unknown_email = await _login(client, "nobody@example.com", PASSWORD)

    assert wrong_password.status_code == unknown_email.status_code
    assert wrong_password.json() == unknown_email.json()


async def test_login_inactive_user_returns_401(
    client, db_session, registered_user, register_payload
):
    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == register_payload["email"])
    )
    user.is_active = False
    await db_session.commit()

    response = await _login(client, register_payload["email"], PASSWORD)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"password": PASSWORD},  # missing email
        {"email": "user@example.com"},  # missing password
        {"email": "not-an-email", "password": PASSWORD},  # malformed email
        {},
    ],
)
async def test_login_invalid_payload_returns_422(client, payload):
    response = await client.post("/auth/login", json=payload)

    assert response.status_code == 422
