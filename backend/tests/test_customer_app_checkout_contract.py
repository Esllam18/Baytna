from datetime import date, timedelta


CHEF_PHONE = "+201000000001"


def login_phone(client, phone: str):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]
    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": phone, "code": otp},
    )
    assert verified.status_code == 200
    body = verified.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}}


def prepare_cart(login, *, day_offset: int = 70):
    client = login["client"]
    chef = login_phone(client, CHEF_PHONE)
    service_date = (date.today() + timedelta(days=day_offset)).isoformat()

    opened = client.post(
        "/api/v1/chef/workdays/open",
        headers=chef["headers"],
        json={"service_date": service_date},
    )
    assert opened.status_code == 200

    signature = client.get(
        "/api/v1/chef/signature-menu",
        headers=chef["headers"],
    )
    assert signature.status_code == 200
    dish_id = signature.json()[0]["id"]

    menu = client.put(
        "/api/v1/chef/today-menu",
        headers=chef["headers"],
        json={
            "service_date": service_date,
            "items": [
                {
                    "dish_id": dish_id,
                    "quantity_total": 10,
                    "max_per_order": 5,
                }
            ],
        },
    )
    assert menu.status_code == 200
    menu_item = menu.json()["items"][0]

    cart = client.post(
        "/api/v1/customer/cart/items",
        headers=login["headers"],
        json={"daily_menu_item_id": menu_item["id"], "quantity": 2},
    )
    assert cart.status_code == 201
    return cart.json()


def test_sprint35_cart_ui_contract(login):
    cart = prepare_cart(login, day_offset=70)
    assert set(cart) >= {
        "id",
        "chef_id",
        "service_date",
        "status",
        "subtotal_minor",
        "currency",
        "items",
    }
    line = cart["items"][0]
    assert set(line) >= {
        "id",
        "daily_menu_item_id",
        "dish_id",
        "dish_name",
        "chef_id",
        "unit_price_minor",
        "quantity",
        "line_total_minor",
        "max_per_order",
        "availability_label",
    }


def test_sprint35_cart_update_and_remove_contract(login):
    client = login["client"]
    cart = prepare_cart(login, day_offset=71)
    item_id = cart["items"][0]["id"]

    updated = client.patch(
        f"/api/v1/customer/cart/items/{item_id}",
        headers=login["headers"],
        json={"quantity": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["quantity"] == 3

    removed = client.delete(
        f"/api/v1/customer/cart/items/{item_id}",
        headers=login["headers"],
    )
    assert removed.status_code == 200
    assert removed.json()["items"] == []


def test_sprint35_pricing_quote_ui_contract(login):
    client = login["client"]
    cart = prepare_cart(login, day_offset=72)
    quote = client.post(
        "/api/v1/customer/pricing/quote",
        headers=login["headers"],
        json={
            "cart_id": cart["id"],
            "coupon_code": None,
            "loyalty_points_to_redeem": 0,
        },
    )
    assert quote.status_code == 200
    body = quote.json()
    assert set(body) >= {
        "cart_id",
        "subtotal_minor",
        "delivery_fee_minor",
        "coupon_discount_minor",
        "subscription_discount_minor",
        "loyalty_discount_minor",
        "total_discount_minor",
        "total_minor",
        "currency",
        "loyalty_balance_points",
    }
    assert body["total_minor"] >= body["minimum_payable_minor"]


def test_sprint35_address_checkout_contract(login):
    client = login["client"]
    created = client.post(
        "/api/v1/customer/addresses",
        headers=login["headers"],
        json={
            "label": "البيت",
            "area": "6 أكتوبر",
            "street": "المحور المركزي",
            "building": "12",
            "apartment": "4",
            "is_default": True,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert set(body) >= {
        "id",
        "label",
        "area",
        "street",
        "building",
        "floor",
        "apartment",
        "is_default",
    }
    listed = client.get(
        "/api/v1/customer/addresses",
        headers=login["headers"],
    )
    assert listed.status_code == 200
    assert any(x["id"] == body["id"] for x in listed.json())


def test_sprint35_order_payment_and_tracking_contract(login):
    client = login["client"]
    cart = prepare_cart(login, day_offset=73)

    address = client.post(
        "/api/v1/customer/addresses",
        headers=login["headers"],
        json={"label": "البيت", "area": "6 أكتوبر", "is_default": True},
    ).json()

    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"], "loyalty_points_to_redeem": 0},
    )
    assert order.status_code == 201
    order_body = order.json()
    assert set(order_body) >= {
        "id",
        "status",
        "subtotal_minor",
        "delivery_fee_minor",
        "discount_minor",
        "total_minor",
        "items",
        "timeline",
        "pricing_adjustments",
    }

    set_address = client.put(
        f"/api/v1/customer/orders/{order_body['id']}/delivery-address",
        headers=login["headers"],
        json={"address_id": address["id"]},
    )
    assert set_address.status_code == 200

    payment = client.post(
        f"/api/v1/customer/orders/{order_body['id']}/payment-intent",
        headers=login["headers"],
        json={"idempotency_key": "sprint35-payment-contract-001"},
    )
    assert payment.status_code == 201
    payment_body = payment.json()
    assert set(payment_body) >= {
        "id",
        "order_id",
        "provider",
        "provider_reference",
        "provider_status",
        "amount_minor",
        "status",
        "checkout_url",
        "expires_at",
    }
    assert payment_body["order_id"] == order_body["id"]

    tracking = client.get(
        f"/api/v1/customer/orders/{order_body['id']}/tracking",
        headers=login["headers"],
    )
    assert tracking.status_code == 200
    assert set(tracking.json()) >= {
        "order_id",
        "status",
        "fulfillment_stage",
        "display_status",
        "detail",
        "estimated_ready_at",
        "updated_at",
    }


def test_sprint35_delivery_tracking_before_dispatch_has_null_mission(login):
    client = login["client"]
    cart = prepare_cart(login, day_offset=74)
    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={"cart_id": cart["id"]},
    ).json()

    response = client.get(
        f"/api/v1/customer/orders/{order['id']}/delivery-tracking",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mission_status"] is None
    assert body["order_status"] == order["status"]
