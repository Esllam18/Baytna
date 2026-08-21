from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_WEAK_SECRET_MARKERS = (
    "change-this",
    "development",
    "test-",
    "example",
    "password",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BAYTNA_",
        env_file="../.env",
        extra="ignore",
    )

    env: str = "development"
    app_name: str = "Baytna API"
    api_prefix: str = "/api/v1"
    release_version: str = "0.50.0"
    release_commit: str = ""
    release_slot: str = "local"
    cors_origins: str = "http://localhost:3000,http://localhost:8081"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    trust_proxy_headers: bool = False

    database_url: str = (
        "postgresql+psycopg://baytna:baytna_dev_password@localhost:5432/baytna"
    )

    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    dev_return_otp: bool = True
    otp_pepper: str = "change-this-development-otp-pepper"

    jwt_secret: str = Field(
        default="change-this-development-jwt-secret-at-least-32-characters"
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    refresh_token_pepper: str = "change-this-development-refresh-pepper"

    seed_demo_data: bool = True
    inventory_hold_ttl_minutes: int = 10
    payment_provider: str = "mock"
    payment_webhook_secret: str = "change-this-development-payment-webhook-secret"
    payment_intent_ttl_minutes: int = 15
    # Sprint 32 — Paymob Egypt payment gateway
    paymob_base_url: str = "https://accept.paymob.com"
    paymob_secret_key: str = ""
    paymob_public_key: str = ""
    paymob_hmac_secret: str = ""
    paymob_api_key: str = ""
    paymob_payment_methods: str = ""
    paymob_notification_url: str = ""
    paymob_redirection_url: str = ""
    paymob_unified_checkout_url: str = "https://accept.paymob.com/unifiedcheckout/"
    paymob_intention_path: str = "/v1/intention/"
    paymob_auth_token_path: str = "/api/auth/tokens"
    paymob_refund_path: str = "/api/acceptance/void_refund/refund"
    paymob_request_timeout_seconds: int = 15
    paymob_refund_enabled: bool = False
    paymob_reconciliation_batch_size: int = 200
    chef_acceptance_sla_minutes: int = 10
    loyalty_minor_per_point: int = 1000
    special_order_payment_window_minutes: int = 1440
    special_order_max_days_ahead: int = 60
    loyalty_redemption_minor_per_point: int = 100
    minimum_payable_minor: int = 100

    worker_batch_size: int = 25
    worker_poll_seconds: int = 5
    worker_stale_seconds: int = 120
    ops_delivery_assignment_sla_minutes: int = 10
    ops_support_urgent_sla_minutes: int = 15
    ops_support_high_sla_minutes: int = 60
    ops_support_normal_sla_minutes: int = 240
    ops_incident_auto_resolve: bool = True
    delivery_promise_timezone: str = "Africa/Cairo"
    delivery_promise_required: bool = False
    ops_delivery_promise_warning_minutes: int = 20
    ops_incident_auto_escalate_minutes: int = 15
    ops_notification_min_severity: str = "high"
    economics_required_order_cost_types: str = "chef_payout,delivery_partner,payment_processing"
    economics_default_min_contribution_margin_pct: float = 15.0
    economics_default_min_delivered_orders: int = 100
    provider_import_max_lines: int = 2000
    provider_import_request_timeout_seconds: int = 20
    expansion_rollout_required: bool = False
    expansion_required_budget_categories: str = "operations,chef_onboarding,delivery_supply,contingency"
    expansion_canary_percent: int = 10
    expansion_limited_percent: int = 50
    expansion_default_daily_order_cap: int = 25
    traffic_require_delivery_address_for_checkout: bool = False
    traffic_default_hourly_order_cap: int = 8
    traffic_default_chef_daily_order_cap: int = 12
    traffic_warning_utilization_pct: float = 80.0
    traffic_critical_utilization_pct: float = 95.0
    traffic_rejection_spike_pct: float = 30.0
    traffic_rejection_spike_min_attempts: int = 5
    vendor_accounting_require_dual_control: bool = False
    vendor_accounting_require_closed_settlements_for_rollout: bool = False
    vendor_accounting_high_value_import_minor: int = 1_000_000
    launch_command_required: bool = False
    launch_command_require_dual_control: bool = False
    launch_override_max_minutes: int = 120
    launch_financial_close_grace_hours: int = 8
    launch_rollback_target_seconds: int = 300
    launch_evidence_require_no_active_overrides: bool = True

    # Sprint 50 — launch-day SLO automation & post-launch stabilization
    slo_auto_pause_default_enabled: bool = False
    slo_consecutive_red_snapshots: int = 2
    slo_capacity_forecast_lookback_snapshots: int = 6
    launch_daily_close_cadence_enabled: bool = False
    launch_post_launch_stabilization_days: int = 7
    launch_incomplete_evidence_retention_days: int = 30
    launch_expansion_review_window_days: int = 7

    background_job_max_attempts: int = 5
    outbox_max_attempts: int = 8
    retry_base_seconds: int = 5
    outbox_publisher: str = "logging"

    # Sprint 28 — transport/application security
    max_request_body_bytes: int = 1_048_576
    security_hsts_enabled: bool = False
    security_hsts_max_age_seconds: int = 31_536_000
    security_content_security_policy: str = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
        "form-action 'self'"
    )

    # Fixed-window distributed rate limits. Defaults are deliberately generous
    # for local development/test fixtures; production should tune lower.
    rate_limit_otp_send_ip: int = 60
    rate_limit_otp_send_phone: int = 30
    rate_limit_otp_verify_ip: int = 120
    rate_limit_otp_verify_phone: int = 60
    rate_limit_refresh_ip: int = 120
    rate_limit_payment_webhook_ip: int = 300
    rate_limit_window_seconds: int = 60

    security_event_retention_days: int = 30
    rate_limit_retention_minutes: int = 120

    metrics_enabled: bool = True
    metrics_path: str = "/metrics"

    # Sprint 29 — media/object storage
    storage_provider: str = "local"
    storage_local_root: str = "/tmp/baytna-media"
    storage_bucket: str = ""
    storage_region: str = "eu-central-1"
    storage_endpoint_url: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    media_signing_secret: str = "change-this-development-media-signing-secret"
    media_upload_ttl_seconds: int = 900
    media_download_ttl_seconds: int = 300
    media_max_upload_bytes: int = 10_485_760

    # Sprint 29 — notification delivery / external providers
    integration_encryption_secret: str = (
        "change-this-development-integration-encryption-secret"
    )
    notification_push_provider: str = "logging"
    notification_push_endpoint: str = ""
    notification_push_bearer_token: str = ""
    notification_sms_provider: str = "logging"
    notification_sms_endpoint: str = ""
    notification_sms_bearer_token: str = ""
    notification_delivery_max_attempts: int = 5
    notification_dispatch_batch_size: int = 50
    notification_provider_webhook_secret: str = "change-this-development-notification-webhook-secret"
    notification_reconciliation_batch_size: int = 100

    # Sprint 31 — real notification providers
    fcm_project_id: str = ""
    fcm_credentials_file: str = ""
    fcm_validate_only: bool = False
    
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_messaging_service_sid: str = ""
    twilio_status_callback_url: str = ""
    twilio_api_base_url: str = "https://api.twilio.com/2010-04-01"
    
    # Pilot/staging safety profile
    pilot_public_base_url: str = ""
    pilot_require_real_notifications: bool = False
    pilot_require_real_payments: bool = False
    
    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts.split(",") if x.strip()]

    @property
    def paymob_payment_method_list(self) -> list[int | str]:
        values: list[int | str] = []
        for raw in self.paymob_payment_methods.split(","):
            item = raw.strip()
            if not item:
                continue
            values.append(int(item) if item.isdigit() else item)
        return values


    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("BAYTNA_JWT_SECRET must be at least 32 characters")
        return value

    @field_validator(
        "otp_pepper",
        "refresh_token_pepper",
        "payment_webhook_secret",
    )
    @classmethod
    def validate_security_secret_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Security peppers/secrets must be at least 8 characters")
        return value

    @field_validator(
        "max_request_body_bytes",
        "rate_limit_window_seconds",
        "security_event_retention_days",
        "rate_limit_retention_minutes",
        "media_upload_ttl_seconds",
        "media_download_ttl_seconds",
        "media_max_upload_bytes",
        "notification_delivery_max_attempts",
        "notification_dispatch_batch_size",
        "notification_reconciliation_batch_size",
        "paymob_request_timeout_seconds",
        "paymob_reconciliation_batch_size",
        "ops_delivery_assignment_sla_minutes",
        "ops_support_urgent_sla_minutes",
        "ops_support_high_sla_minutes",
        "ops_support_normal_sla_minutes",
        "ops_delivery_promise_warning_minutes",
        "ops_incident_auto_escalate_minutes",
        "economics_default_min_delivered_orders",
        "provider_import_max_lines",
        "provider_import_request_timeout_seconds",
        "expansion_canary_percent",
        "expansion_limited_percent",
        "expansion_default_daily_order_cap",
        "vendor_accounting_high_value_import_minor",
        "launch_rollback_target_seconds",
        "launch_financial_close_grace_hours",
        "launch_override_max_minutes",
        "slo_consecutive_red_snapshots",
        "slo_capacity_forecast_lookback_snapshots",
        "launch_post_launch_stabilization_days",
        "launch_incomplete_evidence_retention_days",
        "launch_expansion_review_window_days",
        "traffic_rejection_spike_min_attempts",
        "traffic_default_chef_daily_order_cap",
        "traffic_default_hourly_order_cap",
    )
    @classmethod
    def validate_positive_values(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Security/retention values must be greater than zero")
        return value


    @field_validator(
        "traffic_warning_utilization_pct",
        "traffic_critical_utilization_pct",
        "traffic_rejection_spike_pct",
    )
    @classmethod
    def validate_traffic_percent(cls, value: float) -> float:
        if value <= 0 or value > 100:
            raise ValueError("Traffic percentages must be in (0, 100]")
        return value

    @field_validator("delivery_promise_timezone")
    @classmethod
    def validate_delivery_promise_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "BAYTNA_DELIVERY_PROMISE_TIMEZONE must be a valid IANA timezone"
            ) from exc
        return value

    @field_validator("ops_notification_min_severity")
    @classmethod
    def validate_ops_notification_min_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"info", "warning", "high", "critical"}:
            raise ValueError(
                "BAYTNA_OPS_NOTIFICATION_MIN_SEVERITY must be "
                "info, warning, high, or critical"
            )
        return normalized

    @field_validator("economics_default_min_contribution_margin_pct")
    @classmethod
    def validate_economics_margin(cls, value: float) -> float:
        if value < -100 or value > 100:
            raise ValueError(
                "BAYTNA_ECONOMICS_DEFAULT_MIN_CONTRIBUTION_MARGIN_PCT "
                "must be between -100 and 100"
            )
        return value

    @field_validator("expansion_canary_percent", "expansion_limited_percent")
    @classmethod
    def validate_rollout_percent(cls, value: int) -> int:
        if value <= 0 or value >= 100:
            raise ValueError("Expansion rollout percentages must be between 1 and 99")
        return value

    @field_validator("expansion_required_budget_categories")
    @classmethod
    def validate_expansion_budget_categories(cls, value: str) -> str:
        allowed = {
            "operations",
            "marketing",
            "chef_onboarding",
            "delivery_supply",
            "contingency",
            "support",
            "technology",
        }
        normalized = [x.strip().lower() for x in value.split(",") if x.strip()]
        if not normalized:
            raise ValueError("Expansion budget categories cannot be empty")
        invalid = sorted(set(normalized) - allowed)
        if invalid:
            raise ValueError(
                "Unsupported expansion budget categories: " + ", ".join(invalid)
            )
        return ",".join(dict.fromkeys(normalized))

    @field_validator("economics_required_order_cost_types")
    @classmethod
    def validate_economics_required_cost_types(cls, value: str) -> str:
        allowed = {
            "chef_payout",
            "delivery_partner",
            "payment_processing",
            "packaging",
            "refund_fee",
            "customer_recovery",
            "other_variable",
        }
        normalized = [x.strip().lower() for x in value.split(",") if x.strip()]
        if not normalized:
            raise ValueError(
                "BAYTNA_ECONOMICS_REQUIRED_ORDER_COST_TYPES cannot be empty"
            )
        invalid = sorted(set(normalized) - allowed)
        if invalid:
            raise ValueError(
                "Unsupported required economics cost types: "
                + ", ".join(invalid)
            )
        return ",".join(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_production_safety(self):
        if self.env.lower() != "production":
            return self

        problems: list[str] = []

        if self.dev_return_otp:
            problems.append("BAYTNA_DEV_RETURN_OTP must be false")
        if self.seed_demo_data:
            problems.append("BAYTNA_SEED_DEMO_DATA must be false")
        if self.payment_provider.strip().lower() == "mock":
            problems.append("BAYTNA_PAYMENT_PROVIDER cannot be mock")
        if self.payment_provider.strip().lower() == "paymob":
            if not self.paymob_secret_key.strip():
                problems.append("BAYTNA_PAYMOB_SECRET_KEY is required")
            if not self.paymob_public_key.strip():
                problems.append("BAYTNA_PAYMOB_PUBLIC_KEY is required")
            if not self.paymob_hmac_secret.strip():
                problems.append("BAYTNA_PAYMOB_HMAC_SECRET is required")
            if not self.paymob_payment_method_list:
                problems.append("BAYTNA_PAYMOB_PAYMENT_METHODS is required")
            if not self.paymob_notification_url.lower().startswith("https://"):
                problems.append("BAYTNA_PAYMOB_NOTIFICATION_URL must be HTTPS")
            if not self.paymob_redirection_url.lower().startswith("https://"):
                problems.append("BAYTNA_PAYMOB_REDIRECTION_URL must be HTTPS")
            if self.paymob_refund_enabled and not self.paymob_api_key.strip():
                problems.append(
                    "BAYTNA_PAYMOB_API_KEY is required when Paymob refunds are enabled"
                )
        if not self.database_url.startswith("postgresql+psycopg://"):
            problems.append("BAYTNA_DATABASE_URL must target PostgreSQL")

        if not self.cors_origin_list:
            problems.append("BAYTNA_CORS_ORIGINS must not be empty")
        for origin in self.cors_origin_list:
            lowered = origin.lower()
            if origin == "*" or "localhost" in lowered or "127.0.0.1" in lowered:
                problems.append(
                    "BAYTNA_CORS_ORIGINS cannot use wildcard/localhost in production"
                )
                break

        hosts = self.allowed_host_list
        if not hosts or "*" in hosts:
            problems.append(
                "BAYTNA_ALLOWED_HOSTS must contain explicit production hosts"
            )

        if not self.security_hsts_enabled:
            problems.append("BAYTNA_SECURITY_HSTS_ENABLED must be true")

        if not self.expansion_rollout_required:
            problems.append("BAYTNA_EXPANSION_ROLLOUT_REQUIRED must be true")
        if not self.traffic_require_delivery_address_for_checkout:
            problems.append(
                "BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT must be true"
            )
        if not self.vendor_accounting_require_dual_control:
            problems.append(
                "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL must be true"
            )
        if not self.vendor_accounting_require_closed_settlements_for_rollout:
            problems.append(
                "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT must be true"
            )
        if not self.launch_command_required:
            problems.append("BAYTNA_LAUNCH_COMMAND_REQUIRED must be true")
        if not self.launch_command_require_dual_control:
            problems.append(
                "BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL must be true"
            )
        if not self.slo_auto_pause_default_enabled:
            problems.append(
                "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED must be true"
            )
        if self.slo_consecutive_red_snapshots < 2:
            problems.append(
                "BAYTNA_SLO_CONSECUTIVE_RED_SNAPSHOTS must be at least 2"
            )
        if not self.launch_daily_close_cadence_enabled:
            problems.append(
                "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED must be true"
            )
        if self.traffic_warning_utilization_pct > self.traffic_critical_utilization_pct:
            problems.append(
                "traffic warning utilization cannot exceed critical utilization"
            )

        if self.storage_provider.strip().lower() != "s3":
            problems.append("BAYTNA_STORAGE_PROVIDER must be s3 in production")
        if not self.storage_bucket.strip():
            problems.append("BAYTNA_STORAGE_BUCKET is required in production")
        if self.notification_push_provider.strip().lower() == "logging":
            problems.append(
                "BAYTNA_NOTIFICATION_PUSH_PROVIDER cannot be logging in production"
            )
        if self.notification_sms_provider.strip().lower() == "logging":
            problems.append(
                "BAYTNA_NOTIFICATION_SMS_PROVIDER cannot be logging in production"
            )

        if self.notification_push_provider.strip().lower() == "fcm":
            if not self.fcm_project_id.strip():
                problems.append("BAYTNA_FCM_PROJECT_ID is required for FCM")
        if self.notification_sms_provider.strip().lower() == "twilio":
            if not self.twilio_account_sid.strip():
                problems.append("BAYTNA_TWILIO_ACCOUNT_SID is required for Twilio")
            if not self.twilio_auth_token.strip():
                problems.append("BAYTNA_TWILIO_AUTH_TOKEN is required for Twilio")
            if not (
                self.twilio_from_number.strip()
                or self.twilio_messaging_service_sid.strip()
            ):
                problems.append(
                    "Twilio requires BAYTNA_TWILIO_FROM_NUMBER or "
                    "BAYTNA_TWILIO_MESSAGING_SERVICE_SID"
                )
            if not self.twilio_status_callback_url.lower().startswith("https://"):
                problems.append(
                    "BAYTNA_TWILIO_STATUS_CALLBACK_URL must be HTTPS"
                )

        # Paymob production secrets are checked only when Paymob is active.
        if self.payment_provider.strip().lower() == "paymob":
            for field_name, secret in (
                ("BAYTNA_PAYMOB_SECRET_KEY", self.paymob_secret_key),
                ("BAYTNA_PAYMOB_HMAC_SECRET", self.paymob_hmac_secret),
            ):
                lowered = secret.lower()
                if len(secret) < 24 or any(
                    marker in lowered for marker in _WEAK_SECRET_MARKERS
                ):
                    problems.append(f"{field_name} must be a strong production secret")

        for field_name, secret in (
            ("BAYTNA_JWT_SECRET", self.jwt_secret),
            ("BAYTNA_OTP_PEPPER", self.otp_pepper),
            ("BAYTNA_REFRESH_TOKEN_PEPPER", self.refresh_token_pepper),
            ("BAYTNA_PAYMENT_WEBHOOK_SECRET", self.payment_webhook_secret),
            ("BAYTNA_MEDIA_SIGNING_SECRET", self.media_signing_secret),
            (
                "BAYTNA_INTEGRATION_ENCRYPTION_SECRET",
                self.integration_encryption_secret,
            ),
            (
                "BAYTNA_NOTIFICATION_PROVIDER_WEBHOOK_SECRET",
                self.notification_provider_webhook_secret,
            ),
            ("BAYTNA_TWILIO_AUTH_TOKEN", self.twilio_auth_token or "x" * 32),
        ):
            lowered = secret.lower()
            if len(secret) < 32 or any(marker in lowered for marker in _WEAK_SECRET_MARKERS):
                problems.append(f"{field_name} must be a strong production secret")

        if problems:
            raise ValueError(
                "Unsafe production configuration: " + "; ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
