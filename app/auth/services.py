from uuid import uuid4, UUID

from datetime import datetime, timezone

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models import RefreshTokenModel, AccessTokenModel
from app.auth.schemas import (
    LoginRequestSchema,
    RegisterRequestSchema,
    TokenResponseSchema,
)
from app.auth.security import (
    get_refresh_token_expiration,
    hash_password,
    verify_password,
    decode_token,
    TokenType,
    InvalidAuthTokenError,
    get_access_token_expiration,
    create_token,
)
from app.auth.token_services import delete_user_tokens, regenerate_tokens
from app.db.session import get_db
from app.users.models import UserModel

bearer_scheme = HTTPBearer()


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(
    db: AsyncSession,
    register_data: RegisterRequestSchema,
) -> UserModel:
    existing_user_id = await db.scalar(
        select(UserModel.id).where(UserModel.email == register_data.email)
    )

    if existing_user_id is not None:
        raise UserAlreadyExistsError

    user = UserModel(
        display_name=register_data.display_name,
        email=register_data.email,
        password_hash=hash_password(register_data.password),
    )

    db.add(user)

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise UserAlreadyExistsError from error

    await db.refresh(user)

    return user


async def login_user(
    db: AsyncSession,
    login_data: LoginRequestSchema,
) -> TokenResponseSchema:
    user = await db.scalar(
        select(UserModel).where(
            UserModel.email == login_data.email,
        )
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(login_data.password, user.password_hash)
    ):
        raise InvalidCredentialsError

    return await regenerate_tokens(db, user)


def _invalid_access_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
    )


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserModel:
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


async def logout_user(db: AsyncSession, current_user: UserModel):
    await delete_user_tokens(db, current_user.id)
