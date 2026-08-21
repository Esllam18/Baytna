from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.modules.observability.metrics import metrics_registry

router = APIRouter(tags=["observability"])


@router.get("/health/observability")
def observability_health() -> dict:
    snapshot = metrics_registry.snapshot()
    return {
        "status": "ok",
        "requests_total": snapshot["requests_total"],
        "errors_total": snapshot["errors_total"],
        "average_duration_ms": round(snapshot["average_duration_ms"], 3),
    }


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics() -> PlainTextResponse:
    settings = get_settings()
    if not settings.metrics_enabled:
        return PlainTextResponse("metrics_disabled\n", status_code=404)
    return PlainTextResponse(
        metrics_registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
