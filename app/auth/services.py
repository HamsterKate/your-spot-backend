from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshTokenModel
from app.auth.schemas import (
    LoginRequestSchema,
    RegisterRequestSchema,
    TokenResponseSchema,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_expiration,
    hash_password,
    verify_password,
)
from app.users.models import UserModel


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(
    db: AsyncSession,
    register_data: RegisterRequestSchema,
) -> UserModel:
    unique_fields = [UserModel.username == register_data.username]

    if register_data.email:
        unique_fields.append(UserModel.email == register_data.email)

    if register_data.phone:
        unique_fields.append(UserModel.phone == register_data.phone)

    existing_user_id = await db.scalar(select(UserModel.id).where(or_(*unique_fields)))

    if existing_user_id is not None:
        raise UserAlreadyExistsError

    user = UserModel(
        first_name=register_data.first_name,
        username=register_data.username,
        email=register_data.email,
        phone=register_data.phone,
        hashed_password=hash_password(register_data.password),
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
            or_(
                UserModel.email == login_data.identifier,
                UserModel.phone == login_data.identifier,
            )
        )
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(login_data.password, user.hashed_password)
    ):
        raise InvalidCredentialsError

    refresh_token_expires_at = get_refresh_token_expiration()
    refresh_token_model = RefreshTokenModel(
        user_id=user.id,
        jti=uuid4(),
        expires_at=refresh_token_expires_at,
    )

    db.add(refresh_token_model)
    await db.commit()

    return TokenResponseSchema(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(
            user_id=user.id,
            jti=refresh_token_model.jti,
            expires_at=refresh_token_expires_at,
        ),
    )
