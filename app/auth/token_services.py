from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshTokenModel, AccessTokenModel
from app.auth.schemas import TokenResponseSchema, RefreshTokenRequestSchema
from app.auth.security import (
    TokenType,
    create_token,
    get_refresh_token_expiration,
    get_access_token_expiration,
    decode_token,
    InvalidAuthTokenError,
)
from app.users.models import UserModel


class InvalidRefreshTokenError(Exception):
    pass


class InvalidAccessTokenError(Exception):
    pass


async def delete_user_tokens(db: AsyncSession, user_id: UUID) -> None:
    """Stage deletion of every access and refresh token of the user (no commit)."""
    await db.execute(
        delete(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
    )
    await db.execute(
        delete(AccessTokenModel).where(AccessTokenModel.user_id == user_id)
    )


def _stage_token(
    db: AsyncSession,
    model_cls: type[AccessTokenModel] | type[RefreshTokenModel],
    token_type: TokenType,
    user_id: UUID,
    expires_at: datetime,
) -> str:
    """Add a token row to the session and return the matching signed JWT."""
    jti = uuid4()
    db.add(model_cls(user_id=user_id, jti=jti, expires_at=expires_at))
    return create_token(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
        token_type=token_type,
    )


async def regenerate_tokens(db: AsyncSession, user: UserModel) -> TokenResponseSchema:
    """Replace all the user's tokens with a fresh access/refresh pair."""
    await delete_user_tokens(db, user.id)

    token_pair = TokenResponseSchema(
        access_token=_stage_token(
            db,
            AccessTokenModel,
            TokenType.ACCESS,
            user.id,
            get_access_token_expiration(),
        ),
        refresh_token=_stage_token(
            db,
            RefreshTokenModel,
            TokenType.REFRESH,
            user.id,
            get_refresh_token_expiration(),
        ),
    )
    await db.commit()  # insert happens in one transaction

    return token_pair


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

    return await regenerate_tokens(db, user)
