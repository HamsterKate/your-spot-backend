from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceCreateRequestSchema(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opening_hours: dict[str, object] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()

        if not 1 <= len(name) <= 255:
            raise ValueError("Name must contain from 1 to 255 characters")

        return name

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None

        address = value.strip()

        if len(address) > 500:
            raise ValueError("Address must contain no more than 500 characters")

        return address or None


class PlaceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creator_id: UUID
    name: str
    description: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    opening_hours: dict[str, object] | None
    created_at: datetime
    updated_at: datetime
