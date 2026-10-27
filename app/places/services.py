from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.places.models import (
    CategoryModel,
    PlaceCategoryModel,
    PlaceModel,
    PlaceTagModel,
    TagModel,
)
from app.places.schemas import (
    PlaceCreateRequestSchema,
    PlaceUpdateRequestSchema,
)
from app.users.models import UserModel


class CategoryNotFoundError(Exception):
    pass


async def get_place_with_taxonomy(
    db: AsyncSession,
    place_id: UUID,
) -> PlaceModel | None:
    return await db.scalar(
        select(PlaceModel)
        .options(
            selectinload(PlaceModel.categories),
            selectinload(PlaceModel.tags),
        )
        .where(PlaceModel.id == place_id)
    )


async def get_categories_by_ids(
    db: AsyncSession,
    category_ids: list[UUID],
) -> list[CategoryModel]:
    if not category_ids:
        return []

    categories = list(
        await db.scalars(
            select(CategoryModel).where(CategoryModel.id.in_(category_ids))
        )
    )

    if len(categories) != len(category_ids):
        raise CategoryNotFoundError

    return categories


async def get_or_create_tags(
    db: AsyncSession,
    tag_names: list[str],
) -> list[TagModel]:
    if not tag_names:
        return []

    existing_tags = list(
        await db.scalars(select(TagModel).where(TagModel.name.in_(tag_names)))
    )
    tags_by_name = {tag.name: tag for tag in existing_tags}

    new_tags = [
        TagModel(name=tag_name)
        for tag_name in tag_names
        if tag_name not in tags_by_name
    ]
    db.add_all(new_tags)

    await db.flush()

    tags_by_name.update({tag.name: tag for tag in new_tags})

    return [tags_by_name[tag_name] for tag_name in tag_names]


async def replace_place_categories(
    db: AsyncSession,
    place: PlaceModel,
    category_ids: list[UUID],
) -> None:
    categories = await get_categories_by_ids(db, category_ids)

    await db.execute(
        delete(PlaceCategoryModel).where(PlaceCategoryModel.place_id == place.id)
    )
    db.add_all(
        [
            PlaceCategoryModel(
                place_id=place.id,
                category_id=category.id,
            )
            for category in categories
        ]
    )


async def replace_place_tags(
    db: AsyncSession,
    place: PlaceModel,
    tag_names: list[str],
) -> None:
    tags = await get_or_create_tags(db, tag_names)

    await db.execute(delete(PlaceTagModel).where(PlaceTagModel.place_id == place.id))
    db.add_all(
        [
            PlaceTagModel(
                place_id=place.id,
                tag_id=tag.id,
            )
            for tag in tags
        ]
    )


async def create_place(
    db: AsyncSession,
    creator: UserModel,
    place_data: PlaceCreateRequestSchema,
) -> PlaceModel:
    place = PlaceModel(
        creator_id=creator.id,
        **place_data.model_dump(exclude={"category_ids", "tags"}),
    )
    db.add(place)

    await db.flush()

    await replace_place_categories(db, place, place_data.category_ids)
    await replace_place_tags(db, place, place_data.tags)

    await db.commit()

    created_place = await get_place_with_taxonomy(db, place.id)

    if created_place is None:
        raise RuntimeError("Created place not found")

    return created_place


async def get_current_user_places(
    db: AsyncSession,
    user: UserModel,
) -> list[PlaceModel]:
    result = await db.scalars(
        select(PlaceModel)
        .options(
            selectinload(PlaceModel.categories),
            selectinload(PlaceModel.tags),
        )
        .where(PlaceModel.creator_id == user.id)
        .order_by(PlaceModel.created_at.desc())
    )

    return list(result)


async def get_current_user_place(
    db: AsyncSession,
    user: UserModel,
    place_id: UUID,
) -> PlaceModel | None:
    return await db.scalar(
        select(PlaceModel)
        .options(
            selectinload(PlaceModel.categories),
            selectinload(PlaceModel.tags),
        )
        .where(
            PlaceModel.id == place_id,
            PlaceModel.creator_id == user.id,
        )
    )


async def update_place(
    db: AsyncSession,
    place: PlaceModel,
    place_data: PlaceUpdateRequestSchema,
) -> PlaceModel:
    update_data = place_data.model_dump(
        exclude_unset=True,
        exclude={"category_ids", "tags"},
    )

    for field_name, value in update_data.items():
        setattr(place, field_name, value)

    if "category_ids" in place_data.model_fields_set:
        await replace_place_categories(
            db,
            place,
            place_data.category_ids or [],
        )

    if "tags" in place_data.model_fields_set:
        await replace_place_tags(
            db,
            place,
            place_data.tags or [],
        )

    await db.commit()
    await db.refresh(place, attribute_names=["categories", "tags"])

    return place


async def delete_place(
    db: AsyncSession,
    place: PlaceModel,
) -> None:
    await db.delete(place)
    await db.commit()
