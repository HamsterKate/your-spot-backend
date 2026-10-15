from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.groups.models import GroupMemberRoleEnum


class GroupCreateRequestSchema(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()

        if not 1 <= len(name) <= 150:
            raise ValueError("Group name must contain from 1 to 150 characters")

        return name

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        description = value.strip()

        return description or None


class GroupResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creator_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class UserGroupResponseSchema(GroupResponseSchema):
    role: GroupMemberRoleEnum
    joined_at: datetime
