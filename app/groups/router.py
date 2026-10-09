from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.groups.schemas import (
    GroupCreateRequestSchema,
    GroupResponseSchema,
    UserGroupResponseSchema,
)
from app.groups.services import create_group, get_user_groups
from app.users.models import UserModel

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[UserGroupResponseSchema])
async def get_groups(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserGroupResponseSchema]:
    return await get_user_groups(db, current_user)


@router.post(
    "",
    response_model=GroupResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_group(
    group_data: GroupCreateRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupResponseSchema:
    return await create_group(
        db=db,
        owner=current_user,
        group_data=group_data,
    )
