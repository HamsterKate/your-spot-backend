from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.invitations.schemas import InvitationResponseSchema
from app.invitations.services import create_invitation
from app.users.models import UserModel

router = APIRouter(tags=["invitations"])


@router.post(
    "/groups/{group_id}/invitations",
    response_model=InvitationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_group_invitation(
    group_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponseSchema:
    return await create_invitation(
        db=db,
        group_id=group_id,
        current_user=current_user,
    )
