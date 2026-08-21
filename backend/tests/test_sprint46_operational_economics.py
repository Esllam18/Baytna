from datetime import timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.db_models import (
    EconomicsCostEntryEntity,
    ExpansionAssessmentEntity,
    ExpansionZoneEntity,
    OrderEntity,
)
from app.core.security import utc_now
from tests.test_admin_operations import admin_headers
from tests.test_sprint45_pilot_stability import (
    _create_program,
    _seed_eight_stable_weeks,
    _seed_verified_economics,
)


def _completed_profitable_program(client):
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)
    assert client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/activate",
        headers=headers,
    ).status_code == 200

    _seed_verified_economics(program["id"])

    for evidence_type in ["pilot_qa_exit", "operations_signoff"]:
        response = client.put(
            f"/api/v1/admin/pilot/programs/{program['id']}/evidence/{evidence_type}",
            headers=headers,
            json={
                "status": "passed",
                "reference": f"sprint46://{evidence_type}",
            },
        )
        assert response.status_code == 200

    assert client.post(
        f"/api/v1/admin/pilot/programs/{program['id']}/complete",
        headers=headers,
    ).status_code == 200
    return headers, program


def test_customer_cannot_access_operational_economics(login):
    response = login["client"].get(
        "/api/v1/admin/economics/costs",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_cost_entry_requires_verification_before_profitability(login):
    client = login["client"]
    start, end, _ = _seed_eight_stable_weeks()
    headers, program = _create_program(client, start, end)

    with SessionLocal() as db:
        order = db.scalar(
            select(OrderEntity).where(
                OrderEntity.status == "delivered",
                OrderEntity.created_at >= utc_now() - timedelta(days=60),
            )
        )
        assert order is not None
        order_id = order.id
        incurred_on = order.service_date

    created = client.post(
        "/api/v1/admin/economics/costs",
        headers=headers,
        json={
            "pilot_program_id": program["id"],
            "order_id": str(order_id),
            "area": None,
            "incurred_on": incurred_on.isoformat(),
            "cost_type": "chef_payout",
            "amount_minor": 18000,
            "currency": "EGP",
            "source": "manual",
            "external_reference": "s46-cost-unverified-1",
            "note": "Actual chef settlement",
        },
    )
    assert created.status_code == 201
    assert created.json()["is_verified"] is False

    report = client.get(
        f"/api/v1/admin/economics/programs/{program['id']}/report",
        headers=headers,
    )
    assert report.status_code == 200
    assert report.json()["economics_evaluable"] is False
    assert "unverified_cost_entries_present" in report.json()["blockers"]

    verified = client.post(
        f"/api/v1/admin/economics/costs/{created.json()['id']}/verify",
        headers=headers,
    )
    assert verified.status_code == 200
    assert verified.json()["is_verified"] is True


def test_backend_contribution_margin_and_operational_profit_are_calculated(client):
    headers, program = _completed_profitable_program(client)

    report = client.get(
        f"/api/v1/admin/economics/programs/{program['id']}/report",
        headers=headers,
    )
    assert report.status_code == 200
    body = report.json()

    assert body["delivered_orders"] == 40
    assert body["revenue_coverage_pct"] == 100.0
    assert body["cost_coverage_pct"] == 100.0
    assert body["unverified_cost_entries"] == 0
    assert body["economics_evaluable"] is True
    assert body["operational_profit_positive"] is True
    assert body["contribution_minor"] > 0
    assert body["operational_profit_minor"] > 0
    assert body["contribution_margin_pct"] is not None
    assert body["contribution_per_delivered_order_minor"] is not None
    breakdown = {
        x["cost_type"]: x["amount_minor"]
        for x in body["cost_breakdown"]
    }
    assert breakdown["chef_payout"] == 40 * 18000
    assert breakdown["delivery_partner"] == 40 * 3000
    assert breakdown["payment_processing"] == 40 * 600
    assert breakdown["fixed_operations"] == 100000


def test_post_pilot_profitability_is_backend_source_of_truth(client):
    headers, program = _completed_profitable_program(client)

    result = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    )
    assert result.status_code == 200
    body = result.json()
    assert body["profitability_calculated_from_backend"] is True
    assert body["operational_profit_evidence_status"] == "backend_passed"
    assert body["scale_ready"] is True

    # A new verified fixed cost can make the backend profitability gate fail;
    # no manual "profit positive" evidence can override the ledger.
    with SessionLocal() as db:
        p = UUID(program["id"])
        db.add(
            EconomicsCostEntryEntity(
                pilot_program_id=p,
                incurred_on=utc_now().date() - timedelta(days=1),
                cost_type="fixed_operations",
                cost_scope="fixed",
                amount_minor=1000000,
                currency="EGP",
                source="import",
                external_reference="s46-loss-shock",
                is_verified=True,
                verified_at=utc_now(),
            )
        )
        db.commit()

    blocked = client.get(
        f"/api/v1/admin/pilot/programs/{program['id']}/post-pilot",
        headers=headers,
    ).json()
    assert blocked["profitability_calculated_from_backend"] is True
    assert blocked["operational_profit_evidence_status"] == "backend_failed"
    assert blocked["scale_ready"] is False
    assert "backend_operational_profit_not_positive" in blocked["scale_blockers"]


def test_expansion_zone_assessment_approval_launch_and_pause(client):
    headers, program = _completed_profitable_program(client)

    created = client.post(
        "/api/v1/admin/economics/zones",
        headers=headers,
        json={
            "area": "الشيخ زايد",
            "source_program_id": program["id"],
            "min_delivered_orders": 40,
            "min_contribution_margin_pct": 5,
            "min_operational_profit_minor": 1,
            "notes": "Sprint 46 expansion readiness fixture",
        },
    )
    assert created.status_code == 201
    zone = created.json()
    assert zone["status"] == "candidate"

    assessed = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/assess",
        headers=headers,
    )
    assert assessed.status_code == 200
    assessment = assessed.json()
    assert assessment["decision"] == "ready"
    assert assessment["economics_evaluable"] is True
    assert assessment["stability_gate_met"] is True
    assert assessment["post_pilot_scale_ready"] is True
    assert assessment["blockers_json"] == []

    detail = client.get(
        f"/api/v1/admin/economics/zones/{zone['id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["zone"]["status"] == "ready"

    approved = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    launched = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/launch",
        headers=headers,
    )
    assert launched.status_code == 200
    assert launched.json()["status"] == "live"

    paused = client.post(
        f"/api/v1/admin/economics/zones/{zone['id']}/pause",
        headers=headers,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    audit = client.get(
        "/api/v1/admin/audit",
        headers=headers,
        params={"entity_type": "expansion_zone"},
    )
    assert audit.status_code == 200
    actions = {x["action"] for x in audit.json()}
    assert "expansion.zone.assessed" in actions
    assert "expansion.zone.approved" in actions
    assert "expansion.zone.launched" in actions
    assert "expansion.zone.paused" in actions


def test_expansion_zone_blocks_when_margin_target_is_not_met(client):
    headers, program = _completed_profitable_program(client)

    created = client.post(
        "/api/v1/admin/economics/zones",
        headers=headers,
        json={
            "area": "التجمع الخامس",
            "source_program_id": program["id"],
            "min_delivered_orders": 40,
            "min_contribution_margin_pct": 95,
            "min_operational_profit_minor": 1,
        },
    )
    assert created.status_code == 201

    assessed = client.post(
        f"/api/v1/admin/economics/zones/{created.json()['id']}/assess",
        headers=headers,
    )
    assert assessed.status_code == 200
    body = assessed.json()
    assert body["decision"] == "blocked"
    assert "contribution_margin_below_zone_target" in body["blockers_json"]

    approve = client.post(
        f"/api/v1/admin/economics/zones/{created.json()['id']}/approve",
        headers=headers,
    )
    assert approve.status_code == 409


def test_expansion_assessment_is_durable(client):
    headers, program = _completed_profitable_program(client)
    created = client.post(
        "/api/v1/admin/economics/zones",
        headers=headers,
        json={
            "area": "بدر",
            "source_program_id": program["id"],
            "min_delivered_orders": 40,
            "min_contribution_margin_pct": 5,
            "min_operational_profit_minor": 1,
        },
    )
    zone_id = UUID(created.json()["id"])

    assert client.post(
        f"/api/v1/admin/economics/zones/{zone_id}/assess",
        headers=headers,
    ).status_code == 200

    with SessionLocal() as db:
        zone = db.get(ExpansionZoneEntity, zone_id)
        assessment = db.scalar(
            select(ExpansionAssessmentEntity).where(
                ExpansionAssessmentEntity.zone_id == zone_id
            )
        )
        assert zone is not None
        assert assessment is not None
        assert assessment.decision == "ready"
        assert assessment.economics_evaluable is True
