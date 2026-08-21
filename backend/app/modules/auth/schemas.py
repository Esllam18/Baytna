from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.models import PublicUser


def normalize_phone_value(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+"):
        cleaned = "+20" + cleaned.lstrip("0")
    if len(cleaned) < 10:
        raise ValueError("رقم الهاتف غير صالح")
    return cleaned


class SendOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_phone_value(value)


class SendOtpResponse(BaseModel):
    challenge_expires_at: datetime
    development_otp: str | None = None


class VerifyOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_phone_value(value)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user: PublicUser
