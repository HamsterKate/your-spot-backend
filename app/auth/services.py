from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RegisterRequestSchema
from app.auth.security import hash_password
from app.users.models import UserModel


class UserAlreadyExistsError(Exception):
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
