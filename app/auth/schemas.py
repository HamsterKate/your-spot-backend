import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class RegisterRequestSchema(BaseModel):
    first_name: str
    username: str
    email: EmailStr | None = None
    phone: str | None = None
    password: str

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        first_name = value.strip()

        if not 1 <= len(first_name) <= 100:
            raise ValueError("First name must contain from 1 to 100 characters")

        return first_name

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip().lower()

        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError(
                "Username must contain 3-30 lowercase letters, digits, or underscores"
            )

        return username

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return value.lower() if value else None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        phone = value.strip().replace(" ", "").replace("-", "")

        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Phone must be in E.164 format, for example +380501234567")

        return phone

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not 8 <= len(value) <= 128:
            raise ValueError("Password must contain from 8 to 128 characters")

        return value

    @model_validator(mode="after")
    def validate_contact(self) -> "RegisterRequestSchema":
        if self.email is None and self.phone is None:
            raise ValueError("Provide an email or phone number")

        return self


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    username: str
    email: EmailStr | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequestSchema(BaseModel):
    identifier: str
    password: str

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        identifier = value.strip()

        if not identifier:
            raise ValueError("Email or phone number is required")

        if "@" in identifier:
            return identifier.lower()

        phone = identifier.replace(" ", "").replace("-", "")

        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError(
                "Provide a valid email or phone in E.164 format, "
                "for example +380501234567"
            )

        return phone

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
