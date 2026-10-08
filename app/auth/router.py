from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RegisterRequestSchema, UserResponseSchema
from app.auth.services import UserAlreadyExistsError, register_user
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    register_data: RegisterRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    try:
        return await register_user(db, register_data)
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username, email, or phone already exists",
        ) from error
