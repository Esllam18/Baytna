from __future__ import annotations

import argparse
import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def request_json(
    *,
    base_url: str,
    bearer: str,
    path: str,
) -> object:
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(
        req,
        timeout=30,
        context=ssl.create_default_context(),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--incident-id", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Pilot evidence must be collected from HTTPS.")

    order = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/orders/{args.order_id}",
    )
    order_summary = order["order"]
    delivery = order.get("delivery")

    failures: list[str] = []

    if order_summary.get("status") != "delivered":
        failures.append("order is not delivered")
    start = order_summary.get("promised_delivery_window_start_at")
    end = order_summary.get("promised_delivery_window_end_at")
    zone = order_summary.get("promised_delivery_timezone")
    if not start or not end or not zone:
        failures.append("immutable promised delivery window is missing")

    if not delivery or not delivery.get("delivered_at"):
        failures.append("delivery completion timestamp is missing")

    timing_status = delivery.get("delivery_timing_status") if delivery else None
    if timing_status not in {"on_time", "late"}:
        failures.append(
            f"delivery timing outcome is not measurable: {timing_status}"
        )

    expected_status = None
    expected_late_minutes = None
    if end and delivery and delivery.get("delivered_at"):
        deadline = parse_dt(end)
        delivered_at = parse_dt(delivery["delivered_at"])
        if delivered_at <= deadline:
            expected_status = "on_time"
            expected_late_minutes = 0
        else:
            expected_status = "late"
            late_seconds = (delivered_at - deadline).total_seconds()
            expected_late_minutes = max(
                1,
                int((late_seconds + 59) // 60),
            )

        if timing_status != expected_status:
            failures.append(
                f"stored timing status {timing_status} "
                f"does not match {expected_status}"
            )
        if (
            expected_status == "late"
            and int(delivery.get("late_by_minutes") or 0)
            != expected_late_minutes
        ):
            failures.append("late_by_minutes does not match timestamps")

    kpis = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=(
            "/api/v1/admin/control-room/kpis?"
            + urllib.parse.urlencode({"days": args.days})
        ),
    )

    if kpis.get("on_time_delivery_rate_pct") is None:
        failures.append("on-time KPI is not measurable")
    if float(kpis.get("delivery_promise_coverage_pct") or 0) < 100.0:
        failures.append(
            "delivery promise coverage is below 100% for the KPI sample"
        )

    incident_evidence = None
    if args.incident_id:
        incidents = request_json(
            base_url=args.api,
            bearer=args.admin_token,
            path="/api/v1/admin/control-room/incidents?limit=300",
        )
        incident_evidence = next(
            (
                item
                for item in incidents
                if item.get("id") == args.incident_id
            ),
            None,
        )
        if incident_evidence is None:
            failures.append("requested operations incident evidence not found")

        notifications = request_json(
            base_url=args.api,
            bearer=args.admin_token,
            path="/api/v1/customer/notifications?limit=100",
        )
        notification_found = any(
            item.get("kind") == "ops_incident"
            and str(item.get("data_json", {}).get("incident_id"))
            == args.incident_id
            for item in notifications
        )
        if not notification_found:
            failures.append(
                "admin ops notification for incident evidence was not found"
            )

    evidence = {
        "release": "0.50.0",
        "order_id": args.order_id,
        "promise": {
            "start_at": start,
            "end_at": end,
            "timezone": zone,
        },
        "delivery": {
            "delivered_at": delivery.get("delivered_at") if delivery else None,
            "timing_status": timing_status,
            "late_by_minutes": (
                delivery.get("late_by_minutes") if delivery else None
            ),
            "expected_status": expected_status,
            "expected_late_by_minutes": expected_late_minutes,
        },
        "kpis": {
            "days": kpis.get("days"),
            "on_time_delivery_rate_pct": (
                kpis.get("on_time_delivery_rate_pct")
            ),
            "on_time_measurable_deliveries": (
                kpis.get("on_time_measurable_deliveries")
            ),
            "late_deliveries": kpis.get("late_deliveries"),
            "delivery_promise_coverage_pct": (
                kpis.get("delivery_promise_coverage_pct")
            ),
            "launch_target_on_time_met": (
                kpis.get("launch_target_on_time_met")
            ),
        },
        "incident": incident_evidence,
        "verified": not failures,
        "failures": failures,
    }

    rendered = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
    )
    print(rendered)

    if args.output:
        Path(args.output).write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
