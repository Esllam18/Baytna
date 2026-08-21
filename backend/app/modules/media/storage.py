from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import boto3
import jwt

from app.core.config import Settings
from app.core.security import utc_now


@dataclass(slots=True)
class StorageObjectInfo:
    size_bytes: int
    checksum_sha256: str | None
    content_type: str | None


@dataclass(slots=True)
class SignedTransfer:
    url: str
    expires_at: object
    headers: dict[str, str]


class ObjectStorageProvider:
    name = "base"

    def create_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        raise NotImplementedError

    def head(self, *, object_key: str) -> StorageObjectInfo:
        raise NotImplementedError

    def create_download(
        self,
        *,
        object_key: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        raise NotImplementedError

    def delete(self, *, object_key: str) -> None:
        raise NotImplementedError


class LocalObjectStorageProvider(ObjectStorageProvider):
    name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = Path(settings.storage_local_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _token(self, *, object_key: str, op: str, ttl_seconds: int) -> str:
        now = utc_now()
        return jwt.encode(
            {
                "sub": object_key,
                "op": op,
                "iat": now,
                "exp": now + timedelta(seconds=ttl_seconds),
                "aud": "baytna-media",
            },
            self.settings.media_signing_secret,
            algorithm="HS256",
        )

    def decode_token(self, token: str, *, operation: str) -> str:
        payload = jwt.decode(
            token,
            self.settings.media_signing_secret,
            algorithms=["HS256"],
            audience="baytna-media",
        )
        if payload.get("op") != operation:
            raise ValueError("media token operation mismatch")
        object_key = payload.get("sub")
        if not object_key or ".." in object_key or object_key.startswith("/"):
            raise ValueError("invalid media object key")
        return object_key

    def path_for(self, object_key: str) -> Path:
        path = self.root / object_key
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        if resolved_root not in resolved_path.parents and resolved_path != resolved_root:
            raise ValueError("unsafe object path")
        return resolved_path

    def create_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        token = self._token(
            object_key=object_key,
            op="upload",
            ttl_seconds=ttl_seconds,
        )
        return SignedTransfer(
            url=f"/api/v1/media/local-upload/{token}",
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
            headers={"Content-Type": content_type},
        )

    def head(self, *, object_key: str) -> StorageObjectInfo:
        path = self.path_for(object_key)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(object_key)
        data = path.read_bytes()
        return StorageObjectInfo(
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            content_type=None,
        )

    def create_download(
        self,
        *,
        object_key: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        token = self._token(
            object_key=object_key,
            op="download",
            ttl_seconds=ttl_seconds,
        )
        return SignedTransfer(
            url=f"/api/v1/media/local-download/{token}",
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
            headers={},
        )

    def delete(self, *, object_key: str) -> None:
        path = self.path_for(object_key)
        if path.exists():
            path.unlink()


class S3ObjectStorageProvider(ObjectStorageProvider):
    name = "s3"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        kwargs = {
            "region_name": settings.storage_region or None,
        }
        if settings.storage_endpoint_url:
            kwargs["endpoint_url"] = settings.storage_endpoint_url
        if settings.storage_access_key_id:
            kwargs["aws_access_key_id"] = settings.storage_access_key_id
        if settings.storage_secret_access_key:
            kwargs["aws_secret_access_key"] = settings.storage_secret_access_key
        self.client = boto3.client("s3", **kwargs)

    def create_upload(
        self,
        *,
        object_key: str,
        content_type: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.settings.storage_bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl_seconds,
        )
        return SignedTransfer(
            url=url,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
            headers={"Content-Type": content_type},
        )

    def head(self, *, object_key: str) -> StorageObjectInfo:
        response = self.client.head_object(
            Bucket=self.settings.storage_bucket,
            Key=object_key,
        )
        checksum = response.get("ChecksumSHA256")
        return StorageObjectInfo(
            size_bytes=int(response["ContentLength"]),
            checksum_sha256=checksum,
            content_type=response.get("ContentType"),
        )

    def create_download(
        self,
        *,
        object_key: str,
        ttl_seconds: int,
    ) -> SignedTransfer:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.settings.storage_bucket,
                "Key": object_key,
            },
            ExpiresIn=ttl_seconds,
        )
        return SignedTransfer(
            url=url,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
            headers={},
        )

    def delete(self, *, object_key: str) -> None:
        self.client.delete_object(
            Bucket=self.settings.storage_bucket,
            Key=object_key,
        )


def build_storage_provider(settings: Settings) -> ObjectStorageProvider:
    provider = settings.storage_provider.strip().lower()
    if provider == "local":
        return LocalObjectStorageProvider(settings)
    if provider == "s3":
        if not settings.storage_bucket:
            raise ValueError("BAYTNA_STORAGE_BUCKET is required for s3 storage")
        return S3ObjectStorageProvider(settings)
    raise ValueError(f"Unsupported storage provider: {provider}")
