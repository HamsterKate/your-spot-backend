from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.places.models import PlaceModel
from app.places.schemas import (
    PlaceCreateRequestSchema,
    PlaceUpdateRequestSchema,
)
from app.users.models import UserModel


async def create_place(
    db: AsyncSession,
    creator: UserModel,
    place_data: PlaceCreateRequestSchema,
) -> PlaceModel:
    place = PlaceModel(
        creator_id=creator.id,
        **place_data.model_dump(),
    )
    db.add(place)

    await db.commit()
    await db.refresh(place)

    return place


async def get_current_user_places(
    db: AsyncSession,
    user: UserModel,
) -> list[PlaceModel]:
    result = await db.scalars(
        select(PlaceModel)
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
        select(PlaceModel).where(
            PlaceModel.id == place_id,
            PlaceModel.creator_id == user.id,
        )
    )


async def update_place(
    db: AsyncSession,
    place: PlaceModel,
    place_data: PlaceUpdateRequestSchema,
) -> PlaceModel:
    for field_name, value in place_data.model_dump(exclude_unset=True).items():
        setattr(place, field_name, value)

    await db.commit()
    await db.refresh(place)

    return place
