from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.places.models import CategoryModel, TagModel


async def get_categories(db: AsyncSession) -> list[CategoryModel]:
    result = await db.scalars(select(CategoryModel).order_by(CategoryModel.name))

    return list(result)


async def get_tags(db: AsyncSession) -> list[TagModel]:
    result = await db.scalars(select(TagModel).order_by(TagModel.name))

    return list(result)
