from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.places.models import CategoryModel, TagModel
from app.taxonomy.schemas import (
    CategoryResponseSchema,
    TagResponseSchema,
)
from app.taxonomy.services import get_categories, get_tags
from app.users.models import UserModel

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get(
    "/categories",
    response_model=list[CategoryResponseSchema],
)
async def get_all_categories(
    _: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryModel]:
    return await get_categories(db)


@router.get(
    "/tags",
    response_model=list[TagResponseSchema],
)
async def get_all_tags(
    _: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TagModel]:
    return await get_tags(db)
