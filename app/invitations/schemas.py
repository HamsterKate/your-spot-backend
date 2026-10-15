from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvitationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    token: str
    expires_at: datetime
    is_active: bool
    created_at: datetime
