from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.groups.models import GroupMemberModel, GroupMemberRoleEnum, GroupModel
from app.groups.schemas import (
    GroupCreateRequestSchema,
    UserGroupResponseSchema,
)
from app.users.models import UserModel


async def create_group(
    db: AsyncSession,
    owner: UserModel,
    group_data: GroupCreateRequestSchema,
) -> GroupModel:
    group = GroupModel(
        name=group_data.name,
        description=group_data.description,
    )
    db.add(group)

    await db.flush()

    group_member = GroupMemberModel(
        group_id=group.id,
        user_id=owner.id,
        role=GroupMemberRoleEnum.OWNER,
    )
    db.add(group_member)

    await db.commit()
    await db.refresh(group)

    return group


async def get_user_groups(
    db: AsyncSession,
    user: UserModel,
) -> list[UserGroupResponseSchema]:
    result = await db.execute(
        select(
            GroupModel,
            GroupMemberModel.role,
            GroupMemberModel.joined_at,
        )
        .join(
            GroupMemberModel,
            GroupMemberModel.group_id == GroupModel.id,
        )
        .where(GroupMemberModel.user_id == user.id)
        .order_by(GroupModel.created_at.desc())
    )

    return [
        UserGroupResponseSchema(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            updated_at=group.updated_at,
            role=role,
            joined_at=joined_at,
        )
        for group, role, joined_at in result.all()
    ]
