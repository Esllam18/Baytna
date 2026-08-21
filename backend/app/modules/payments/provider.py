from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.core.config import Settings


@dataclass(slots=True)
class ProviderLineItem:
    name: str
    amount_minor: int
    quantity: int = 1
    description: str = ""


@dataclass(slots=True)
class ProviderBillingData:
    first_name: str
    last_name: str
    phone_number: str
    email: str
    country: str = "EG"
    city: str = "6 October"
    street: str = "N/A"
    building: str = "N/A"
    floor: str = "N/A"
    apartment: str = "N/A"
    state: str = "Giza"


@dataclass(slots=True)
class ProviderPaymentContext:
    order_id: UUID
    customer_id: UUID
    billing_data: ProviderBillingData
    items: list[ProviderLineItem] = field(default_factory=list)
    notification_url: str = ""
    redirection_url: str = ""


@dataclass(slots=True)
class ProviderIntent:
    reference: str
    checkout_url: str
    provider_order_reference: str | None = None
    provider_status: str | None = None


@dataclass(slots=True)
class ProviderRefund:
    reference: str
    succeeded: bool
    provider_status: str | None = None
    error: str | None = None


class PaymentProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "payment_provider_error",
        status_code: int | None = None,
        permanent: bool = False,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.permanent = permanent
        super().__init__(message)


class PaymentProvider:
    name: str

    def create_intent(
        self,
        *,
        payment_id: UUID,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        context: ProviderPaymentContext | None = None,
    ) -> ProviderIntent:
        raise NotImplementedError

    def refund(
        self,
        *,
        payment_reference: str,
        amount_minor: int,
        idempotency_key: str,
    ) -> ProviderRefund:
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_intent(
        self,
        *,
        payment_id: UUID,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        context: ProviderPaymentContext | None = None,
    ) -> ProviderIntent:
        reference = f"mock_pi_{payment_id.hex}"
        return ProviderIntent(
            reference=reference,
            provider_order_reference=f"mock_order_{payment_id.hex}",
            provider_status="created",
            checkout_url=f"https://mock-payments.local/checkout/{reference}",
        )

    def refund(
        self,
        *,
        payment_reference: str,
        amount_minor: int,
        idempotency_key: str,
    ) -> ProviderRefund:
        return ProviderRefund(
            reference=f"mock_rf_{uuid4().hex}",
            succeeded=True,
            provider_status="succeeded",
        )


class PaymobPaymentProvider(PaymentProvider):
    """Paymob Egypt modern Intention API + hosted Unified Checkout.

    Creation uses the v1 Intention API with the merchant Secret Key.
    The resulting client_secret is intentionally used only to build the
    hosted checkout URL; it is not stored as a standalone database field.
    """

    name = "paymob"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.paymob_base_url.rstrip("/")
        self.intention_url = self.base_url + settings.paymob_intention_path
        self.timeout = settings.paymob_request_timeout_seconds

        if not settings.paymob_secret_key.strip():
            raise ValueError("BAYTNA_PAYMOB_SECRET_KEY is required")
        if not settings.paymob_public_key.strip():
            raise ValueError("BAYTNA_PAYMOB_PUBLIC_KEY is required")
        if not settings.paymob_payment_method_list:
            raise ValueError("BAYTNA_PAYMOB_PAYMENT_METHODS is required")

    def _request_json(
        self,
        *,
        url: str,
        payload: dict,
        headers: dict[str, str],
    ) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **headers,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"detail": raw}
            detail = (
                body.get("detail")
                or body.get("message")
                or body.get("error")
                or f"HTTP {exc.code}"
            )
            raise PaymentProviderError(
                f"Paymob request failed: {detail}",
                code="paymob_http_error",
                status_code=exc.code,
                permanent=400 <= exc.code < 500 and exc.code != 429,
            ) from exc
        except urllib.error.URLError as exc:
            raise PaymentProviderError(
                f"Paymob transport failure: {exc}",
                code="paymob_transport_error",
                permanent=False,
            ) from exc

    def create_intent(
        self,
        *,
        payment_id: UUID,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        context: ProviderPaymentContext | None = None,
    ) -> ProviderIntent:
        if context is None:
            raise ValueError("Paymob requires payment context")

        items = context.items or [
            ProviderLineItem(
                name=f"Baytna order {context.order_id}",
                amount_minor=amount_minor,
                quantity=1,
            )
        ]

        # Paymob validates the Intention amount against the item total.
        # When platform delivery/discount accounting means order lines do not
        # sum exactly to the payable amount, use one canonical payable item.
        items_total = sum(x.amount_minor * x.quantity for x in items)
        if items_total != amount_minor:
            items = [
                ProviderLineItem(
                    name=f"Baytna order {context.order_id}",
                    description="Baytna payable order total",
                    amount_minor=amount_minor,
                    quantity=1,
                )
            ]

        billing = context.billing_data
        payload = {
            "amount": amount_minor,
            "currency": currency.upper(),
            "payment_methods": self.settings.paymob_payment_method_list,
            "items": [
                {
                    "name": item.name[:255],
                    "amount": item.amount_minor,
                    "description": item.description[:255],
                    "quantity": item.quantity,
                }
                for item in items
            ],
            "billing_data": {
                "apartment": billing.apartment or "N/A",
                "first_name": billing.first_name or "Baytna",
                "last_name": billing.last_name or "Customer",
                "street": billing.street or "N/A",
                "building": billing.building or "N/A",
                "phone_number": billing.phone_number,
                "country": billing.country or "EG",
                "email": billing.email,
                "floor": billing.floor or "N/A",
                "state": billing.state or "Giza",
                "city": billing.city or "6 October",
            },
            "special_reference": str(payment_id),
            "notification_url": (
                context.notification_url
                or self.settings.paymob_notification_url
            ),
            "redirection_url": (
                context.redirection_url
                or self.settings.paymob_redirection_url
            ),
        }

        response = self._request_json(
            url=self.intention_url,
            payload=payload,
            headers={
                "Authorization": f"Token {self.settings.paymob_secret_key}",
                # Safe merchant-side trace only. The Paymob API remains the
                # authoritative idempotency boundary through special_reference.
                "X-Baytna-Idempotency-Key": idempotency_key,
            },
        )

        intention_id = response.get("id")
        client_secret = response.get("client_secret")
        provider_order_reference = response.get("intention_order_id")
        if not intention_id or not client_secret:
            raise PaymentProviderError(
                "Paymob Intention response is missing id/client_secret",
                code="paymob_intention_response_invalid",
                permanent=False,
            )

        checkout_query = urllib.parse.urlencode(
            {
                "publicKey": self.settings.paymob_public_key,
                "clientSecret": client_secret,
            }
        )
        checkout_base = self.settings.paymob_unified_checkout_url
        separator = "&" if "?" in checkout_base else "?"
        checkout_url = checkout_base + separator + checkout_query

        return ProviderIntent(
            reference=str(intention_id),
            provider_order_reference=(
                str(provider_order_reference)
                if provider_order_reference is not None
                else None
            ),
            provider_status=str(response.get("status") or "created"),
            checkout_url=checkout_url,
        )

    def _legacy_auth_token(self) -> str:
        if not self.settings.paymob_api_key.strip():
            raise PaymentProviderError(
                "Paymob legacy API key is not configured for refunds",
                code="paymob_refund_credentials_missing",
                permanent=True,
            )
        response = self._request_json(
            url=self.base_url + self.settings.paymob_auth_token_path,
            payload={"api_key": self.settings.paymob_api_key},
            headers={},
        )
        token = response.get("token")
        if not token:
            raise PaymentProviderError(
                "Paymob auth token response is invalid",
                code="paymob_auth_response_invalid",
                permanent=False,
            )
        return str(token)

    def refund(
        self,
        *,
        payment_reference: str,
        amount_minor: int,
        idempotency_key: str,
    ) -> ProviderRefund:
        if not self.settings.paymob_refund_enabled:
            return ProviderRefund(
                reference="",
                succeeded=False,
                provider_status="disabled",
                error="Paymob refund API is disabled by configuration",
            )
        if not payment_reference:
            return ProviderRefund(
                reference="",
                succeeded=False,
                provider_status="transaction_reference_missing",
                error="Paymob transaction reference is required for refund",
            )

        auth_token = self._legacy_auth_token()
        response = self._request_json(
            url=self.base_url + self.settings.paymob_refund_path,
            payload={
                "auth_token": auth_token,
                "transaction_id": int(payment_reference),
                "amount_cents": amount_minor,
            },
            headers={"X-Baytna-Idempotency-Key": idempotency_key},
        )

        reference = response.get("id") or response.get("transaction_id")
        succeeded = bool(
            response.get("success") is True
            or response.get("is_refund") is True
        )
        return ProviderRefund(
            reference=str(reference or ""),
            succeeded=succeeded,
            provider_status=(
                "succeeded"
                if succeeded
                else str(response.get("status") or "submitted")
            ),
            error=None if succeeded else str(response.get("message") or ""),
        )


def get_provider(
    name: str,
    settings: Settings | None = None,
) -> PaymentProvider:
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockPaymentProvider()
    if normalized == "paymob":
        if settings is None:
            raise ValueError("Settings are required for Paymob provider")
        return PaymobPaymentProvider(settings)
    raise ValueError(f"Unsupported payment provider: {name}")
