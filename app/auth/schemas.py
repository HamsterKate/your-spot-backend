from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)


class RegisterRequestSchema(BaseModel):
    display_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)
    ]
    email: EmailStr
    password: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=128)
    ]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRefreshResponseSchema(TokenResponseSchema):
    id: UUID
    display_name: str
    email: EmailStr


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str
