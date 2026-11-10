from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    email: EmailStr
    avatar_url: str | None = None
