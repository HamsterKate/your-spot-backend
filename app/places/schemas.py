from datetime import datetime, time
from typing import Annotated
from uuid import UUID
from typing_extensions import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
    field_serializer,
    computed_field,
)

from app.core.config import settings
from app.places.helpers import validate_location
from app.taxonomy.schemas import CategoryResponseSchema, TagResponseSchema

PlaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
PlaceAddress = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


def normalize_tags(tags: list[str]) -> list[str]:
    normalized_tags = [" ".join(tag.split()).lower() for tag in tags]

    if any(not tag for tag in normalized_tags):
        raise ValueError("Tags cannot be empty")

    if any(len(tag) > 100 for tag in normalized_tags):
        raise ValueError("Each tag must contain no more than 100 characters")

    if len(normalized_tags) != len(set(normalized_tags)):
        raise ValueError("Tags must be unique")

    return normalized_tags


class OpeningHoursSchema(BaseModel):
    """Lenient: used for responses / reading what's already in the DB."""

    model_config = ConfigDict(extra="ignore")

    opens_at: time | None = Field(examples=["09:00"], default=None)
    closes_at: time | None = Field(examples=["18:00"], default=None)

    @field_serializer("opens_at", "closes_at")
    def serialize_time(self, value: time | None) -> str | None:
        if isinstance(value, time):
            return value.strftime("%H:%M")
        return value


class OpeningHoursCreateUpdateSchema(OpeningHoursSchema):
    """Strict: used only for incoming requests."""

    model_config = ConfigDict(extra="forbid")

    opens_at: time = Field(examples=["09:00"])
    closes_at: time = Field(examples=["18:00"])

    @model_validator(mode="after")
    def validate_range(self) -> "OpeningHoursCreateUpdateSchema":
        if self.opens_at >= self.closes_at:
            raise ValueError("Opening hour must be earlier than closing hour")
        return self


class PlaceValidationMixin:
    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("category_ids")
    @classmethod
    def validate_category_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if cls is PlaceUpdateRequestSchema and value is None:
            return None

        if len(value) != len(set(value)):
            raise ValueError("Category IDs must be unique")

        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if cls is PlaceUpdateRequestSchema and value is None:
            return None

        return normalize_tags(value)

    @model_validator(mode="after")
    def validate_location(self) -> Self:
        if isinstance(self, PlaceUpdateRequestSchema):
            # validation happens on the merged data in the service layer,
            # so we skip it here
            return self

        validate_location(self.address, self.latitude, self.longitude)
        return self


class PlaceCreateRequestSchema(PlaceValidationMixin, BaseModel):
    name: PlaceName
    description: str | None = None
    address: PlaceAddress | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opening_hours: OpeningHoursCreateUpdateSchema | None = None
    category_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PlaceUpdateRequestSchema(PlaceValidationMixin, BaseModel):
    name: PlaceName | None = None
    description: str | None = None
    address: PlaceAddress | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opening_hours: OpeningHoursCreateUpdateSchema | None = None
    category_ids: list[UUID] | None = None
    tags: list[str] | None = None

    @model_validator(mode="after")
    def validate_update_data(self) -> "PlaceUpdateRequestSchema":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")

        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null")

        return self


class PlacePhotoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    place_id: UUID
    name: str
    content_type: str
    position: int
    created_at: datetime
    url: str | None = None


class PlaceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creator_id: UUID
    name: str
    description: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    opening_hours: OpeningHoursSchema | None = None
    created_at: datetime
    updated_at: datetime
    categories: list[CategoryResponseSchema]
    tags: list[TagResponseSchema]
    photos: list[PlacePhotoResponseSchema] = Field(default_factory=list)
    creator_name: str

    @computed_field
    @property
    def url(self) -> str:
        return f"{settings.api_v1_prefix}/places/{self.id}"
