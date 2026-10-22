from uuid import UUID

import pytest
from sqlalchemy import select

from app.auth.models import RefreshTokenModel


async def test_logout_success_returns_204_empty_body(client, auth_headers):
    response = await client.get("/auth/logout", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""


async def test_logout_without_credentials_is_rejected(client):
    response = await client.get("/auth/logout")

    # HTTPBearer returns 403 on older FastAPI versions and 401 on newer ones
    assert response.status_code in (401, 403)


async def test_logout_with_invalid_token_returns_401(client):
    response = await client.get(
        "/auth/logout", headers={"Authorization": "Bearer not.a.jwt"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


async def test_logout_with_refresh_token_returns_401(client, tokens):
    """A refresh token must not be accepted as an access token."""
    response = await client.get(
        "/auth/logout", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert response.status_code == 401


async def test_logout_deletes_refresh_tokens(
    client, db_session, registered_user, auth_headers
):
    await client.get("/auth/logout", headers=auth_headers)

    rows = (
        await db_session.scalars(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == UUID(registered_user["id"])
            )
        )
    ).all()
    assert rows == []


async def test_refresh_fails_after_logout(client, tokens, auth_headers):
    await client.get("/auth/logout", headers=auth_headers)

    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401


async def test_access_token_is_invalid_after_logout(client, auth_headers):
    await client.get("/auth/logout", headers=auth_headers)

    second = await client.get("/auth/logout", headers=auth_headers)

    assert second.status_code == 401
