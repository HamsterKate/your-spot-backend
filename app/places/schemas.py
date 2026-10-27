from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from app.taxonomy.schemas import CategoryResponseSchema, TagResponseSchema


def normalize_tags(tags: list[str]) -> list[str]:
    normalized_tags = [" ".join(tag.split()).lower() for tag in tags]

    if any(not tag for tag in normalized_tags):
        raise ValueError("Tags cannot be empty")

    if any(len(tag) > 100 for tag in normalized_tags):
        raise ValueError("Each tag must contain no more than 100 characters")

    if len(normalized_tags) != len(set(normalized_tags)):
        raise ValueError("Tags must be unique")

    return normalized_tags


class PlaceCreateRequestSchema(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opening_hours: dict[str, object] | None = None
    category_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

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

    @field_validator("category_ids")
    @classmethod
    def validate_category_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Category IDs must be unique")

        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)


class PlaceUpdateRequestSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opening_hours: dict[str, object] | None = None
    category_ids: list[UUID] | None = None
    tags: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

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
            raise ValueError("Address must contain at most 500 characters")

        return address or None

    @model_validator(mode="after")
    def validate_update_data(self) -> "PlaceUpdateRequestSchema":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")

        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null")

        return self

    @field_validator("category_ids")
    @classmethod
    def validate_category_ids(
        cls,
        value: list[UUID] | None,
    ) -> list[UUID] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Category IDs must be unique")

        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        return normalize_tags(value)


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
    categories: list[CategoryResponseSchema]
    tags: list[TagResponseSchema]
