import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    CouponEntity,
    CouponRedemptionEntity,
    LoyaltyAccountEntity,
    LoyaltyRedemptionEntity,
    LoyaltyTransactionEntity,
    OrderPricingAdjustmentEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.payments.security import sign_webhook

CHEF_ID = "10000000-0000-0000-0000-000000000001"
CHEF_PHONE = "+201000000001"
DRIVER_PHONE = "+201090000001"


def login_phone(client, phone: str):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]
    verified = client.post("/api/v1/auth/verify-otp", json={"phone": phone, "code": otp})
    assert verified.status_code == 200
    body = verified.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}, "body": body}


def create_admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        admin = UserEntity(id=uuid4(), phone=f"+20108{uuid4().int % 100000000:08d}", role="admin", is_active=True)
        db.add(admin); db.commit(); db.refresh(admin)
        token, _ = create_access_token(user_id=admin.id, role=UserRole.ADMIN, settings=settings)
        return {"headers": {"Authorization": f"Bearer {token}"}, "id": admin.id}


def webhook(client, body: dict):
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook(raw, get_settings().payment_webhook_secret)
    return client.post("/api/v1/payments/webhooks/mock", content=raw, headers={"Content-Type": "application/json", "X-Baytna-Signature": signature})


def prepare_cart(client, customer, service_date: str, quantity=2):
    chef = login_phone(client, CHEF_PHONE)
    opened = client.post("/api/v1/chef/workdays/open", headers=chef["headers"], json={"service_date": service_date})
    assert opened.status_code == 200
    signature = client.get("/api/v1/chef/signature-menu", headers=chef["headers"]).json()
    today = client.put("/api/v1/chef/today-menu", headers=chef["headers"], json={"service_date": service_date, "items": [{"dish_id": signature[0]["id"], "quantity_total": 20, "max_per_order": 10}]}).json()
    cart = client.post("/api/v1/customer/cart/items", headers=customer["headers"], json={"daily_menu_item_id": today["items"][0]["id"], "quantity": quantity})
    assert cart.status_code == 201
    return chef, signature[0], cart.json()


def create_coupon(client, admin, code="SAVE10", discount_type="fixed", discount_value=1000, **extra):
    payload = {
        "code": code,
        "name": code,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_subtotal_minor": extra.get("min_subtotal_minor", 0),
        "max_discount_minor": extra.get("max_discount_minor"),
        "total_usage_limit": extra.get("total_usage_limit"),
        "per_customer_usage_limit": extra.get("per_customer_usage_limit", 1),
        "stack_with_subscription": extra.get("stack_with_subscription", True),
        "is_active": True,
    }
    r = client.post("/api/v1/admin/pricing/coupons", headers=admin["headers"], json=payload)
    assert r.status_code == 201
    return r.json()


def create_plan_and_grant(client, admin, customer_id, *, code="PLUS", discount_bps=1000, multiplier_bps=15000):
    plan = client.post("/api/v1/admin/pricing/subscription-plans", headers=admin["headers"], json={
        "code": code,
        "name": "Baytna Plus",
        "price_minor": 9900,
        "duration_days": 30,
        "order_discount_bps": discount_bps,
        "max_order_discount_minor": 5000,
        "loyalty_multiplier_bps": multiplier_bps,
    })
    assert plan.status_code == 201
    plan = plan.json()
    grant = client.post(f"/api/v1/admin/pricing/subscription-plans/{plan['id']}/grant", headers=admin["headers"], json={"customer_id": customer_id, "source": "promo"})
    assert grant.status_code == 201
    return plan, grant.json()


def set_loyalty_balance(customer_id: str, points: int):
    with SessionLocal() as db:
        uid = UUID(customer_id)
        row = db.get(LoyaltyAccountEntity, uid)
        if row is None:
            row = LoyaltyAccountEntity(customer_id=uid, balance_points=points, lifetime_earned_points=points)
            db.add(row)
        else:
            row.balance_points = points
            row.lifetime_earned_points = max(row.lifetime_earned_points, points)
        db.commit()


def test_fixed_coupon_quote_and_order_pricing_snapshot(login):
    client=login["client"]; admin=create_admin_headers(); service_date=(date.today()+timedelta(days=100)).isoformat()
    _, _, cart=prepare_cart(client, login, service_date)
    create_coupon(client, admin, code="FIX10", discount_value=1000)
    quote=client.post("/api/v1/customer/pricing/quote", headers=login["headers"], json={"cart_id":cart["id"],"coupon_code":"fix10"})
    assert quote.status_code==200
    q=quote.json(); assert q["coupon_discount_minor"]==1000; assert q["total_minor"]==q["subtotal_minor"]-1000
    order=client.post("/api/v1/customer/orders", headers=login["headers"], json={"cart_id":cart["id"],"coupon_code":"FIX10"})
    assert order.status_code==201
    body=order.json(); assert body["discount_minor"]==1000; assert body["total_minor"]==q["total_minor"]
    assert any(x["adjustment_type"]=="coupon" and x["reference_code"]=="FIX10" for x in body["pricing_adjustments"])


def test_percent_coupon_respects_max_discount(login):
    client=login["client"]; admin=create_admin_headers(); service_date=(date.today()+timedelta(days=101)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    create_coupon(client,admin,code="PCT50",discount_type="percent",discount_value=5000,max_discount_minor=1200)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"PCT50"})
    assert q.status_code==200; assert q.json()["coupon_discount_minor"]==1200


def test_coupon_minimum_subtotal_is_enforced(login):
    client=login["client"]; admin=create_admin_headers(); service_date=(date.today()+timedelta(days=102)).isoformat(); _,_,cart=prepare_cart(client,login,service_date,quantity=1)
    create_coupon(client,admin,code="BIGMIN",discount_value=500,min_subtotal_minor=999999)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"BIGMIN"})
    assert q.status_code==422; assert q.json()["error"]["code"]=="coupon_minimum_not_met"


def test_coupon_reservation_released_when_order_cancelled(login):
    client=login["client"]; admin=create_admin_headers(); service_date=(date.today()+timedelta(days=103)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    coupon=create_coupon(client,admin,code="CANCELME",discount_value=700,total_usage_limit=1)
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"CANCELME"}).json()
    with SessionLocal() as db:
        c=db.get(CouponEntity,UUID(coupon["id"])); assert c.reserved_count==1
    cancelled=client.post(f"/api/v1/customer/orders/{order['id']}/cancel",headers=login["headers"]); assert cancelled.status_code==200
    with SessionLocal() as db:
        c=db.get(CouponEntity,UUID(coupon["id"])); assert c.reserved_count==0; assert c.redeemed_count==0
        red=db.scalar(select(CouponRedemptionEntity).where(CouponRedemptionEntity.order_id==UUID(order["id"]))); assert red.status=="released"


def test_loyalty_quote_requires_available_balance(login):
    client=login["client"]; service_date=(date.today()+timedelta(days=104)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"],"loyalty_points_to_redeem":5})
    assert q.status_code==422; assert q.json()["error"]["code"]=="loyalty_insufficient_points"


def test_loyalty_points_reserved_then_restored_on_cancel(login):
    client=login["client"]; service_date=(date.today()+timedelta(days=105)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    cid=login["body"]["user"]["id"]; set_loyalty_balance(cid,50)
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"],"loyalty_points_to_redeem":10})
    assert order.status_code==201; assert order.json()["discount_minor"]==1000
    with SessionLocal() as db:
        acc=db.get(LoyaltyAccountEntity,UUID(cid)); assert acc.balance_points==40
        red=db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id==UUID(order.json()["id"]))); assert red.status=="reserved"
    client.post(f"/api/v1/customer/orders/{order.json()['id']}/cancel",headers=login["headers"])
    with SessionLocal() as db:
        acc=db.get(LoyaltyAccountEntity,UUID(cid)); assert acc.balance_points==50
        red=db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id==UUID(order.json()["id"]))); assert red.status=="released"


def test_loyalty_redemption_applies_on_payment_success(login):
    client=login["client"]; service_date=(date.today()+timedelta(days=106)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    cid=login["body"]["user"]["id"]; set_loyalty_balance(cid,80)
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"],"loyalty_points_to_redeem":12}).json()
    intent=client.post(f"/api/v1/customer/orders/{order['id']}/payment-intent",headers=login["headers"],json={"idempotency_key":"s24-loyalty-pay-0001"}).json()
    success=webhook(client,{"event_id":"s24-loyalty-success-0001","event_type":"payment.succeeded","payment_reference":intent["provider_reference"],"amount_minor":intent["amount_minor"],"currency":"EGP"})
    assert success.status_code==200
    with SessionLocal() as db:
        acc=db.get(LoyaltyAccountEntity,UUID(cid)); assert acc.balance_points==68; assert acc.lifetime_redeemed_points==12
        red=db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id==UUID(order["id"]))); assert red.status=="applied"
        tx=db.scalar(select(LoyaltyTransactionEntity).where(LoyaltyTransactionEntity.idempotency_key==f"order-redeem:{order['id']}")); assert tx.points==-12


def test_loyalty_cannot_reduce_order_below_minimum_payable(login):
    client=login["client"]; service_date=(date.today()+timedelta(days=107)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    cid=login["body"]["user"]["id"]; set_loyalty_balance(cid,100000)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"],"loyalty_points_to_redeem":100000})
    assert q.status_code==422; assert q.json()["error"]["code"]=="loyalty_redemption_too_high"


def test_subscription_discount_applies_to_quote(login):
    client=login["client"]; admin=create_admin_headers(); cid=login["body"]["user"]["id"]; create_plan_and_grant(client,admin,cid,discount_bps=1000)
    service_date=(date.today()+timedelta(days=108)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"]})
    assert q.status_code==200; body=q.json(); assert body["subscription_plan_name"]=="Baytna Plus"; assert body["subscription_discount_minor"]>0


def test_non_stackable_coupon_disables_subscription_discount(login):
    client=login["client"]; admin=create_admin_headers(); cid=login["body"]["user"]["id"]; create_plan_and_grant(client,admin,cid,discount_bps=1000)
    create_coupon(client,admin,code="NOSTACK",discount_value=500,stack_with_subscription=False)
    service_date=(date.today()+timedelta(days=109)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"NOSTACK"})
    assert q.status_code==200; body=q.json(); assert body["coupon_discount_minor"]==500; assert body["subscription_discount_minor"]==0


def test_customer_can_view_and_cancel_current_subscription(login):
    client=login["client"]; admin=create_admin_headers(); cid=login["body"]["user"]["id"]; plan,_=create_plan_and_grant(client,admin,cid,code="CURRENT")
    plans=client.get("/api/v1/customer/subscriptions/plans",headers=login["headers"]); assert plan["id"] in {x["id"] for x in plans.json()}
    current=client.get("/api/v1/customer/subscriptions/current",headers=login["headers"]); assert current.status_code==200; assert current.json()["plan_id"]==plan["id"]
    cancelled=client.post("/api/v1/customer/subscriptions/current/cancel",headers=login["headers"]); assert cancelled.status_code==200; assert cancelled.json()["status"]=="cancelled"
    current2=client.get("/api/v1/customer/subscriptions/current",headers=login["headers"]); assert current2.status_code==200; assert current2.json() is None


def test_payment_failure_releases_coupon_and_loyalty(login):
    client=login["client"]; admin=create_admin_headers(); cid=login["body"]["user"]["id"]; set_loyalty_balance(cid,30); create_coupon(client,admin,code="FAILBACK",discount_value=400)
    service_date=(date.today()+timedelta(days=110)).isoformat(); _,_,cart=prepare_cart(client,login,service_date)
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"FAILBACK","loyalty_points_to_redeem":5}).json()
    intent=client.post(f"/api/v1/customer/orders/{order['id']}/payment-intent",headers=login["headers"],json={"idempotency_key":"s24-fail-release"}).json()
    failed=webhook(client,{"event_id":"s24-fail-release-event","event_type":"payment.failed","payment_reference":intent["provider_reference"],"amount_minor":intent["amount_minor"],"currency":"EGP"}); assert failed.status_code==200
    with SessionLocal() as db:
        acc=db.get(LoyaltyAccountEntity,UUID(cid)); assert acc.balance_points==30
        cr=db.scalar(select(CouponRedemptionEntity).where(CouponRedemptionEntity.order_id==UUID(order["id"]))); lr=db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id==UUID(order["id"]))); assert cr.status=="released"; assert lr.status=="released"


def test_coupon_customer_usage_limit_after_success(login):
    client=login["client"]; admin=create_admin_headers(); create_coupon(client,admin,code="ONCE",discount_value=500,per_customer_usage_limit=1)
    d1=(date.today()+timedelta(days=111)).isoformat(); _,_,cart=prepare_cart(client,login,d1)
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"],"coupon_code":"ONCE"}).json(); intent=client.post(f"/api/v1/customer/orders/{order['id']}/payment-intent",headers=login["headers"],json={"idempotency_key":"s24-once-pay"}).json(); webhook(client,{"event_id":"s24-once-success","event_type":"payment.succeeded","payment_reference":intent["provider_reference"],"amount_minor":intent["amount_minor"],"currency":"EGP"})
    # New cart on a different date.
    d2=(date.today()+timedelta(days=112)).isoformat(); _,_,cart2=prepare_cart(client,login,d2)
    q=client.post("/api/v1/customer/pricing/quote",headers=login["headers"],json={"cart_id":cart2["id"],"coupon_code":"ONCE"})
    assert q.status_code==409; assert q.json()["error"]["code"]=="coupon_customer_limit_reached"


def test_subscription_snapshot_increases_loyalty_multiplier_on_delivery(login):
    client=login["client"]; admin=create_admin_headers(); cid=login["body"]["user"]["id"]; create_plan_and_grant(client,admin,cid,code="BOOST",discount_bps=0,multiplier_bps=20000)
    service_date=(date.today()+timedelta(days=113)).isoformat(); chef,_,cart=prepare_cart(client,login,service_date)
    # Need address before driver assignment.
    client.post("/api/v1/customer/addresses",headers=login["headers"],json={"label":"المنزل","area":"6 أكتوبر","street":"شارع 1","is_default":True})
    order=client.post("/api/v1/customer/orders",headers=login["headers"],json={"cart_id":cart["id"]}).json(); intent=client.post(f"/api/v1/customer/orders/{order['id']}/payment-intent",headers=login["headers"],json={"idempotency_key":"s24-boost-pay"}).json(); webhook(client,{"event_id":"s24-boost-success","event_type":"payment.succeeded","payment_reference":intent["provider_reference"],"amount_minor":intent["amount_minor"],"currency":"EGP"})
    client.post(f"/api/v1/chef/orders/{order['id']}/accept",headers=chef["headers"],json={}); client.post(f"/api/v1/chef/orders/{order['id']}/start-preparing",headers=chef["headers"],json={}); client.post(f"/api/v1/chef/orders/{order['id']}/ready-for-pickup",headers=chef["headers"],json={})
    driver=login_phone(client,DRIVER_PHONE); client.put("/api/v1/driver/availability",headers=driver["headers"],json={"available":True}); task=next(x for x in client.get("/api/v1/driver/missions/available",headers=driver["headers"]).json() if x["order_id"]==order["id"]); client.post(f"/api/v1/driver/missions/{task['id']}/accept",headers=driver["headers"]); client.post(f"/api/v1/driver/missions/{task['id']}/arrive-pickup",headers=driver["headers"]); client.post(f"/api/v1/driver/missions/{task['id']}/confirm-pickup",headers=driver["headers"]); client.post(f"/api/v1/driver/missions/{task['id']}/start-delivery",headers=driver["headers"]); delivered=client.post(f"/api/v1/driver/missions/{task['id']}/deliver",headers=driver["headers"],json={"proof_type":"otp","proof_reference":"OTP-2424"}); assert delivered.status_code==200
    account=client.get("/api/v1/customer/loyalty",headers=login["headers"]).json(); base=order["total_minor"]//get_settings().loyalty_minor_per_point; assert account["balance_points"]==base*2


def test_admin_pricing_endpoints_require_admin(login):
    r=login["client"].post("/api/v1/admin/pricing/coupons",headers=login["headers"],json={"code":"NOPE","name":"Nope","discount_type":"fixed","discount_value":100})
    assert r.status_code==403; assert r.json()["error"]["code"]=="forbidden"


def test_coupon_total_limit_counts_pending_reservations(client):
    a = login_phone(client, "01074440001")
    b = login_phone(client, "01074440002")
    admin = create_admin_headers()
    create_coupon(client, admin, code="ONLYONE", discount_value=500, total_usage_limit=1, per_customer_usage_limit=1)

    d1 = (date.today() + timedelta(days=114)).isoformat()
    _, _, cart1 = prepare_cart(client, a, d1)
    first = client.post(
        "/api/v1/customer/orders",
        headers=a["headers"],
        json={"cart_id": cart1["id"], "coupon_code": "ONLYONE"},
    )
    assert first.status_code == 201

    d2 = (date.today() + timedelta(days=115)).isoformat()
    _, _, cart2 = prepare_cart(client, b, d2)
    second = client.post(
        "/api/v1/customer/pricing/quote",
        headers=b["headers"],
        json={"cart_id": cart2["id"], "coupon_code": "ONLYONE"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "coupon_usage_limit_reached"


def test_inventory_hold_expiry_releases_coupon_and_loyalty(login):
    from app.core.db_models import InventoryReservationEntity
    from app.core.security import utc_now

    client = login["client"]
    admin = create_admin_headers()
    cid = login["body"]["user"]["id"]
    set_loyalty_balance(cid, 25)
    create_coupon(client, admin, code="EXPIREBACK", discount_value=300)

    service_date = (date.today() + timedelta(days=116)).isoformat()
    _, _, cart = prepare_cart(client, login, service_date)
    order = client.post(
        "/api/v1/customer/orders",
        headers=login["headers"],
        json={
            "cart_id": cart["id"],
            "coupon_code": "EXPIREBACK",
            "loyalty_points_to_redeem": 5,
        },
    ).json()

    with SessionLocal() as db:
        reservation = db.scalar(
            select(InventoryReservationEntity).where(
                InventoryReservationEntity.order_id == UUID(order["id"])
            )
        )
        reservation.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    detail = client.get(
        f"/api/v1/customer/orders/{order['id']}",
        headers=login["headers"],
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "expired"

    with SessionLocal() as db:
        account = db.get(LoyaltyAccountEntity, UUID(cid))
        assert account.balance_points == 25
        coupon = db.scalar(select(CouponEntity).where(CouponEntity.code == "EXPIREBACK"))
        assert coupon.reserved_count == 0
        coupon_redemption = db.scalar(
            select(CouponRedemptionEntity).where(
                CouponRedemptionEntity.order_id == UUID(order["id"])
            )
        )
        loyalty_redemption = db.scalar(
            select(LoyaltyRedemptionEntity).where(
                LoyaltyRedemptionEntity.order_id == UUID(order["id"])
            )
        )
        assert coupon_redemption.status == "released"
        assert loyalty_redemption.status == "released"
