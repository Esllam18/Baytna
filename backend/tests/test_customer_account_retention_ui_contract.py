from uuid import UUID

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.notifications.service import NotificationService


def test_sprint36_customer_profile_get_and_update(login):
    client = login["client"]

    first = client.get(
        "/api/v1/customer/profile",
        headers=login["headers"],
    )
    assert first.status_code == 200
    assert set(first.json()) >= {
        "id",
        "phone",
        "display_name",
        "preferred_language",
        "role",
        "is_active",
        "created_at",
    }

    updated = client.patch(
        "/api/v1/customer/profile",
        headers=login["headers"],
        json={
            "display_name": "محمد خالد",
            "preferred_language": "ar",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "محمد خالد"
    assert updated.json()["phone"] == "+201000000000"


def test_sprint36_address_update_default_and_delete(login):
    client = login["client"]

    a1 = client.post(
        "/api/v1/customer/addresses",
        headers=login["headers"],
        json={
            "label": "البيت",
            "area": "6 أكتوبر",
            "street": "المحور",
            "is_default": True,
        },
    ).json()
    a2 = client.post(
        "/api/v1/customer/addresses",
        headers=login["headers"],
        json={
            "label": "الشغل",
            "area": "الشيخ زايد",
            "street": "البستان",
            "is_default": False,
        },
    ).json()

    edited = client.patch(
        f"/api/v1/customer/addresses/{a2['id']}",
        headers=login["headers"],
        json={
            "label": "المكتب",
            "area": "الشيخ زايد",
            "street": "البستان 2",
            "building": "7",
            "floor": "2",
            "apartment": "5",
            "latitude": None,
            "longitude": None,
            "is_default": False,
        },
    )
    assert edited.status_code == 200
    assert edited.json()["label"] == "المكتب"

    defaulted = client.post(
        f"/api/v1/customer/addresses/{a2['id']}/default",
        headers=login["headers"],
    )
    assert defaulted.status_code == 200
    assert defaulted.json()["is_default"] is True

    listed = client.get(
        "/api/v1/customer/addresses",
        headers=login["headers"],
    ).json()
    assert next(x for x in listed if x["id"] == a1["id"])["is_default"] is False

    deleted = client.delete(
        f"/api/v1/customer/addresses/{a2['id']}",
        headers=login["headers"],
    )
    assert deleted.status_code == 204

    listed_after = client.get(
        "/api/v1/customer/addresses",
        headers=login["headers"],
    ).json()
    assert len(listed_after) == 1
    assert listed_after[0]["id"] == a1["id"]
    assert listed_after[0]["is_default"] is True


def test_sprint36_address_isolation(login):
    client = login["client"]
    address = client.post(
        "/api/v1/customer/addresses",
        headers=login["headers"],
        json={"label": "البيت", "area": "6 أكتوبر"},
    ).json()

    sent = client.post("/api/v1/auth/send-otp", json={"phone": "01011111111"})
    otp = sent.json()["development_otp"]
    second = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01011111111", "code": otp},
    ).json()
    headers = {"Authorization": f"Bearer {second['access_token']}"}

    assert client.post(
        f"/api/v1/customer/addresses/{address['id']}/default",
        headers=headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/customer/addresses/{address['id']}",
        headers=headers,
    ).status_code == 404


def test_sprint36_favorites_ui_contract(login):
    client = login["client"]
    chef = client.get("/api/v1/chefs").json()[0]
    dishes = client.get(
        f"/api/v1/chefs/{chef['id']}/signature-menu"
    ).json()
    dish = dishes[0]

    favorite_chef = client.put(
        f"/api/v1/customer/favorites/chefs/{chef['id']}",
        headers=login["headers"],
    )
    assert favorite_chef.status_code == 200
    assert set(favorite_chef.json()) >= {
        "favorite_id",
        "chef_id",
        "display_name",
        "specialty",
        "area",
        "rating",
        "is_verified",
        "is_open_today",
    }

    favorite_dish = client.put(
        f"/api/v1/customer/favorites/dishes/{dish['id']}",
        headers=login["headers"],
    )
    assert favorite_dish.status_code == 200
    assert set(favorite_dish.json()) >= {
        "favorite_id",
        "dish_id",
        "chef_id",
        "name",
        "category",
        "base_price_minor",
        "image_url",
        "is_active",
    }

    summary = client.get(
        "/api/v1/customer/favorites/summary",
        headers=login["headers"],
    )
    assert summary.status_code == 200
    assert summary.json() == {"chefs_count": 1, "dishes_count": 1}


def test_sprint36_notifications_list_summary_and_read(login):
    user_id = UUID(login["body"]["user"]["id"])
    with SessionLocal() as db:
        NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="support_reply",
            title="رد جديد",
            body="فريق بيتنا رد على طلب الدعم.",
            action_url="/account/support",
            data_json={"source": "test"},
            dedupe_key="sprint36-notification-1",
            commit=True,
        )

    client = login["client"]
    summary = client.get(
        "/api/v1/customer/notifications/summary",
        headers=login["headers"],
    )
    assert summary.status_code == 200
    assert summary.json()["unread_count"] == 1

    rows = client.get(
        "/api/v1/customer/notifications",
        headers=login["headers"],
    )
    assert rows.status_code == 200
    item = rows.json()[0]
    assert set(item) >= {
        "id",
        "kind",
        "title",
        "body",
        "action_url",
        "data_json",
        "read_at",
        "created_at",
    }

    read = client.post(
        f"/api/v1/customer/notifications/{item['id']}/read",
        headers=login["headers"],
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None


def test_sprint36_notification_preferences_contract(login):
    client = login["client"]
    prefs = client.get(
        "/api/v1/customer/notifications/preferences",
        headers=login["headers"],
    )
    assert prefs.status_code == 200
    assert set(prefs.json()) >= {
        "user_id",
        "push_enabled",
        "sms_enabled",
        "order_updates",
        "support_updates",
        "marketing_enabled",
    }

    updated = client.put(
        "/api/v1/customer/notifications/preferences",
        headers=login["headers"],
        json={
            "push_enabled": True,
            "sms_enabled": True,
            "order_updates": True,
            "support_updates": True,
            "marketing_enabled": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["sms_enabled"] is True


def test_sprint36_loyalty_history_contract(login):
    response = login["client"].get(
        "/api/v1/customer/loyalty",
        headers=login["headers"],
    )
    assert response.status_code == 200
    assert set(response.json()) >= {
        "customer_id",
        "balance_points",
        "lifetime_earned_points",
        "lifetime_redeemed_points",
        "transactions",
    }


def test_sprint36_support_create_reply_and_detail(login):
    client = login["client"]

    created = client.post(
        "/api/v1/customer/support/tickets",
        headers=login["headers"],
        json={
            "order_id": None,
            "category": "app_issue",
            "subject": "مشكلة في التطبيق",
            "description": "الشاشة لا تحدث البيانات بعد الضغط.",
            "priority": "normal",
            "attachment_ids": [],
        },
    )
    assert created.status_code == 201
    ticket = created.json()
    assert set(ticket) >= {
        "id",
        "customer_id",
        "category",
        "subject",
        "description",
        "priority",
        "status",
        "messages",
    }

    reply = client.post(
        f"/api/v1/customer/support/tickets/{ticket['id']}/messages",
        headers=login["headers"],
        json={"body": "تفاصيل إضافية للمشكلة", "attachment_ids": []},
    )
    assert reply.status_code == 200
    assert any(
        msg["body"] == "تفاصيل إضافية للمشكلة"
        for msg in reply.json()["messages"]
    )

    detail = client.get(
        f"/api/v1/customer/support/tickets/{ticket['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == ticket["id"]


def test_sprint36_subscription_visibility_contract(login):
    client = login["client"]

    plans = client.get(
        "/api/v1/customer/subscriptions/plans",
        headers=login["headers"],
    )
    assert plans.status_code == 200
    assert isinstance(plans.json(), list)

    current = client.get(
        "/api/v1/customer/subscriptions/current",
        headers=login["headers"],
    )
    assert current.status_code == 200
