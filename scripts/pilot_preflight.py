from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings


def validate_pilot(settings: Settings) -> list[str]:
    problems: list[str] = []
    if settings.env.lower() not in {"staging", "pilot"}:
        problems.append("BAYTNA_ENV must be staging or pilot")
    if not settings.database_url.startswith("postgresql+psycopg://"):
        problems.append("Pilot database must be PostgreSQL")
    if settings.dev_return_otp:
        problems.append("BAYTNA_DEV_RETURN_OTP must be false")
    if settings.seed_demo_data:
        problems.append("BAYTNA_SEED_DEMO_DATA must be false")
    if settings.payment_provider.lower() != "paymob":
        problems.append("Pilot payment provider must be paymob")
    if settings.payment_provider.lower() == "paymob":
        if not settings.paymob_secret_key:
            problems.append("BAYTNA_PAYMOB_SECRET_KEY is required")
        if not settings.paymob_public_key:
            problems.append("BAYTNA_PAYMOB_PUBLIC_KEY is required")
        if not settings.paymob_hmac_secret:
            problems.append("BAYTNA_PAYMOB_HMAC_SECRET is required")
        if not settings.paymob_payment_method_list:
            problems.append("BAYTNA_PAYMOB_PAYMENT_METHODS is required")
        if not settings.paymob_notification_url.startswith("https://"):
            problems.append("Paymob notification URL must be HTTPS")
        if not settings.paymob_redirection_url.startswith("https://"):
            problems.append("Paymob redirection URL must be HTTPS")
    if settings.storage_provider.lower() != "s3":
        problems.append("Pilot storage must be s3")
    if not settings.storage_bucket:
        problems.append("BAYTNA_STORAGE_BUCKET is required")
    if settings.notification_push_provider.lower() != "fcm":
        problems.append("Pilot push provider must be fcm")
    if not settings.fcm_project_id:
        problems.append("BAYTNA_FCM_PROJECT_ID is required")
    if settings.notification_sms_provider.lower() != "twilio":
        problems.append("Pilot SMS provider must be twilio")
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        problems.append("Twilio credentials are required")
    if not (
        settings.twilio_from_number
        or settings.twilio_messaging_service_sid
    ):
        problems.append("Twilio sender configuration is required")
    if not settings.twilio_status_callback_url.startswith("https://"):
        problems.append("Twilio status callback must be HTTPS")
    if not settings.pilot_public_base_url.startswith("https://"):
        problems.append("Pilot public base URL must be HTTPS")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also contact configured PostgreSQL/S3/FCM/Twilio services. Paymob live charge creation is intentionally not performed.",
    )
    args = parser.parse_args()

    settings = Settings()
    problems = validate_pilot(settings)
    if problems:
        print("PILOT PREFLIGHT FAILED")
        for item in problems:
            print(f"- {item}")
        return 2

    print("Pilot configuration shape: OK")
    if not args.live:
        print("Offline pilot preflight passed.")
        return 0

    from sqlalchemy import text
    from app.core.database import build_engine
    from app.modules.media.storage import (
        S3ObjectStorageProvider,
        build_storage_provider,
    )
    from app.modules.notification_delivery.providers import (
        build_push_provider,
        build_sms_provider,
    )

    engine = build_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("PostgreSQL connectivity: OK")

    storage = build_storage_provider(settings)
    if not isinstance(storage, S3ObjectStorageProvider):
        raise RuntimeError("Pilot storage provider is not S3")
    storage.client.head_bucket(Bucket=settings.storage_bucket)
    print("S3 bucket access: OK")

    push = build_push_provider(settings)
    push.probe()
    print("FCM OAuth credentials: OK")

    sms = build_sms_provider(settings)
    sms.probe()
    print("Twilio credentials: OK")
    print("Paymob configuration: OK (no charge/intention created by preflight)")

    print("Live pilot preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
