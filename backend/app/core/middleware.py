from __future__ import annotations

import re
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.modules.observability.metrics import metrics_registry


_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        if incoming and _SAFE_REQUEST_ID.fullmatch(incoming.strip()):
            request_id = incoming.strip()
        else:
            request_id = uuid4().hex
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = (
            self.settings.security_content_security_policy
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if self.settings.security_hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.settings.security_hsts_max_age_seconds}; "
                "includeSubDomains"
            )
        return response


class RequestBodyLimitMiddleware:
    def __init__(self, app, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = self.settings.max_request_body_bytes
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "request_body_too_large",
                                "message": "حجم الطلب أكبر من الحد المسموح.",
                                "details": {"max_bytes": max_bytes},
                            },
                            "request_id": "unknown",
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    # ASGI apps cannot cleanly replace a response after downstream
                    # processing has started, so raise before forwarding the chunk.
                    raise RequestBodyTooLarge(max_bytes)
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "request_body_too_large",
                        "message": "حجم الطلب أكبر من الحد المسموح.",
                        "details": {"max_bytes": max_bytes},
                    },
                    "request_id": "unknown",
                },
            )
            await response(scope, receive, send)


class RequestBodyTooLarge(Exception):
    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = max(0.0, time.perf_counter() - started)
            metrics_registry.observe(
                method=request.method,
                status_code=status_code,
                duration_seconds=elapsed,
            )
            if "response" in locals():
                response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.3f}"
