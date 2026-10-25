from sqlalchemy.ext.asyncio import AsyncSession

from app.places.models import PlaceModel
from app.places.schemas import PlaceCreateRequestSchema
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
