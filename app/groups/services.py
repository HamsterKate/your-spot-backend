from sqlalchemy.ext.asyncio import AsyncSession

from app.groups.models import GroupMemberModel, GroupMemberRoleEnum, GroupModel
from app.groups.schemas import GroupCreateRequestSchema
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
