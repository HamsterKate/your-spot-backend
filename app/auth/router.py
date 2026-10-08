from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequestSchema,
    RefreshTokenRequestSchema,
    RegisterRequestSchema,
    TokenResponseSchema,
    UserResponseSchema,
)
from app.auth.services import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    login_user,
    register_user,
)
from app.auth.token_services import InvalidRefreshTokenError, refresh_tokens
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


@router.post("/login", response_model=TokenResponseSchema)
async def login(
    login_data: LoginRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenResponseSchema:
    try:
        return await login_user(db, login_data)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, phone number, or password",
        ) from error


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh(
    refresh_data: RefreshTokenRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenResponseSchema:
    try:
        return await refresh_tokens(db, refresh_data)
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from error
