import asyncio
import logging
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.storage.minio import delete_object, get_object_content, upload_object
from app.users.models import UserModel

logger = logging.getLogger(__name__)


class EmailAlreadyExistsError(Exception):
    pass


class EmptyAvatarError(Exception):
    pass


class AvatarTooLargeError(Exception):
    pass


class UnsupportedAvatarTypeError(Exception):
    pass


class StorageError(Exception):
    pass


def _build_avatar_key(avatar_object_id: UUID) -> str:
    return f"users/avatars/{avatar_object_id}"


def _detect_image_type(content: bytes) -> str | None:
    # Don't trust the client-supplied Content-Type: sniff magic bytes instead
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _read_avatar(file: UploadFile) -> tuple[bytes, str]:
    try:
        # Read at most limit + 1 bytes so oversized uploads aren't loaded into memory
        content = await file.read(settings.max_photo_size_bytes + 1)
    finally:
        await file.close()

    if not content:
        raise EmptyAvatarError

    if len(content) > settings.max_photo_size_bytes:
        raise AvatarTooLargeError

    content_type = _detect_image_type(content)

    if content_type is None or content_type not in settings.allowed_photo_content_types:
        raise UnsupportedAvatarTypeError

    return content, content_type


async def _email_taken(db: AsyncSession, email: str, user_id: UUID) -> bool:
    found = await db.scalar(
        select(UserModel.id).where(
            UserModel.email == email,
            UserModel.id != user_id,
        )
    )
    return found is not None


async def _delete_object_quietly(object_key: str) -> None:
    # Cleanup must never fail the request; an orphaned object is harmless
    try:
        await asyncio.to_thread(delete_object, object_key)
    except Exception:
        logger.warning("Failed to delete object %s", object_key, exc_info=True)


async def update_current_user(
    db: AsyncSession,
    user: UserModel,
    display_name: str | None,
    email: str | None,
    file: UploadFile | None,
) -> UserModel:
    # 1. Validate everything before touching storage
    avatar = await _read_avatar(file) if file is not None else None

    if email is not None:
        email = email.lower()
        if email != user.email and await _email_taken(db, email, user.id):
            raise EmailAlreadyExistsError

    # 2. Apply profile changes
    if display_name is not None:
        user.display_name = display_name

    if email is not None:
        user.email = email

    old_avatar_key: str | None = None
    new_avatar_key: str | None = None

    # 3. Upload the new avatar under a fresh id (old object stays intact for now)
    if avatar is not None:
        content, content_type = avatar
        new_avatar_id = uuid4()
        new_avatar_key = _build_avatar_key(new_avatar_id)

        if user.avatar_object_id is not None:
            old_avatar_key = _build_avatar_key(user.avatar_object_id)

        try:
            await asyncio.to_thread(
                upload_object, new_avatar_key, content, content_type
            )
        except Exception as error:
            await db.rollback()
            raise StorageError from error

        user.avatar_object_id = new_avatar_id
        user.avatar_content_type = content_type

    # 4. Commit; on failure remove the just-uploaded object
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        if new_avatar_key:
            await _delete_object_quietly(new_avatar_key)
        raise EmailAlreadyExistsError from error  # unique-email race
    except Exception:
        await db.rollback()
        if new_avatar_key:
            await _delete_object_quietly(new_avatar_key)
        raise

    # 5. Only after a successful commit remove the replaced avatar
    if old_avatar_key:
        await _delete_object_quietly(old_avatar_key)

    await db.refresh(user)

    return user


async def get_avatar_content(
    db: AsyncSession,
    avatar_object_id: UUID,
) -> tuple[bytes, str] | None:
    content_type = await db.scalar(
        select(UserModel.avatar_content_type).where(
            UserModel.avatar_object_id == avatar_object_id
        )
    )

    if content_type is None:
        return None

    try:
        content = await asyncio.to_thread(
            get_object_content, _build_avatar_key(avatar_object_id)
        )
    except Exception as error:
        raise StorageError from error

    return content, content_type
