from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class RegisterRequestSchema(BaseModel):
    display_name: str
    email: EmailStr
    password: str

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        display_name = value.strip()

        if not 1 <= len(display_name) <= 50:
            raise ValueError("Display name must contain from 1 to 50 characters")

        return display_name

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not 8 <= len(value) <= 128:
            raise ValueError("Password must contain from 8 to 128 characters")

        return value


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Password is required")

        return value


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str
