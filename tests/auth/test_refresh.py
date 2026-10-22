"""Refresh tests.

NOTE: `token_services.py` wasn't visible when these were written. They assume
the request body is {"refresh_token": "..."} and that refresh tokens are
single-use (rotated). Adjust if your implementation differs.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.auth.security import TokenType, create_token


async def test_refresh_success_returns_new_tokens(client, tokens):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


async def test_refresh_rotates_refresh_token(client, tokens):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.json()["refresh_token"] != tokens["refresh_token"]


async def test_refresh_token_cannot_be_reused(client, tokens):
    first = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert second.status_code == 401


async def test_refresh_new_access_token_works(client, tokens):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    new_access = response.json()["access_token"]

    logout = await client.get(
        "/auth/logout", headers={"Authorization": f"Bearer {new_access}"}
    )

    assert logout.status_code == 204


async def test_refresh_garbage_token_returns_401(client):
    response = await client.post("/auth/refresh", json={"refresh_token": "not.a.jwt"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


async def test_refresh_with_access_token_returns_401(client, tokens):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


async def test_refresh_expired_token_returns_401(client, registered_user):
    expired = create_token(
        user_id=UUID(registered_user["id"]),
        jti=uuid4(),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        token_type=TokenType.REFRESH,
    )

    response = await client.post("/auth/refresh", json={"refresh_token": expired})

    assert response.status_code == 401


async def test_refresh_valid_signature_but_unknown_jti_returns_401(
    client, registered_user
):
    """A correctly signed token that was never stored in the DB must be rejected."""
    forged = create_token(
        user_id=UUID(registered_user["id"]),
        jti=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        token_type=TokenType.REFRESH,
    )

    response = await client.post("/auth/refresh", json={"refresh_token": forged})

    assert response.status_code == 401


async def test_refresh_missing_body_returns_422(client):
    response = await client.post("/auth/refresh", json={})

    assert response.status_code == 422
