from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.db_models import (
    DeliveryTaskEntity,
    EconomicsCostEntryEntity,
    OrderEntity,
    OperationsIncidentEntity,
    PaymentEntity,
    PaymentReconciliationIssueEntity,
    PilotQaEvidenceEntity,
    ReviewEntity,
    UserEntity,
)
from app.core.security import utc_now
from tests.test_admin_operations import CHEF_ID, admin_headers


def _seed_eight_stable_weeks() -> tuple[date, date, list[UUID]]:
    today = utc_now().date()
    start = today - timedelta(days=56)
    end = today - timedelta(days=1)
    customers = [uuid4() for _ in range(5)]

    with SessionLocal() as db:
        for i, customer_id in enumerate(customers):
            db.add(
                UserEntity(
                    id=customer_id,
                    phone=f"01077{i}{uuid4().int % 1000000:06d}",
                    role="customer",
                    is_active=True,
                )
            )
        db.flush()

        # Three of five customers enter the pilot as repeat customers.
        prior_day = start - timedelta(days=10)
        for customer_id in customers[:3]:
            prior_dt = datetime.combine(
                prior_day,
                time(12, 0),
                tzinfo=timezone.utc,
            )
            db.add(
                OrderEntity(
                    customer_id=customer_id,
                    chef_id=CHEF_ID,
                    service_date=prior_day,
                    status="delivered",
                    subtotal_minor=15000,
                    delivery_fee_minor=0,
                    discount_minor=0,
                    total_minor=15000,
                    currency="EGP",
                    created_at=prior_dt,
                    updated_at=prior_dt,
                )
            )

        for week in range(8):
            order_day = start + timedelta(days=week * 7 + 1)
            created_at = datetime.combine(
                order_day,
                time(10, 0),
                tzinfo=timezone.utc,
            )
            promise_start = created_at + timedelta(hours=2)
            promise_end = created_at + timedelta(hours=4)
            delivered_at = created_at + timedelta(hours=3)

            for index, customer_id in enumerate(customers):
                total = 28000 + index * 1000
                order = OrderEntity(
                    customer_id=customer_id,
                    chef_id=CHEF_ID,
                    service_date=order_day,
                    status="delivered",
                    subtotal_minor=total,
                    delivery_fee_minor=0,
                    discount_minor=0,
                    total_minor=total,
                    currency="EGP",
                    promised_delivery_window_start_at=promise_start,
                    promised_delivery_window_end_at=promise_end,
                    promised_delivery_timezone="Africa/Cairo",
                    delivery_promise_source="test_pilot",
                    delivery_promise_snapshot_at=created_at,
                    created_at=created_at,
                    updated_at=created_at,
                )
                db.add(order)
                db.flush()

                db.add(
                    DeliveryTaskEntity(
                        order_id=order.id,
                        chef_id=CHEF_ID,
                        status="delivered",
                        delivered_at=delivered_at,
                        delivery_timing_status="on_time",
                        late_by_minutes=0,
                        created_at=created_at,
                        updated_at=delivered_at,
                    )
                )
                db.add(
                    ReviewEntity(
                        order_id=order.id,
                        customer_id=customer_id,
                        chef_id=CHEF_ID,
                        food_quality=5,
                        packaging=5,
                        order_accuracy=5,
                        value_for_money=5,
                        chef_overall=5,
                        delivery_overall=5,
                        comment="Stable pilot week",
                        created_at=delivered_at,
                        updated_at=delivered_at,
                    )
                )
                db.add(
                    PaymentEntity(
                        order_id=order.id,
                        customer_id=customer_id,
                        provider="mock",
                        provider_reference=f"pilot-{order.id}",
                        idempotency_key=f"pilot-payment-{order.id}",
                        amount_minor=total,
                        refunded_minor=0,
                        currency="EGP",
                        status="succeeded",
                        expires_at=created_at + timedelta(hours=1),
                        succeeded_at=created_at + timedelta(minutes=5),
                        created_at=created_at,
                        updated_at=created_at,
                    )
                )
        db.commit()
    return start, end, customers


def _create_program(client, start: date, end: date):
    headers, _ = admin_headers()
    response = client.post(
        "/api/v1/admin/pilot/programs",
        headers=headers,
        json={
            "name": "Sprint 45 Stability Pilot",
            "area": None,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "required_stability_weeks": 8,
            "rating_target": 4.7,
            "repeat_customer_target_pct": 40,
            "on_time_target_pct": 95,
            "cancellation_max_pct": 5,
            "notes": "Automated stability fixture",
        },
    )
    assert response.status_code == 201
    return headers, response.json()


def _seed_verified_economics(program_id: str) -> None:
    program_uuid = UUID(program_id)
    with SessionLocal() as db:
        program = db.get(__import__("app.core.db_models", fromlist=["PilotProgramEntity"]).PilotProgramEntity, program_uuid)
        orders = list(
            db.scalars(
                select(OrderEntity).where(
                    OrderEntity.created_at >= datetime.combine(
                        program.start_date, time.min, tzinfo=timezone.utc
                    ),
                    OrderEntity.created_at < datetime.combine(
                        program.end_date + timedelta(days=1),
                        time.min,
                        tzinfo=timezone.utc,
                    ),
                    OrderEntity.status == "delivered",
                )
            ).all()
        )
        for order in orders:
            for cost_type, amount in [
                ("chef_payout", 18000),
                ("delivery_partner", 3000),
                ("payment_processing", 600),
            ]:
                db.add(
                    EconomicsCostEntryEntity(
                        pilot_program_id=program_uuid,
                        order_id=order.id,
                        incurred_on=order.service_date,
                        cost_type=cost_type,
                        cost_scope="variable",
                        amount_minor=amount,
                        currency="EGP",
                        source="import",
                        external_reference=(
                            f"s45-econ-{order.id}-{cost_type}"
                        ),
                        is_verified=True,
                        verified_at=utc_now(),
                    )
                )
        db.add(
            EconomicsCostEntryEntity(
                pilot_program_id=program_uuid,
                incurred_on=program.end_date,
                cost_type="fixed_operations",
                cost_scope="fixed",
                amount_minor=100000,
                currency="EGP",
                source="import",
                external_reference=f"s45-fixed-{program_uuid}",
                is_verified=True,
                verified_at=utc_now(),
            )
        )
        db.commit()


def test_customer_cannot_access_pilot_stability(login):
    response = login["client"].get(
        "/api/v1/admin/pilot/programs",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_eight_complete_stable_weeks_pass_stability_gate(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)

    activated = client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/activate",
        headers=headers,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    report = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/stability",
        headers=headers,
    )
    assert report.status_code == 200
    body = report.json()
    assert body["complete_full_weeks"] == 8
    assert body["evaluable_weeks"] == 8
    assert body["passed_weeks"] == 8
    assert body["current_consecutive_passed_weeks"] == 8
    assert body["max_consecutive_passed_weeks"] == 8
    assert body["stability_gate_met"] is True
    assert len(body["weeks"]) == 8
    assert all(x["week_passed"] is True for x in body["weeks"])
    assert all(x["delivery_promise_coverage_pct"] == 100.0 for x in body["weeks"])
    assert all(x["on_time_delivery_rate_pct"] == 100.0 for x in body["weeks"])


def test_customer_cohorts_track_acquisition_and_retention(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)

    cohorts = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/cohorts",
        headers=headers,
        params={"weeks": 8},
    )
    assert cohorts.status_code == 200
    body = cohorts.json()
    # Three customers existed before the pilot; two were acquired in W1.
    assert body["acquired_customers"] == 2
    assert body["cohorts"][0]["cohort_week"] == 1
    assert body["cohorts"][0]["cohort_size"] == 2
    assert body["cohorts"][0]["retention"][0]["retention_pct"] == 100.0
    assert body["cohorts"][0]["retention"][1]["retention_pct"] == 100.0
    assert body["cohorts"][0]["retention"][4]["retention_pct"] == 100.0


def test_scale_readiness_requires_completed_pilot_backend_profit_qa_signoff(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)
    client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/activate",
        headers=headers,
    )

    before = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    )
    assert before.status_code == 200
    assert before.json()["stability_gate_met"] is True
    assert before.json()["scale_ready"] is False
    assert before.json()["profitability_calculated_from_backend"] is True
    assert before.json()["operational_profit_evidence_status"] == "backend_unevaluable"
    assert "pilot_program_not_completed" in before.json()["scale_blockers"]
    assert any(
        x.startswith("economics_")
        for x in before.json()["scale_blockers"]
    )

    _seed_verified_economics(program["id"])
    for evidence_type, reference in [
        ("pilot_qa_exit", "qa-report://sprint46-pilot-exit"),
        ("operations_signoff", "ops-signoff://pilot-owner-approved"),
    ]:
        result = client.put(
            f"/api/v1/admin/pilot/programs/{program['id']}/evidence/{evidence_type}",
            headers=headers,
            json={
                "status": "passed",
                "reference": reference,
                "notes": "Verified in Sprint 46 economics test",
            },
        )
        assert result.status_code == 200

    completed = client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/complete",
        headers=headers,
    )
    assert completed.status_code == 200

    after = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    )
    body = after.json()
    assert body["profitability_calculated_from_backend"] is True
    assert body["operational_profit_evidence_status"] == "backend_passed"
    assert body["qa_exit_evidence_status"] == "passed"
    assert body["operations_signoff_status"] == "passed"
    assert body["scale_ready"] is True
    assert body["scale_blockers"] == []



def test_passed_evidence_requires_reference(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)
    result = client.put(
        f"/api/v1/admin/pilot/programs/{program['id']}/evidence/pilot_qa_exit",
        headers=headers,
        json={"status": "passed", "reference": None},
    )
    assert result.status_code == 422


def test_evidence_update_creates_audit_record(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)
    result = client.put(
        f"/api/v1/admin/pilot/programs/{program['id']}/evidence/pilot_qa_exit",
        headers=headers,
        json={
            "status": "passed",
            "reference": "qa://verified",
        },
    )
    assert result.status_code == 200

    audit = client.get(
        "/api/v1/admin/audit",
        headers=headers,
        params={"action": "pilot.evidence.updated"},
    )
    assert audit.status_code == 200
    assert any(
        x["metadata_json"].get("program_id") == program["id"]
        for x in audit.json()
    )


def test_only_one_active_pilot_program_allowed(client):
    today = utc_now().date()
    headers, first = _create_program(
        client,
        today - timedelta(days=7),
        today + timedelta(days=30),
    )
    second_response = client.post(
        "/api/v1/admin/pilot/programs",
        headers=headers,
        json={
            "name": "Second Pilot",
            "area": None,
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
        },
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert client.post(
        f"/api/v1/admin/pilot/programs/{first['id']}/activate",
        headers=headers,
    ).status_code == 200
    conflict = client.post(
        f"/api/v1/admin/pilot/programs/{second['id']}/activate",
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "pilot_program_active_exists"


def test_worker_daily_pilot_snapshot_job_is_scheduled(client):
    from app.core.config import get_settings
    from app.modules.reliability.jobs import BackgroundJobService

    with SessionLocal() as db:
        jobs = BackgroundJobService(db, get_settings()).schedule_maintenance()
        assert len(jobs) == 13
        assert any(x.job_type == "pilot.snapshot" for x in jobs)


def test_scale_readiness_blocks_active_critical_incidents_and_reconciliation(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)
    client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/activate",
        headers=headers,
    )
    _seed_verified_economics(program["id"])
    for evidence_type in [
        "pilot_qa_exit",
        "operations_signoff",
    ]:
        assert client.put(
            f"/api/v1/admin/pilot/programs/{program['id']}/evidence/{evidence_type}",
            headers=headers,
            json={
                "status": "passed",
                "reference": f"test://{evidence_type}",
            },
        ).status_code == 200
    assert client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/complete",
        headers=headers,
    ).status_code == 200

    ready = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    )
    assert ready.json()["scale_ready"] is True

    with SessionLocal() as db:
        incident = OperationsIncidentEntity(
            fingerprint="sprint45:critical:blocker",
            category="reliability",
            severity="critical",
            status="open",
            source_type="worker",
            source_id="pilot-worker",
            title="Critical pilot blocker",
            message="Scale must stop while this is open.",
            details_json={},
        )
        db.add(incident)
        db.commit()
        incident_id = incident.id

    blocked = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    ).json()
    assert blocked["scale_ready"] is False
    assert blocked["active_critical_incidents"] == 1
    assert "active_critical_incidents_present" in blocked["scale_blockers"]

    with SessionLocal() as db:
        incident = db.get(OperationsIncidentEntity, incident_id)
        incident.status = "resolved"
        incident.resolved_at = utc_now()
        db.add(
            PaymentReconciliationIssueEntity(
                fingerprint="sprint45:reconciliation:blocker",
                issue_type="status_mismatch",
                status="open",
                expected_json={"status": "succeeded"},
                actual_json={"status": "pending"},
            )
        )
        db.commit()

    blocked = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    ).json()
    assert blocked["scale_ready"] is False
    assert blocked["open_payment_reconciliation_issues"] == 1
    assert "open_payment_reconciliation_issues_present" in blocked["scale_blockers"]
