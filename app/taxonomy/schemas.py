from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None


class TagResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
