from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AccessTokenModel
from app.auth.security import (
    InvalidAuthTokenError,
    TokenType,
    decode_token,
)
from app.db.session import get_db
from app.users.models import UserModel

bearer_scheme = HTTPBearer(auto_error=False)


def _invalid_access_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
    )


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserModel:
    if credentials is None:
        raise _invalid_access_token_error()

    try:
        payload = decode_token(
            credentials.credentials,
            expected_token_type=TokenType.ACCESS,
        )
        user_id = UUID(str(payload["sub"]))
        jti = UUID(str(payload["jti"]))
    except (InvalidAuthTokenError, KeyError, TypeError, ValueError) as error:
        raise _invalid_access_token_error() from error

    user = await db.scalar(
        select(UserModel)
        .join(AccessTokenModel, AccessTokenModel.user_id == UserModel.id)
        .where(
            UserModel.id == user_id,
            UserModel.is_active.is_(True),
            AccessTokenModel.jti == jti,
            AccessTokenModel.expires_at > datetime.now(timezone.utc),
        )
    )
    if user is None:
        raise _invalid_access_token_error()

    return user
