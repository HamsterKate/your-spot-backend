from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.users.models import UserModel
from app.users.schemas import DisplayName, UserResponseSchema
from app.users.services import (
    AvatarTooLargeError,
    EmailAlreadyExistsError,
    EmptyAvatarError,
    StorageError,
    UnsupportedAvatarTypeError,
    update_current_user,
    get_avatar_content,
)

router = APIRouter(prefix="/users", tags=["users"])


def build_user_response(user: UserModel, request: Request) -> UserResponseSchema:
    avatar_url = None

    if user.avatar_object_id is not None:
        avatar_url = str(request.url_for("get_avatar", avatar_id=user.avatar_object_id))

    return UserResponseSchema.model_validate(user).model_copy(
        update={"avatar_url": avatar_url}
    )


@router.get("/me", response_model=UserResponseSchema)
async def get_me(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
) -> UserResponseSchema:
    return build_user_response(current_user, request)


@router.patch(
    "/me",
    response_model=UserResponseSchema,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid avatar"},
        status.HTTP_409_CONFLICT: {"description": "Email already in use"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "Avatar too large"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Storage unavailable"},
    },
)
async def update_me(
    request: Request,
    display_name: Annotated[DisplayName | None, Form()] = None,
    email: Annotated[EmailStr | None, Form()] = None,
    file: UploadFile | None = File(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    try:
        user = await update_current_user(
            db=db,
            user=current_user,
            display_name=display_name,
            email=email,
            file=file,
        )
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use",
        ) from error
    except EmptyAvatarError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file cannot be empty",
        ) from error
    except UnsupportedAvatarTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are supported",
        ) from error
    except AvatarTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Avatar size must not exceed 5 MB",
        ) from error
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Avatar storage is temporarily unavailable",
        ) from error

    return build_user_response(user, request)


@router.get(
    "/avatars/{avatar_id}",
    name="get_avatar",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Avatar not found"}},
)
async def get_avatar(
    avatar_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        avatar = await get_avatar_content(db, avatar_id)
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Avatar storage is temporarily unavailable",
        ) from error

    if avatar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found",
        )

    content, content_type = avatar

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
