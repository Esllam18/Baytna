from datetime import date, timedelta
from uuid import UUID

from app.core.database import SessionLocal
from app.core.db_models import (
    DeliveryTaskEntity,
    OrderEntity,
    ReviewEntity,
)


def test_review_eligibility_before_delivery(login):
    client = login["client"]

    response = client.get(
        "/api/v1/customer/orders/00000000-0000-0000-0000-000000000001/review-eligibility",
        headers=login["headers"],
    )
    assert response.status_code == 404


def test_review_eligibility_delivered_without_review(login):
    from tests.test_post_order import create_delivered_order

    client = login["client"]
    service_date = (date.today() + timedelta(days=120)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    response = client.get(
        f"/api/v1/customer/orders/{order['id']}/review-eligibility",
        headers=login["headers"],
    )
    assert response.status_code == 200
    assert response.json() == {
        "order_id": order["id"],
        "order_status": "delivered",
        "can_review": True,
        "reason": "ready_for_review",
        "review": None,
    }


def test_review_eligibility_returns_existing_review(login):
    from tests.test_post_order import create_delivered_order, review_payload

    client = login["client"]
    service_date = (date.today() + timedelta(days=121)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(chef_overall=4),
    )
    assert created.status_code == 201

    response = client.get(
        f"/api/v1/customer/orders/{order['id']}/review-eligibility",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["can_review"] is True
    assert body["reason"] == "review_exists"
    assert body["review"]["id"] == created.json()["id"]
    assert body["review"]["chef_overall"] == 4


def test_review_eligibility_is_customer_isolated(client):
    from tests.test_post_order import create_delivered_order, login_phone

    first = login_phone(client, "01037111111")
    second = login_phone(client, "01037222222")
    service_date = (date.today() + timedelta(days=122)).isoformat()
    order, _ = create_delivered_order(client, first, service_date)

    response = client.get(
        f"/api/v1/customer/orders/{order['id']}/review-eligibility",
        headers=second["headers"],
    )
    assert response.status_code == 404


def test_public_review_does_not_expose_customer_or_order_identity(login):
    from tests.test_post_order import create_delivered_order, review_payload

    client = login["client"]
    service_date = (date.today() + timedelta(days=123)).isoformat()
    order, _ = create_delivered_order(client, login, service_date)

    created = client.post(
        f"/api/v1/customer/orders/{order['id']}/review",
        headers=login["headers"],
        json=review_payload(),
    )
    assert created.status_code == 201

    public = client.get(
        f"/api/v1/chefs/{order['chef_id']}/reviews"
    )
    assert public.status_code == 200
    review = next(x for x in public.json() if x["id"] == created.json()["id"])

    assert "customer_id" not in review
    assert "order_id" not in review
    assert "driver_id" not in review
    assert "is_visible" not in review
    assert set(review) == {
        "id",
        "food_quality",
        "packaging",
        "order_accuracy",
        "value_for_money",
        "chef_overall",
        "comment",
        "created_at",
    }


def test_special_order_customer_api_contract_paths_exist(client):
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]

    expected = {
        "/api/v1/chefs/{chef_id}/availability": {"get"},
        "/api/v1/customer/special-orders": {"get", "post"},
        "/api/v1/customer/special-orders/{special_order_id}": {"get"},
        "/api/v1/customer/special-orders/{special_order_id}/accept-counter-offer": {"post"},
        "/api/v1/customer/special-orders/{special_order_id}/cancel": {"post"},
        "/api/v1/customer/special-orders/{special_order_id}/checkout": {"post"},
    }

    for path, methods in expected.items():
        assert path in paths
        assert methods.issubset(
            {
                method
                for method in paths[path]
                if method in {"get", "post", "put", "patch", "delete"}
            }
        )
