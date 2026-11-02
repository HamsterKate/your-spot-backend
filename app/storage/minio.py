import io
from datetime import timedelta
from functools import lru_cache

from minio import Minio

from app.core.config import settings


@lru_cache
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio_client()

    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_object(
    object_key: str,
    content: bytes,
    content_type: str,
) -> None:
    client = get_minio_client()

    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_key,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )


def delete_object(object_key: str) -> None:
    client = get_minio_client()

    client.remove_object(
        bucket_name=settings.minio_bucket,
        object_name=object_key,
    )


def get_presigned_url(object_key: str) -> str:
    client = get_minio_client()

    return client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=object_key,
        expires=timedelta(minutes=15),
    )
