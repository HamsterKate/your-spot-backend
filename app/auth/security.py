from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidAuthTokenError(Exception):
    pass


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "type": TokenType.ACCESS,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def get_refresh_token_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )


def create_refresh_token(
    user_id: UUID,
    jti: UUID,
    expires_at: datetime,
) -> str:
    payload = {
        "sub": str(user_id),
        "type": TokenType.REFRESH,
        "jti": str(jti),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, expected_token_type: TokenType) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.InvalidTokenError as error:
        raise InvalidAuthTokenError from error

    if payload.get("type") != expected_token_type:
        raise InvalidAuthTokenError

    return payload
