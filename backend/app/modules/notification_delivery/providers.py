from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from uuid import uuid4

from app.core.config import Settings

logger = logging.getLogger("baytna.notifications.external")


@dataclass(slots=True)
class ProviderResult:
    provider_message_id: str
    provider_status: str = "accepted"


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        permanent: bool = False,
        deactivate_target: bool = False,
    ) -> None:
        self.code = code
        self.permanent = permanent
        self.deactivate_target = deactivate_target
        super().__init__(message)


class PushProvider:
    name = "base"

    def send(
        self,
        *,
        token: str,
        title: str,
        body: str,
        data: dict,
    ) -> ProviderResult:
        raise NotImplementedError

    def probe(self) -> dict:
        return {"provider": self.name, "status": "configured"}


class SmsProvider:
    name = "base"

    def send(
        self,
        *,
        phone: str,
        body: str,
    ) -> ProviderResult:
        raise NotImplementedError

    def probe(self) -> dict:
        return {"provider": self.name, "status": "configured"}


class LoggingPushProvider(PushProvider):
    name = "logging"

    def send(self, *, token: str, title: str, body: str, data: dict) -> ProviderResult:
        message_id = f"log-push-{uuid4().hex}"
        logger.info(
            "push_notification %s",
            json.dumps(
                {
                    "message_id": message_id,
                    "token_hash_hint": token[-6:] if len(token) >= 6 else "***",
                    "title": title,
                    "body": body,
                    "data": data,
                },
                ensure_ascii=False,
            ),
        )
        return ProviderResult(
            provider_message_id=message_id,
            provider_status="accepted",
        )


class LoggingSmsProvider(SmsProvider):
    name = "logging"

    def send(self, *, phone: str, body: str) -> ProviderResult:
        message_id = f"log-sms-{uuid4().hex}"
        logger.info(
            "sms_notification %s",
            json.dumps(
                {
                    "message_id": message_id,
                    "phone_hint": phone[-4:],
                    "body": body,
                },
                ensure_ascii=False,
            ),
        )
        return ProviderResult(
            provider_message_id=message_id,
            provider_status="accepted",
        )


class HttpPushProvider(PushProvider):
    name = "http"

    def __init__(self, settings: Settings) -> None:
        self.endpoint = settings.notification_push_endpoint
        self.token = settings.notification_push_bearer_token
        if not self.endpoint:
            raise ValueError("BAYTNA_NOTIFICATION_PUSH_ENDPOINT is required")

    def send(self, *, token: str, title: str, body: str, data: dict) -> ProviderResult:
        payload = json.dumps(
            {
                "token": token,
                "title": title,
                "body": body,
                "data": data,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8") or "{}"
            parsed = json.loads(response_body)
            message_id = (
                parsed.get("message_id")
                or parsed.get("id")
                or f"http-push-{uuid4().hex}"
            )
            return ProviderResult(provider_message_id=str(message_id))


class HttpSmsProvider(SmsProvider):
    name = "http"

    def __init__(self, settings: Settings) -> None:
        self.endpoint = settings.notification_sms_endpoint
        self.token = settings.notification_sms_bearer_token
        if not self.endpoint:
            raise ValueError("BAYTNA_NOTIFICATION_SMS_ENDPOINT is required")

    def send(self, *, phone: str, body: str) -> ProviderResult:
        payload = json.dumps({"to": phone, "body": body}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8") or "{}"
            parsed = json.loads(response_body)
            message_id = (
                parsed.get("message_id")
                or parsed.get("id")
                or f"http-sms-{uuid4().hex}"
            )
            return ProviderResult(provider_message_id=str(message_id))


class FCMPushProvider(PushProvider):
    """Firebase Cloud Messaging HTTP v1 provider.

    Uses Google Application Default Credentials unless
    BAYTNA_FCM_CREDENTIALS_FILE is supplied.
    """

    name = "fcm"
    scope = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.project_id = settings.fcm_project_id.strip()
        if not self.project_id:
            raise ValueError("BAYTNA_FCM_PROJECT_ID is required for FCM")
        self.endpoint = (
            "https://fcm.googleapis.com/v1/projects/"
            f"{self.project_id}/messages:send"
        )

    def _access_token(self) -> str:
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2 import service_account
            import google.auth
        except Exception as exc:
            raise RuntimeError(
                "google-auth is required for FCM provider"
            ) from exc

        if self.settings.fcm_credentials_file.strip():
            credentials = service_account.Credentials.from_service_account_file(
                self.settings.fcm_credentials_file,
                scopes=[self.scope],
            )
        else:
            credentials, detected_project = google.auth.default(
                scopes=[self.scope]
            )
            if not self.project_id and detected_project:
                self.project_id = detected_project

        credentials.refresh(GoogleRequest())
        if not credentials.token:
            raise RuntimeError("FCM OAuth token refresh returned no token")
        return str(credentials.token)

    def send(self, *, token: str, title: str, body: str, data: dict) -> ProviderResult:
        access_token = self._access_token()
        string_data = {
            str(key): (
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            )
            for key, value in (data or {}).items()
        }
        payload = {
            "validate_only": bool(self.settings.fcm_validate_only),
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": string_data,
            },
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                parsed = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_error = json.loads(raw)
            except Exception:
                parsed_error = {}
            error = parsed_error.get("error") or {}
            status = str(error.get("status") or f"HTTP_{exc.code}")
            detail_codes: list[str] = []
            for detail in error.get("details") or []:
                if isinstance(detail, dict) and detail.get("errorCode"):
                    detail_codes.append(str(detail["errorCode"]))
            code = detail_codes[0] if detail_codes else status

            token_invalid = code in {
                "UNREGISTERED",
                "SENDER_ID_MISMATCH",
            }
            permanent = token_invalid or code in {
                "INVALID_ARGUMENT",
                "THIRD_PARTY_AUTH_ERROR",
            }
            raise ProviderError(
                error.get("message") or f"FCM request failed: {status}",
                code=f"FCM_{code}",
                permanent=permanent,
                deactivate_target=token_invalid,
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"FCM transport failure: {exc}",
                code="FCM_TRANSPORT",
                permanent=False,
            ) from exc

        message_id = parsed.get("name")
        if not message_id:
            raise ProviderError(
                "FCM success response did not contain a message name",
                code="FCM_RESPONSE_INVALID",
                permanent=False,
            )
        return ProviderResult(
            provider_message_id=str(message_id),
            provider_status="accepted",
        )

    def probe(self) -> dict:
        token = self._access_token()
        return {
            "provider": self.name,
            "status": "ok",
            "project_id": self.project_id,
            "oauth_token_present": bool(token),
        }


class TwilioSmsProvider(SmsProvider):
    name = "twilio"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.account_sid = settings.twilio_account_sid.strip()
        self.auth_token = settings.twilio_auth_token.strip()
        self.from_number = settings.twilio_from_number.strip()
        self.messaging_service_sid = settings.twilio_messaging_service_sid.strip()
        self.status_callback_url = settings.twilio_status_callback_url.strip()
        self.api_base = settings.twilio_api_base_url.rstrip("/")

        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio account SID/auth token are required")
        if not self.from_number and not self.messaging_service_sid:
            raise ValueError(
                "Twilio requires a From number or Messaging Service SID"
            )

    def _authorization_header(self) -> str:
        raw = f"{self.account_sid}:{self.auth_token}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _message_endpoint(self) -> str:
        return (
            f"{self.api_base}/Accounts/"
            f"{urllib.parse.quote(self.account_sid)}/Messages.json"
        )

    def send(self, *, phone: str, body: str) -> ProviderResult:
        params = {
            "To": phone,
            "Body": body,
        }
        if self.messaging_service_sid:
            params["MessagingServiceSid"] = self.messaging_service_sid
        else:
            params["From"] = self.from_number
        if self.status_callback_url:
            params["StatusCallback"] = self.status_callback_url

        request = urllib.request.Request(
            self._message_endpoint(),
            data=urllib.parse.urlencode(params).encode("utf-8"),
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                parsed = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error = json.loads(raw)
            except Exception:
                error = {}
            code = str(error.get("code") or f"HTTP_{exc.code}")
            permanent = exc.code not in {408, 409, 425, 429} and exc.code < 500
            raise ProviderError(
                error.get("message") or f"Twilio request failed: HTTP {exc.code}",
                code=f"TWILIO_{code}",
                permanent=permanent,
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"Twilio transport failure: {exc}",
                code="TWILIO_TRANSPORT",
                permanent=False,
            ) from exc

        sid = parsed.get("sid")
        if not sid:
            raise ProviderError(
                "Twilio success response did not contain a message SID",
                code="TWILIO_RESPONSE_INVALID",
                permanent=False,
            )
        return ProviderResult(
            provider_message_id=str(sid),
            provider_status=str(parsed.get("status") or "accepted"),
        )

    def probe(self) -> dict:
        endpoint = (
            f"{self.api_base}/Accounts/"
            f"{urllib.parse.quote(self.account_sid)}.json"
        )
        request = urllib.request.Request(
            endpoint,
            headers={"Authorization": self._authorization_header()},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                parsed = json.loads(response.read().decode("utf-8") or "{}")
        except Exception as exc:
            raise RuntimeError(f"Twilio credential probe failed: {exc}") from exc
        return {
            "provider": self.name,
            "status": "ok",
            "account_sid": parsed.get("sid") or self.account_sid,
        }


class DisabledPushProvider(PushProvider):
    name = "disabled"

    def send(self, **kwargs):
        raise RuntimeError("push provider disabled")


class DisabledSmsProvider(SmsProvider):
    name = "disabled"

    def send(self, **kwargs):
        raise RuntimeError("sms provider disabled")


def build_push_provider(settings: Settings) -> PushProvider:
    name = settings.notification_push_provider.strip().lower()
    if name == "logging":
        return LoggingPushProvider()
    if name == "http":
        return HttpPushProvider(settings)
    if name == "fcm":
        return FCMPushProvider(settings)
    if name == "disabled":
        return DisabledPushProvider()
    raise ValueError(f"Unsupported push provider: {name}")


def build_sms_provider(settings: Settings) -> SmsProvider:
    name = settings.notification_sms_provider.strip().lower()
    if name == "logging":
        return LoggingSmsProvider()
    if name == "http":
        return HttpSmsProvider(settings)
    if name == "twilio":
        return TwilioSmsProvider(settings)
    if name == "disabled":
        return DisabledSmsProvider()
    raise ValueError(f"Unsupported sms provider: {name}")
