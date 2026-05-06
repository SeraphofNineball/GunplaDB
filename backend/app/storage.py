import io
from minio import Minio
from minio.error import S3Error

from app.config import settings

_client: Minio | None = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def upload_bytes(data: bytes, object_path: str, content_type: str = "application/octet-stream") -> str:
    client = get_minio()
    client.put_object(
        settings.minio_bucket,
        object_path,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_path


def get_presigned_url(object_path: str, expires_hours: int = 24) -> str:
    from datetime import timedelta
    client = get_minio()
    return client.presigned_get_object(
        settings.minio_bucket,
        object_path,
        expires=timedelta(hours=expires_hours),
    )


def get_public_url(object_path: str) -> str:
    # Served through Nginx proxy at /gunpladb/<path>
    return f"/{settings.minio_bucket}/{object_path}"


def delete_object(object_path: str):
    client = get_minio()
    try:
        client.remove_object(settings.minio_bucket, object_path)
    except S3Error:
        pass


def object_exists(object_path: str) -> bool:
    client = get_minio()
    try:
        client.stat_object(settings.minio_bucket, object_path)
        return True
    except S3Error:
        return False
