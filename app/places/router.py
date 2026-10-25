from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.places.schemas import (
    PlaceCreateRequestSchema,
    PlaceResponseSchema,
)
from app.places.services import create_place
from app.users.models import UserModel

router = APIRouter(prefix="/places", tags=["places"])


@router.post(
    "",
    response_model=PlaceResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_place(
    place_data: PlaceCreateRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaceResponseSchema:
    return await create_place(
        db=db,
        creator=current_user,
        place_data=place_data,
    )
