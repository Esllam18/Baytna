from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import MediaAssetEntity, UserEntity
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.media.schemas import (
    MediaAssetResponse,
    MediaCompleteResponse,
    MediaDownloadResponse,
    MediaUploadCreateRequest,
    MediaUploadResponse,
)
from app.modules.media.storage import ObjectStorageProvider, build_storage_provider


EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

PUBLIC_PURPOSES = {"chef_avatar", "dish_image"}


class MediaService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = build_storage_provider(settings)
        self.audit = AuditRepository(db)

    def create_upload(
        self,
        *,
        owner_user_id: UUID,
        payload: MediaUploadCreateRequest,
        request_id: str | None,
    ) -> MediaUploadResponse:
        if payload.size_bytes > self.settings.media_max_upload_bytes:
            raise ApiError(
                413,
                "media_too_large",
                "حجم الملف أكبر من الحد المسموح.",
                {"max_bytes": self.settings.media_max_upload_bytes},
            )

        if payload.visibility == "public" and payload.purpose not in PUBLIC_PURPOSES:
            raise ApiError(
                422,
                "media_public_purpose_not_allowed",
                "هذا النوع من الملفات يجب أن يظل خاصًا.",
            )

        extension = EXTENSIONS[payload.mime_type]
        asset_id = uuid4()
        object_key = (
            f"{owner_user_id}/{payload.purpose}/"
            f"{asset_id.hex}{extension}"
        )
        signed = self.storage.create_upload(
            object_key=object_key,
            content_type=payload.mime_type,
            ttl_seconds=self.settings.media_upload_ttl_seconds,
        )

        row = MediaAssetEntity(
            id=asset_id,
            owner_user_id=owner_user_id,
            purpose=payload.purpose,
            visibility=payload.visibility,
            storage_provider=self.storage.name,
            object_key=object_key,
            original_filename=payload.filename,
            mime_type=payload.mime_type,
            expected_size_bytes=payload.size_bytes,
            status="pending",
            upload_expires_at=signed.expires_at,
        )
        self.db.add(row)
        self.audit.add(
            action="media.upload.created",
            actor_user_id=owner_user_id,
            entity_type="media_asset",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "purpose": row.purpose,
                "mime_type": row.mime_type,
                "expected_size_bytes": row.expected_size_bytes,
            },
        )
        self.db.commit()
        self.db.refresh(row)

        return MediaUploadResponse(
            asset=MediaAssetResponse.model_validate(row),
            upload_url=signed.url,
            upload_headers=signed.headers,
            expires_at=signed.expires_at,
        )

    def complete(
        self,
        *,
        actor: UserEntity,
        asset_id: UUID,
        request_id: str | None,
    ) -> MediaCompleteResponse:
        row = self._authorized_asset(actor=actor, asset_id=asset_id)

        if row.status == "ready":
            return MediaCompleteResponse(
                asset=MediaAssetResponse.model_validate(row)
            )
        if row.status in {"deleted", "failed"}:
            raise ApiError(
                409,
                "media_not_completable",
                "لا يمكن إكمال الملف من حالته الحالية.",
            )
        if ensure_utc(row.upload_expires_at) <= utc_now():
            row.status = "failed"
            self.db.commit()
            raise ApiError(
                409,
                "media_upload_expired",
                "انتهت صلاحية رابط رفع الملف.",
            )

        try:
            info = self.storage.head(object_key=row.object_key)
        except FileNotFoundError:
            raise ApiError(
                409,
                "media_object_missing",
                "لم يتم العثور على الملف في التخزين.",
            )

        if info.size_bytes != row.expected_size_bytes:
            row.status = "failed"
            row.actual_size_bytes = info.size_bytes
            self.db.commit()
            raise ApiError(
                409,
                "media_size_mismatch",
                "حجم الملف المرفوع لا يطابق الحجم المتوقع.",
                {
                    "expected": row.expected_size_bytes,
                    "actual": info.size_bytes,
                },
            )

        if info.size_bytes > self.settings.media_max_upload_bytes:
            row.status = "failed"
            self.db.commit()
            raise ApiError(
                413,
                "media_too_large",
                "حجم الملف أكبر من الحد المسموح.",
            )

        row.actual_size_bytes = info.size_bytes
        row.checksum_sha256 = info.checksum_sha256
        row.status = "ready"
        row.ready_at = utc_now()

        self.audit.add(
            action="media.upload.completed",
            actor_user_id=actor.id,
            entity_type="media_asset",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"checksum_sha256": row.checksum_sha256},
        )
        self.db.commit()
        self.db.refresh(row)
        return MediaCompleteResponse(
            asset=MediaAssetResponse.model_validate(row)
        )

    def list_owned(
        self,
        *,
        owner_user_id: UUID,
        status: str | None = None,
    ) -> list[MediaAssetResponse]:
        stmt = select(MediaAssetEntity).where(
            MediaAssetEntity.owner_user_id == owner_user_id
        )
        if status:
            stmt = stmt.where(MediaAssetEntity.status == status)
        stmt = stmt.order_by(MediaAssetEntity.created_at.desc())
        return [
            MediaAssetResponse.model_validate(x)
            for x in self.db.scalars(stmt).all()
        ]

    def download(
        self,
        *,
        actor: UserEntity,
        asset_id: UUID,
    ) -> MediaDownloadResponse:
        row = self._authorized_asset(actor=actor, asset_id=asset_id)
        if row.status != "ready":
            raise ApiError(409, "media_not_ready", "الملف غير جاهز للتحميل.")

        signed = self.storage.create_download(
            object_key=row.object_key,
            ttl_seconds=self.settings.media_download_ttl_seconds,
        )
        return MediaDownloadResponse(
            asset_id=row.id,
            download_url=signed.url,
            expires_at=signed.expires_at,
        )

    def public_download(self, *, asset_id: UUID) -> MediaDownloadResponse:
        row = self.db.get(MediaAssetEntity, asset_id)
        if row is None or row.status != "ready" or row.visibility != "public":
            raise ApiError(404, "media_not_found", "الملف غير موجود.")
        signed = self.storage.create_download(
            object_key=row.object_key,
            ttl_seconds=self.settings.media_download_ttl_seconds,
        )
        return MediaDownloadResponse(
            asset_id=row.id,
            download_url=signed.url,
            expires_at=signed.expires_at,
        )

    def delete(
        self,
        *,
        actor: UserEntity,
        asset_id: UUID,
        request_id: str | None,
    ) -> None:
        row = self._authorized_asset(actor=actor, asset_id=asset_id)
        if row.status == "deleted":
            return

        self.storage.delete(object_key=row.object_key)
        row.status = "deleted"
        row.deleted_at = utc_now()
        self.audit.add(
            action="media.deleted",
            actor_user_id=actor.id,
            entity_type="media_asset",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()

    def _authorized_asset(
        self,
        *,
        actor: UserEntity,
        asset_id: UUID,
    ) -> MediaAssetEntity:
        row = self.db.get(MediaAssetEntity, asset_id)
        if row is None:
            raise ApiError(404, "media_not_found", "الملف غير موجود.")
        if actor.role != "admin" and row.owner_user_id != actor.id:
            raise ApiError(404, "media_not_found", "الملف غير موجود.")
        return row
