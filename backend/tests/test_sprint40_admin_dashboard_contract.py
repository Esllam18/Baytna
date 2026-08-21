from app.core.database import SessionLocal
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.core.security import create_access_token
from app.core.config import get_settings
from uuid import uuid4


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        user = UserEntity(
            id=uuid4(),
            phone=f"+20109{uuid4().int % 100000000:08d}",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        token, _ = create_access_token(
            user_id=user.id,
            role=UserRole.ADMIN,
            settings=settings,
        )
        return {
            "Authorization": f"Bearer {token}"
        }, user


def test_admin_profile_contract(client):
    headers, user = admin_headers()
    response = client.get("/api/v1/admin/profile", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "phone": user.phone,
        "role": "admin",
        "is_active": True,
    }


def test_customer_cannot_access_admin_profile(login):
    response = login["client"].get(
        "/api/v1/admin/profile",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_sprint40_admin_frontend_required_paths(client):
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]

    expected = {
        "/api/v1/admin/profile": {"get"},
        "/api/v1/admin/dashboard/overview": {"get"},
        "/api/v1/admin/orders": {"get"},
        "/api/v1/admin/orders/{order_id}": {"get"},
        "/api/v1/admin/orders/{order_id}/notes": {"get", "post"},
        "/api/v1/admin/orders/{order_id}/refunds": {"get", "post"},
        "/api/v1/admin/chefs": {"get"},
        "/api/v1/admin/chefs/{chef_id}": {"get"},
        "/api/v1/admin/chefs/{chef_id}/status": {"patch"},
        "/api/v1/admin/drivers": {"get"},
        "/api/v1/admin/drivers/{driver_id}": {"get"},
        "/api/v1/admin/support/workload-summary": {"get"},
        "/api/v1/admin/support/tickets": {"get"},
        "/api/v1/admin/support/tickets/{ticket_id}": {"get"},
        "/api/v1/admin/support/tickets/{ticket_id}/assign": {"post"},
        "/api/v1/admin/support/tickets/{ticket_id}/messages": {"post"},
        "/api/v1/admin/support/tickets/{ticket_id}/status": {"patch"},
        "/api/v1/admin/finance/summary": {"get"},
        "/api/v1/admin/analytics/daily": {"get"},
        "/api/v1/admin/analytics/funnel": {"get"},
        "/api/v1/admin/analytics/retention": {"get"},
        "/api/v1/admin/audit": {"get"},
    }

    for path, methods in expected.items():
        assert path in paths
        actual = {
            method
            for method in paths[path]
            if method in {"get", "post", "put", "patch", "delete"}
        }
        assert methods.issubset(actual)
