from fastapi.security import HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.schemas import (
    LoginRequestSchema,
    RegisterRequestSchema,
    TokenResponseSchema,
)
from app.auth.security import (
    hash_password,
    verify_password,
)
from app.auth.token_services import delete_user_tokens, regenerate_tokens
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


async def logout_user(db: AsyncSession, current_user: UserModel):
    await delete_user_tokens(db, current_user.id)
