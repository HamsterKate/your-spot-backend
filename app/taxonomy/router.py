from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

from app.taxonomy.services import get_categories, get_tags

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get(
    "/categories",
    response_model=dict[UUID, str],
)
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
) -> dict[UUID, str]:
    categories = await get_categories(db)
    return {c.id: c.name for c in categories}


@router.get(
    "/tags",
    response_model=dict[UUID, str],
)
async def get_all_tags(
    db: AsyncSession = Depends(get_db),
) -> dict[UUID, str]:
    tags = await get_tags(db)
    return {t.id: t.name for t in tags}
