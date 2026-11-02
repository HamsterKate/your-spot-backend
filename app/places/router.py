from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
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
    PlacePhotoLimitExceededError,
    StorageError,
    create_place_photo,
    delete_place_photo,
    get_place_photo,
    get_place_photo_content as get_photo_content,
    get_place_photos,
)
from app.users.models import UserModel
from app.places.models import PlaceModel, PlacePhotoModel
from app.places.schemas import (
    PlaceCreateRequestSchema,
    PlacePhotoResponseSchema,
    PlaceResponseSchema,
    PlaceUpdateRequestSchema,
)

router = APIRouter(prefix="/places", tags=["places"])


ALLOWED_PHOTO_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024


def build_photo_response(
    photo: PlacePhotoModel,
    request: Request,
) -> PlacePhotoResponseSchema:
    url = str(
        request.url_for(
            "get_place_photo_content",
            place_id=photo.place_id,
            photo_id=photo.id,
        )
    )

    return PlacePhotoResponseSchema.model_validate(photo).model_copy(
        update={"url": url}
    )


def build_place_response(
    place: PlaceModel,
    request: Request,
) -> PlaceResponseSchema:
    photos = [build_photo_response(photo, request) for photo in place.photos]

    return PlaceResponseSchema.model_validate(place).model_copy(
        update={"photos": photos}
    )


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

    return build_place_response(place, request).model_copy(update={"url": url})


@router.get(
    "",
    response_model=list[PlaceResponseSchema],
)
async def get_places(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=100),
    category_id: UUID | None = Query(None),
    tag_ids: list[UUID] | None = Query(None, alias="tag_id"),
) -> list[PlaceResponseSchema]:
    places = await get_places_for_guest(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        tag_ids=tag_ids,
    )

    return [build_place_response(place, request) for place in places]


@router.get(
    "/me",
    response_model=list[PlaceResponseSchema],
)
async def get_places_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[PlaceResponseSchema]:
    places = await get_current_user_places(db, user, page, page_size)

    return [build_place_response(place, request) for place in places]


@router.post(
    "/{place_id}/photos",
    response_model=PlacePhotoResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_place_photo(
    place_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlacePhotoResponseSchema:
    place = await get_current_user_place(db, current_user, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    if file.content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are supported",
        )

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo file cannot be empty",
        )

    if len(content) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Photo size must not exceed 5 MB",
        )

    name = (file.filename or "photo").replace("\\", "/").rsplit("/", 1)[-1]

    if len(name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo name must contain no more than 100 characters",
        )

    try:
        photo = await create_place_photo(
            db=db,
            place=place,
            user=current_user,
            name=name,
            content=content,
            content_type=file.content_type,
        )
    except PlacePhotoLimitExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A place can contain no more than 10 photos",
        ) from error
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Photo storage is temporarily unavailable",
        ) from error

    return build_photo_response(photo, request)


@router.get(
    "/{place_id}/photos",
    response_model=list[PlacePhotoResponseSchema],
)
async def get_place_photos_list(
    place_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[PlacePhotoResponseSchema]:
    place = await get_place_for_guest(db, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    photos = await get_place_photos(db, place.id)

    return [build_photo_response(photo, request) for photo in photos]


@router.get(
    "/{place_id}/photos/{photo_id}/content",
    name="get_place_photo_content",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Photo not found",
        },
    },
)
async def get_place_photo_content(
    place_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    photo = await get_place_photo(db, place_id, photo_id)

    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    try:
        content = await get_photo_content(photo)
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Photo storage is temporarily unavailable",
        ) from error

    return Response(
        content=content,
        media_type=photo.content_type,
    )


@router.delete(
    "/{place_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_current_user_place_photo(
    place_id: UUID,
    photo_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    place = await get_current_user_place(db, current_user, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    photo = await get_place_photo(db, place_id, photo_id)

    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    try:
        await delete_place_photo(db, photo)
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Photo storage is temporarily unavailable",
        ) from error


@router.get(
    "/{place_id}",
    response_model=PlaceResponseSchema,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Place not found",
        },
    },
)
async def get_place(
    place_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlaceResponseSchema:
    place = await get_place_for_guest(db, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    return build_place_response(place, request)


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
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaceResponseSchema:
    place = await get_current_user_place(db, current_user, place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    try:
        updated_place = await update_place(db, place, place_data)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more categories do not exist",
        ) from error

    return build_place_response(updated_place, request)


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
