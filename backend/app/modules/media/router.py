from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.errors import ApiError
from app.modules.media.schemas import (
    MediaAssetResponse,
    MediaCompleteResponse,
    MediaDownloadResponse,
    MediaUploadCreateRequest,
    MediaUploadResponse,
)
from app.modules.media.service import MediaService
from app.modules.media.storage import LocalObjectStorageProvider, build_storage_provider

router = APIRouter(tags=["media"])


@router.post(
    "/media/uploads",
    response_model=MediaUploadResponse,
    status_code=201,
)
def create_upload(
    payload: MediaUploadCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MediaUploadResponse:
    return MediaService(db, settings).create_upload(
        owner_user_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/media/{asset_id}/complete",
    response_model=MediaCompleteResponse,
)
def complete_upload(
    asset_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MediaCompleteResponse:
    return MediaService(db, settings).complete(
        actor=user,
        asset_id=asset_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/media",
    response_model=list[MediaAssetResponse],
)
def list_media(
    status: str | None = None,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[MediaAssetResponse]:
    return MediaService(db, settings).list_owned(
        owner_user_id=user.id,
        status=status,
    )


@router.get(
    "/media/{asset_id}/download-url",
    response_model=MediaDownloadResponse,
)
def download_url(
    asset_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MediaDownloadResponse:
    return MediaService(db, settings).download(
        actor=user,
        asset_id=asset_id,
    )


@router.get(
    "/media/public/{asset_id}",
    response_model=MediaDownloadResponse,
)
def public_download_url(
    asset_id: UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MediaDownloadResponse:
    return MediaService(db, settings).public_download(asset_id=asset_id)


@router.delete("/media/{asset_id}", status_code=204)
def delete_media(
    asset_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    MediaService(db, settings).delete(
        actor=user,
        asset_id=asset_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/media/local-upload/{token}", include_in_schema=False)
async def local_upload(
    token: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    provider = build_storage_provider(settings)
    if not isinstance(provider, LocalObjectStorageProvider):
        raise ApiError(404, "media_local_route_disabled", "المسار غير متاح.")

    try:
        object_key = provider.decode_token(token, operation="upload")
    except Exception:
        raise ApiError(403, "media_token_invalid", "رابط رفع الملف غير صالح.")

    body = await request.body()
    if not body:
        raise ApiError(422, "media_empty_file", "الملف فارغ.")
    if len(body) > settings.media_max_upload_bytes:
        raise ApiError(413, "media_too_large", "حجم الملف أكبر من الحد المسموح.")

    path = provider.path_for(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {"uploaded": True, "size_bytes": len(body)}


@router.get("/media/local-download/{token}", include_in_schema=False)
def local_download(
    token: str,
    settings: Settings = Depends(get_settings),
):
    provider = build_storage_provider(settings)
    if not isinstance(provider, LocalObjectStorageProvider):
        raise ApiError(404, "media_local_route_disabled", "المسار غير متاح.")

    try:
        object_key = provider.decode_token(token, operation="download")
        path = provider.path_for(object_key)
    except Exception:
        raise ApiError(403, "media_token_invalid", "رابط تحميل الملف غير صالح.")

    if not path.exists():
        raise ApiError(404, "media_object_missing", "الملف غير موجود.")
    return FastAPIResponse(content=path.read_bytes())
