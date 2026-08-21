from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.db_models import DeliveryTaskEntity, OrderEntity
from app.core.errors import ApiError
from app.core.security import ensure_utc, utc_now


@dataclass(frozen=True)
class DeliveryPromise:
    window_start_at: datetime
    window_end_at: datetime
    timezone_name: str
    source: str
    snapshot_at: datetime


@dataclass(frozen=True)
class DeliveryTimingResult:
    status: str
    late_by_minutes: int | None


class DeliveryTimingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def snapshot(
        self,
        *,
        service_date: date,
        window_start: str | None,
        window_end: str | None,
        source: str,
    ) -> DeliveryPromise | None:
        if not window_start and not window_end:
            if self.settings.delivery_promise_required:
                raise ApiError(
                    409,
                    "delivery_window_required",
                    "يجب تحديد نافذة توصيل قبل إنشاء الطلب.",
                )
            return None

        if not window_start or not window_end:
            raise ApiError(
                409,
                "delivery_window_incomplete",
                "نافذة التوصيل غير مكتملة.",
            )

        start_clock = self._clock(window_start)
        end_clock = self._clock(window_end)
        if start_clock >= end_clock:
            raise ApiError(
                409,
                "delivery_window_invalid",
                "وقت نهاية التوصيل يجب أن يكون بعد وقت البداية.",
            )

        zone = ZoneInfo(self.settings.delivery_promise_timezone)
        local_start = datetime.combine(
            service_date,
            start_clock,
            tzinfo=zone,
        )
        local_end = datetime.combine(
            service_date,
            end_clock,
            tzinfo=zone,
        )

        return DeliveryPromise(
            window_start_at=local_start.astimezone(timezone.utc),
            window_end_at=local_end.astimezone(timezone.utc),
            timezone_name=self.settings.delivery_promise_timezone,
            source=source,
            snapshot_at=utc_now(),
        )

    def apply(self, order: OrderEntity, promise: DeliveryPromise | None) -> None:
        if promise is None:
            return
        order.promised_delivery_window_start_at = promise.window_start_at
        order.promised_delivery_window_end_at = promise.window_end_at
        order.promised_delivery_timezone = promise.timezone_name
        order.delivery_promise_source = promise.source
        order.delivery_promise_snapshot_at = promise.snapshot_at

    def evaluate(
        self,
        *,
        order: OrderEntity,
        delivered_at: datetime,
    ) -> DeliveryTimingResult:
        deadline = order.promised_delivery_window_end_at
        if deadline is None:
            return DeliveryTimingResult(
                status="unmeasurable",
                late_by_minutes=None,
            )

        actual = ensure_utc(delivered_at)
        deadline_utc = ensure_utc(deadline)
        if actual <= deadline_utc:
            return DeliveryTimingResult(
                status="on_time",
                late_by_minutes=0,
            )

        late_seconds = (actual - deadline_utc).total_seconds()
        return DeliveryTimingResult(
            status="late",
            late_by_minutes=max(1, int((late_seconds + 59) // 60)),
        )

    def stamp_task(
        self,
        *,
        order: OrderEntity,
        task: DeliveryTaskEntity,
        delivered_at: datetime,
    ) -> DeliveryTimingResult:
        result = self.evaluate(
            order=order,
            delivered_at=delivered_at,
        )
        task.delivery_timing_status = result.status
        task.late_by_minutes = result.late_by_minutes
        return result

    @staticmethod
    def _clock(raw: str) -> time:
        try:
            return time.fromisoformat(raw)
        except ValueError as exc:
            raise ApiError(
                409,
                "delivery_window_invalid",
                "صيغة وقت التوصيل غير صحيحة.",
            ) from exc
