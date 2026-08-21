from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MediaUploadCreateRequest(BaseModel):
    purpose: str = Field(
        pattern=r"^(chef_avatar|dish_image|support_attachment|delivery_proof|customer_attachment|other)$"
    )
    visibility: str = Field(default="private", pattern=r"^(private|public)$")
    filename: str | None = Field(default=None, max_length=255)
    mime_type: str = Field(
        pattern=r"^(image/jpeg|image/png|image/webp|application/pdf)$"
    )
    size_bytes: int = Field(gt=0, le=50_000_000)


class MediaAssetResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    purpose: str
    visibility: str
    storage_provider: str
    original_filename: str | None
    mime_type: str
    expected_size_bytes: int
    actual_size_bytes: int | None
    checksum_sha256: str | None
    status: str
    upload_expires_at: datetime
    ready_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaUploadResponse(BaseModel):
    asset: MediaAssetResponse
    upload_url: str
    upload_headers: dict[str, str]
    expires_at: datetime


class MediaDownloadResponse(BaseModel):
    asset_id: UUID
    download_url: str
    expires_at: datetime


class MediaCompleteResponse(BaseModel):
    asset: MediaAssetResponse
