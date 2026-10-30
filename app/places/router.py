from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Request,
    Response
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.places.models import PlaceModel
from app.places.schemas import (
    PlaceCreateRequestSchema,
    PlaceResponseSchema,
    PlaceUpdateRequestSchema,
)
from app.places.services import (
    CategoryNotFoundError,
    create_place,
    delete_place,
    get_current_user_place,
    update_place,
    get_place_for_guest,
    get_places_for_guest,
    get_current_user_places,
)
from app.users.models import UserModel

router = APIRouter(prefix="/places", tags=["places"])


@router.post(
    "",
    response_model=PlaceResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "One or more categories do not exist",
        },
    },
)
async def create_new_place(
    place_data: PlaceCreateRequestSchema,
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaceResponseSchema:
    try:
        place = await create_place(
            db=db,
            creator=current_user,
            place_data=place_data,
        )
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more categories do not exist",
        ) from error

    url = str(request.url_for("get_place", place_id=place.id))
    response.headers["Location"] = url

    return PlaceResponseSchema.model_validate(place).model_copy(update={"url": url})


@router.get(
    "",
    response_model=list[PlaceResponseSchema],
)
async def get_places(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> list[PlaceModel]:
    return await get_places_for_guest(db, page=page, page_size=page_size)


@router.get(
    "/me",
    response_model=list[PlaceResponseSchema],
)
async def get_places_me(
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> list[PlaceModel]:
    return await get_current_user_places(db, user, page, page_size)


@router.get(
    "/{place_id}",
    response_model=PlaceResponseSchema,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Place not found",
        },
    },
)
async def get_place(place_id: UUID, db: AsyncSession = Depends(get_db)) -> PlaceModel:
    place = await get_place_for_guest(db, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    return place


@router.patch(
    "/{place_id}",
    response_model=PlaceResponseSchema,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "One or more categories do not exist",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Place not found",
        },
    },
)
async def update_current_user_place(
    place_id: UUID,
    place_data: PlaceUpdateRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaceModel:
    place = await get_current_user_place(db, current_user, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    try:
        return await update_place(db, place, place_data)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more categories do not exist",
        ) from error


@router.delete(
    "/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Place not found",
        },
    },
)
async def delete_current_user_place(
    place_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    place = await get_current_user_place(db, current_user, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    await delete_place(db, place)
