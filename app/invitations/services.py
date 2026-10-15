from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.groups.models import GroupMemberModel, GroupMemberRoleEnum, GroupModel
from app.invitations.models import GroupInvitationModel
from app.users.models import UserModel


async def create_invitation(
    db: AsyncSession,
    group_id: UUID,
    current_user: UserModel,
) -> GroupInvitationModel:
    group = await db.get(GroupModel, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    membership = await db.scalar(
        select(GroupMemberModel).where(
            GroupMemberModel.group_id == group_id,
            GroupMemberModel.user_id == current_user.id,
        )
    )

    if membership is None or membership.role != GroupMemberRoleEnum.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can create invitations",
        )

    invitation = GroupInvitationModel(
        group_id=group_id,
        created_by_id=current_user.id,
    )
    db.add(invitation)

    await db.commit()
    await db.refresh(invitation)

    return invitation
