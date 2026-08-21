from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import ApiError, api_error_handler
from app.core.middleware import (
    ObservabilityMiddleware,
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.seed import seed_demo_data
from app.modules.admin.router import router as admin_router
from app.modules.admin_ops.router import router as admin_ops_router
from app.modules.analytics.router import router as admin_analytics_router
from app.modules.addresses.router import router as addresses_router
from app.modules.auth.router import router as auth_router
from app.modules.chefs.router import router as chefs_router
from app.modules.chef_app.router import router as chef_app_router
from app.modules.health.router import router as health_router
from app.modules.fulfillment.chef_router import router as chef_fulfillment_router
from app.modules.favorites.router import router as favorites_router
from app.modules.loyalty.router import router as loyalty_router
from app.modules.notifications.router import router as notifications_router
from app.modules.notification_delivery.customer_router import router as notification_delivery_customer_router
from app.modules.notification_delivery.universal_router import router as notification_delivery_universal_router
from app.modules.notification_delivery.admin_router import router as notification_delivery_admin_router
from app.modules.notification_delivery.webhook_router import router as notification_delivery_webhook_router
from app.modules.notification_delivery.vendor_webhook_router import router as notification_vendor_webhook_router
from app.modules.integration_ops.router import router as integration_ops_router
from app.modules.notification_templates.admin_router import router as notification_templates_admin_router
from app.modules.media.router import router as media_router
from app.modules.observability.admin_router import router as observability_admin_router
from app.modules.observability.router import router as observability_router
from app.modules.operations_control.router import router as operations_control_router
from app.modules.operational_economics.router import router as operational_economics_router
from app.modules.financial_automation.router import router as financial_automation_router
from app.modules.launch_governance.router import router as launch_governance_router
from app.modules.vendor_accounting.router import router as vendor_accounting_router
from app.modules.launch_command.router import router as launch_command_router
from app.modules.pilot_stability.router import router as pilot_stability_router
from app.modules.post_launch.router import router as post_launch_router
from app.modules.retention.router import router as retention_router
from app.modules.reliability.admin_router import router as reliability_admin_router
from app.modules.pricing.admin_router import router as admin_pricing_router
from app.modules.pricing.customer_router import router as customer_pricing_router
from app.modules.pricing.subscription_router import router as subscription_router
from app.modules.fulfillment.customer_router import router as customer_tracking_router
from app.modules.delivery.customer_router import router as delivery_customer_router
from app.modules.delivery.driver_router import router as driver_router
from app.modules.driver_app.router import router as driver_app_router
from app.modules.menus.chef_router import router as chef_menu_router
from app.modules.menus.public_router import router as public_menu_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.admin_router import router as admin_payments_router
from app.modules.payments.router import customer_router as customer_payments_router
from app.modules.payments.router import webhook_router as payment_webhook_router
from app.modules.payments.paymob_router import router as paymob_webhook_router
from app.modules.payment_reconciliation.admin_router import router as payment_reconciliation_admin_router
from app.modules.reviews.admin_router import router as admin_reviews_router
from app.modules.reviews.customer_router import router as customer_reviews_router
from app.modules.reviews.public_router import router as public_reviews_router
from app.modules.support.admin_router import router as admin_support_router
from app.modules.support.customer_router import router as customer_support_router
from app.modules.special_orders.admin_router import router as admin_special_orders_router
from app.modules.special_orders.chef_router import router as chef_special_orders_router
from app.modules.special_orders.customer_router import router as customer_special_orders_router
from app.modules.special_orders.public_router import router as public_special_orders_router
from app.modules.users.customer_router import router as customer_router
from app.modules.users.router import router as users_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.50.0",
    description="Baytna marketplace backend — Sprint 50 Launch-Day SLO Automation & Post-Launch Stabilization",
    lifespan=lifespan,
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_host_list or ["*"],
)
app.add_middleware(RequestBodyLimitMiddleware, settings=settings)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(observability_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(customer_router, prefix=settings.api_prefix)
app.include_router(addresses_router, prefix=settings.api_prefix)
app.include_router(chefs_router, prefix=settings.api_prefix)
app.include_router(public_menu_router, prefix=settings.api_prefix)
app.include_router(chef_menu_router, prefix=settings.api_prefix)
app.include_router(chef_app_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(customer_payments_router, prefix=settings.api_prefix)
app.include_router(payment_webhook_router, prefix=settings.api_prefix)
app.include_router(paymob_webhook_router, prefix=settings.api_prefix)
app.include_router(payment_reconciliation_admin_router, prefix=settings.api_prefix)
app.include_router(admin_payments_router, prefix=settings.api_prefix)
app.include_router(chef_fulfillment_router, prefix=settings.api_prefix)
app.include_router(customer_tracking_router, prefix=settings.api_prefix)
app.include_router(delivery_customer_router, prefix=settings.api_prefix)
app.include_router(driver_router, prefix=settings.api_prefix)
app.include_router(driver_app_router, prefix=settings.api_prefix)
app.include_router(customer_reviews_router, prefix=settings.api_prefix)
app.include_router(public_reviews_router, prefix=settings.api_prefix)
app.include_router(admin_reviews_router, prefix=settings.api_prefix)
app.include_router(customer_support_router, prefix=settings.api_prefix)
app.include_router(admin_support_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.include_router(notification_delivery_customer_router, prefix=settings.api_prefix)
app.include_router(notification_delivery_universal_router, prefix=settings.api_prefix)
app.include_router(notification_delivery_admin_router, prefix=settings.api_prefix)
app.include_router(notification_delivery_webhook_router, prefix=settings.api_prefix)
app.include_router(notification_vendor_webhook_router, prefix=settings.api_prefix)
app.include_router(integration_ops_router, prefix=settings.api_prefix)
app.include_router(notification_templates_admin_router, prefix=settings.api_prefix)
app.include_router(media_router, prefix=settings.api_prefix)
app.include_router(favorites_router, prefix=settings.api_prefix)
app.include_router(loyalty_router, prefix=settings.api_prefix)
app.include_router(retention_router, prefix=settings.api_prefix)
app.include_router(customer_pricing_router, prefix=settings.api_prefix)
app.include_router(subscription_router, prefix=settings.api_prefix)
app.include_router(admin_pricing_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(admin_ops_router, prefix=settings.api_prefix)
app.include_router(admin_analytics_router, prefix=settings.api_prefix)
app.include_router(public_special_orders_router, prefix=settings.api_prefix)
app.include_router(customer_special_orders_router, prefix=settings.api_prefix)
app.include_router(chef_special_orders_router, prefix=settings.api_prefix)
app.include_router(admin_special_orders_router, prefix=settings.api_prefix)
app.include_router(reliability_admin_router, prefix=settings.api_prefix)
app.include_router(observability_admin_router, prefix=settings.api_prefix)
app.include_router(operations_control_router, prefix=settings.api_prefix)
app.include_router(operational_economics_router, prefix=settings.api_prefix)
app.include_router(financial_automation_router, prefix=settings.api_prefix)
app.include_router(launch_governance_router, prefix=settings.api_prefix)
app.include_router(vendor_accounting_router, prefix=settings.api_prefix)
app.include_router(launch_command_router, prefix=settings.api_prefix)
app.include_router(post_launch_router, prefix=settings.api_prefix)
app.include_router(pilot_stability_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Baytna API",
        "sprint": "50",
        "status": "launch-day-slo-post-launch-stabilization",
        "docs": "/docs",
    }
