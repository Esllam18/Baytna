from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.modules.auth.schemas import (
    LogoutRequest,
    RefreshRequest,
    SendOtpRequest,
    SendOtpResponse,
    TokenResponse,
    VerifyOtpRequest,
)
from app.modules.auth.service import AuthService
from app.modules.security_hardening.service import SecurityService, client_ip

router = APIRouter(prefix="/auth", tags=["auth"])


def auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(db, settings)


@router.post("/send-otp", response_model=SendOtpResponse)
def send_otp(
    payload: SendOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SendOtpResponse:
    security = SecurityService(db, settings)
    security.enforce_auth_phone_and_ip(
        request=request,
        phone=payload.phone,
        operation="send_otp",
        ip_limit=settings.rate_limit_otp_send_ip,
        phone_limit=settings.rate_limit_otp_send_phone,
    )
    return AuthService(db, settings).send_otp(
        payload.phone,
        request.state.request_id,
    )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    security = SecurityService(db, settings)
    security.enforce_auth_phone_and_ip(
        request=request,
        phone=payload.phone,
        operation="verify_otp",
        ip_limit=settings.rate_limit_otp_verify_ip,
        phone_limit=settings.rate_limit_otp_verify_phone,
    )
    return AuthService(db, settings).verify_otp(
        payload.phone,
        payload.code,
        request.state.request_id,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    SecurityService(db, settings).enforce(
        request=request,
        scope="auth.refresh.ip",
        raw_key=client_ip(request, settings),
        limit=settings.rate_limit_refresh_ip,
    )
    return AuthService(db, settings).refresh(
        payload.refresh_token,
        request.state.request_id,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    request: Request,
    service: AuthService = Depends(auth_service),
) -> Response:
    service.logout(
        payload.refresh_token,
        request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
