from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "apps/customer_app/app/account/index.tsx",
    "apps/customer_app/app/account/reviews.tsx",
    "apps/customer_app/app/orders/[orderId].tsx",
    "apps/customer_app/app/orders/[orderId]/review.tsx",
    "apps/customer_app/app/special-orders/index.tsx",
    "apps/customer_app/app/special-orders/new.tsx",
    "apps/customer_app/app/special-orders/[specialOrderId].tsx",
    "apps/customer_app/app/chefs/[chefId].tsx",
    "apps/customer_app/app/chefs/[chefId]/dish/[dishId].tsx",
    "apps/customer_app/app/account/support/new.tsx",
    "apps/customer_app/src/hooks/usePostOrder.ts",
    "apps/customer_app/src/ui/StarRating.tsx",
    "apps/customer_app/src/api/customer.ts",
    "apps/customer_app/src/api/types.ts",
]

missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit("Missing Sprint 37 frontend files: " + ", ".join(missing))

api = (ROOT / "apps/customer_app/src/api/customer.ts").read_text(encoding="utf-8")
order = (ROOT / "apps/customer_app/app/orders/[orderId].tsx").read_text(encoding="utf-8")
review = (ROOT / "apps/customer_app/app/orders/[orderId]/review.tsx").read_text(encoding="utf-8")
special_new = (ROOT / "apps/customer_app/app/special-orders/new.tsx").read_text(encoding="utf-8")
special_detail = (ROOT / "apps/customer_app/app/special-orders/[specialOrderId].tsx").read_text(encoding="utf-8")
chef = (ROOT / "apps/customer_app/app/chefs/[chefId].tsx").read_text(encoding="utf-8")
dish = (ROOT / "apps/customer_app/app/chefs/[chefId]/dish/[dishId].tsx").read_text(encoding="utf-8")
account = (ROOT / "apps/customer_app/app/account/index.tsx").read_text(encoding="utf-8")

for symbol in [
    "reviewEligibility",
    "createReview",
    "updateReview",
    "myReviews",
    "chefReviews",
    "chefRatingSummary",
    "chefAvailability",
    "specialOrders",
    "createSpecialOrder",
    "acceptSpecialOrderCounter",
    "checkoutSpecialOrder",
]:
    assert symbol in api

assert 'router.push(`/orders/${o.id}/review`)' in order
assert 'pathname: "/account/support/new"' in order
assert "StarRating" in review
assert "createSpecialOrder" in special_new
assert "checkoutSpecialOrder" in special_detail
assert "acceptSpecialOrderCounter" in special_detail
assert "useChefReviews" in chef and "useChefRatingSummary" in chef
assert 'pathname:"/special-orders/new"' in dish
assert 'router.push("/account/reviews")' in account
assert 'router.push("/special-orders")' in account

print("Sprint 37 frontend static verification passed.")
