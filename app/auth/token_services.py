from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshTokenModel
from app.auth.schemas import RefreshTokenRequestSchema, TokenResponseSchema
from app.auth.security import (
    InvalidAuthTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_refresh_token_expiration,
)
from app.users.models import UserModel


class InvalidRefreshTokenError(Exception):
    pass


async def refresh_tokens(
    db: AsyncSession,
    refresh_data: RefreshTokenRequestSchema,
) -> TokenResponseSchema:
    try:
        payload = decode_token(
            refresh_data.refresh_token,
            expected_token_type=TokenType.REFRESH,
        )
        user_id = UUID(str(payload["sub"]))
        jti = UUID(str(payload["jti"]))
    except (InvalidAuthTokenError, KeyError, TypeError, ValueError) as error:
        raise InvalidRefreshTokenError from error

    refresh_token_model = await db.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.jti == jti,
            RefreshTokenModel.expires_at > datetime.now(timezone.utc),
        )
    )
    user = await db.scalar(
        select(UserModel).where(
            UserModel.id == user_id,
            UserModel.is_active.is_(True),
        )
    )

    if refresh_token_model is None or user is None:
        raise InvalidRefreshTokenError

    await db.delete(refresh_token_model)

    refresh_token_expires_at = get_refresh_token_expiration()
    new_refresh_token_model = RefreshTokenModel(
        user_id=user.id,
        jti=uuid4(),
        expires_at=refresh_token_expires_at,
    )
    db.add(new_refresh_token_model)
    await db.commit()

    return TokenResponseSchema(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(
            user_id=user.id,
            jti=new_refresh_token_model.jti,
            expires_at=refresh_token_expires_at,
        ),
    )
