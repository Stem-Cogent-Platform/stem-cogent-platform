from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.billing.fx import FxQuoteError, quote_usd_ngn, usd_cents_to_ngn_kobo
from app.billing.paystack import PaystackClient, PaystackError
from app.core.config import get_settings
from app.core.database import get_session
from app.core.secrets import get_scalar_secret

router = APIRouter(tags=["billing"])
security_logger = logging.getLogger("security.paystack_webhook")
logger = logging.getLogger(__name__)


class CheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_code: Literal["INDIVIDUAL", "TEAM", "COMPANY"]
    idempotency_key: UUID


def verify_paystack_signature(*, raw_body: bytes, supplied_signature: str, secret_key: str) -> bool:
    if len(supplied_signature) != 128:
        return False
    expected = hmac.new(secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, supplied_signature.casefold())


def _event_identity(payload: dict[str, Any], payload_hash: str) -> tuple[str, str]:
    event_type = payload.get("event")
    if not isinstance(event_type, str) or not event_type or len(event_type) > 100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported Paystack event")
    data = payload.get("data")
    reference = None
    if isinstance(data, dict):
        reference = data.get("reference") or data.get("id") or data.get("subscription_code")
    stable = str(reference) if reference is not None else f"sha256:{payload_hash}"
    return event_type, f"{event_type}:{stable}"[:255]


@router.get("/api/v1/billing/plans")
async def list_plans(context: RequestContext = Depends(get_request_context)) -> list[dict[str, Any]]:
    rows = (
        await context.session.execute(
            text(
                """
                SELECT plan_code, name, monthly_price_cents, currency, trial_days,
                       entitlements
                FROM billing.plans WHERE active ORDER BY monthly_price_cents NULLS LAST
                """
            )
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/api/v1/billing/status")
async def billing_status(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    subscription = (
        await context.session.execute(
            text(
                """
                SELECT subscription.*, plan.name, plan.monthly_price_cents, plan.currency
                FROM billing.subscriptions AS subscription
                JOIN billing.plans AS plan ON plan.plan_code = subscription.plan_code
                WHERE subscription.tenant_id = :tenant_id
                ORDER BY subscription.updated_at DESC LIMIT 1
                """
            ),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().one_or_none()
    return jsonable_encoder({"plan_code": context.principal.plan_code,
                             "billing_status": context.principal.billing_status,
                             "subscription": dict(subscription) if subscription else None})


@router.post("/api/v1/billing/checkout", status_code=status.HTTP_201_CREATED)
async def initialize_checkout(
    body: CheckoutInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    plan = (
        await context.session.execute(
            text(
                """
                SELECT plan_code, name, monthly_price_cents, currency
                FROM billing.plans
                WHERE plan_code = :plan_code AND active AND monthly_price_cents IS NOT NULL
                """
            ),
            {"plan_code": body.plan_code},
        )
    ).mappings().one_or_none()
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Billing plan not found")
    if plan["currency"] != "USD":
        logger.error("Billing plan has a non-USD display currency", extra={"plan_code": plan["plan_code"]})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing configuration is unavailable")
    user = (
        await context.session.execute(
            text("SELECT email FROM auth.users WHERE tenant_id = :tenant_id AND id = :user_id"),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().one()
    reference = f"sc-{context.principal.tenant_id.hex[:12]}-{body.idempotency_key.hex}"
    existing = (
        await context.session.execute(
            text("SELECT * FROM billing.checkout_intents WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
            {"tenant_id": context.principal.tenant_id, "reference": reference},
        )
    ).mappings().one_or_none()
    if existing:
        if existing["plan_code"] != plan["plan_code"]:
            raise HTTPException(status.HTTP_409_CONFLICT, "Checkout idempotency key is already bound to another plan")
        if existing["status"] in {"INITIALIZED", "SUCCEEDED"}:
            return jsonable_encoder(dict(existing))
        if existing["status"] == "PENDING":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "CHECKOUT_IN_PROGRESS",
                        "message": "This checkout is already being prepared."},
            )
        if existing["expires_at"] <= datetime.now(UTC):
            await context.session.execute(
                text("UPDATE billing.checkout_intents SET status = 'EXPIRED', updated_at = NOW() WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
                {"tenant_id": context.principal.tenant_id, "reference": reference},
            )
            await context.session.commit()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "CHECKOUT_QUOTE_EXPIRED",
                        "message": "This checkout quote expired. Start a new checkout to receive a current rate."},
            )
        existing = (
            await context.session.execute(
                text(
                    """
                    UPDATE billing.checkout_intents
                    SET status = 'PENDING', error_code = NULL, updated_at = NOW()
                    WHERE tenant_id = :tenant_id AND provider_reference = :reference
                      AND status IN ('FAILED', 'EXPIRED')
                    RETURNING *
                    """
                ),
                {"tenant_id": context.principal.tenant_id, "reference": reference},
            )
        ).mappings().one_or_none()
        await context.session.commit()
        if existing is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "CHECKOUT_IN_PROGRESS",
                        "message": "This checkout is already being prepared."},
            )
    if existing:
        settlement_amount_kobo = existing["amount_cents"]
        settlement_currency = existing["currency"]
        display_amount_cents = existing["display_amount_cents"]
        display_currency = existing["display_currency"]
        fx_rate = existing["fx_rate"]
        fx_source = existing["fx_source"]
        fx_source_url = existing["fx_source_url"]
        fx_quoted_at = existing["fx_quoted_at"]
        if (
            display_amount_cents is None
            or display_currency != "USD"
            or fx_rate is None
            or not fx_source
            or not fx_source_url
            or fx_quoted_at is None
            or settlement_currency != "NGN"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "CHECKOUT_QUOTE_EXPIRED",
                        "message": "This checkout quote can no longer be used. Start a new checkout to receive a current rate."},
            )
    else:
        try:
            quote = await quote_usd_ngn()
            settlement_amount_kobo = usd_cents_to_ngn_kobo(
                usd_cents=plan["monthly_price_cents"], rate=quote.rate
            )
        except (FxQuoteError, ValueError) as exc:
            logger.warning("Official USD/NGN quote unavailable", extra={"plan_code": plan["plan_code"]})
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "FX_QUOTE_UNAVAILABLE",
                        "message": "The official USD/NGN rate is unavailable. Please try again shortly."},
            ) from exc
        settlement_currency = "NGN"
        display_amount_cents = plan["monthly_price_cents"]
        display_currency = plan["currency"]
        fx_rate = quote.rate
        fx_source = quote.source
        fx_source_url = quote.source_url
        fx_quoted_at = quote.quoted_at
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    if existing is None:
        created = (
            await context.session.execute(
            text(
                """
                INSERT INTO billing.checkout_intents (
                    tenant_id, user_id, plan_code, provider_reference, status,
                    amount_cents, currency, display_amount_cents, display_currency,
                    fx_rate, fx_source, fx_source_url, fx_quoted_at, expires_at
                ) VALUES (
                    :tenant_id, :user_id, :plan_code, :reference, 'PENDING',
                    :settlement_amount_kobo, :settlement_currency, :display_amount_cents,
                    :display_currency, :fx_rate, :fx_source, :fx_source_url,
                    :fx_quoted_at, :expires_at
                ) ON CONFLICT (provider, provider_reference) DO NOTHING
                RETURNING *
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             "plan_code": plan["plan_code"], "reference": reference,
             "settlement_amount_kobo": settlement_amount_kobo,
             "settlement_currency": settlement_currency,
             "display_amount_cents": display_amount_cents,
             "display_currency": display_currency,
             "fx_rate": fx_rate, "fx_source": fx_source,
             "fx_source_url": fx_source_url, "fx_quoted_at": fx_quoted_at,
             "expires_at": expires_at},
            )
        ).mappings().one_or_none()
        await context.session.commit()
        if created is None:
            concurrent = (
                await context.session.execute(
                    text("SELECT * FROM billing.checkout_intents WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
                    {"tenant_id": context.principal.tenant_id, "reference": reference},
                )
            ).mappings().one_or_none()
            if concurrent and concurrent["status"] in {"INITIALIZED", "SUCCEEDED"}:
                return jsonable_encoder(dict(concurrent))
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "CHECKOUT_IN_PROGRESS",
                        "message": "This checkout is already being prepared."},
            )
    try:
        checkout = await PaystackClient(_paystack_secret()).initialize_transaction(
            {"email": user["email"], "amount": str(settlement_amount_kobo),
             "currency": settlement_currency, "reference": reference,
             "callback_url": f"{get_settings().FRONTEND_PUBLIC_URL.rstrip('/')}/billing/complete?reference={reference}",
             "metadata": json.dumps({"tenant_id": str(context.principal.tenant_id),
                                      "user_id": str(context.principal.user_id),
                                      "plan_code": plan["plan_code"],
                                      "display_currency": display_currency,
                                      "display_amount_cents": display_amount_cents},
                                     separators=(",", ":"))}
        )
    except PaystackError as exc:
        await context.session.execute(
            text("UPDATE billing.checkout_intents SET status = 'FAILED', error_code = 'PAYSTACK_UNAVAILABLE', updated_at = NOW() WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
            {"tenant_id": context.principal.tenant_id, "reference": reference},
        )
        await context.session.commit()
        logger.warning("Paystack checkout initialization failed", extra={"reference": reference})
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "PAYMENT_PROVIDER_UNAVAILABLE",
                    "message": "We couldn't reach your bank right now. Please try again in a few minutes."},
        ) from exc
    row = (
        await context.session.execute(
            text(
                """
                UPDATE billing.checkout_intents SET status = 'INITIALIZED',
                    authorization_url = :authorization_url, updated_at = NOW()
                WHERE tenant_id = :tenant_id AND provider_reference = :reference
                RETURNING *
                """
            ),
            {"tenant_id": context.principal.tenant_id, "reference": reference,
             "authorization_url": checkout["authorization_url"]},
        )
    ).mappings().one()
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/api/v1/billing/checkout/{reference}")
async def verify_checkout(
    reference: str,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    if len(reference) > 100 or not reference.startswith(f"sc-{context.principal.tenant_id.hex[:12]}-"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checkout not found")
    intent = (
        await context.session.execute(
            text("SELECT * FROM billing.checkout_intents WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
            {"tenant_id": context.principal.tenant_id, "reference": reference},
        )
    ).mappings().one_or_none()
    if intent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checkout not found")
    if intent["status"] != "SUCCEEDED":
        try:
            provider = await PaystackClient(_paystack_secret()).verify_transaction(reference)
        except PaystackError:
            provider = {}
        if provider.get("status") == "success":
            await _activate_checkout(context.session, context.principal.tenant_id, reference, provider)
            await context.session.commit()
            intent = (
                await context.session.execute(
                    text("SELECT * FROM billing.checkout_intents WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
                    {"tenant_id": context.principal.tenant_id, "reference": reference},
                )
            ).mappings().one()
    return jsonable_encoder(dict(intent))


async def _paystack_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    supplied_signature = request.headers.get("x-paystack-signature", "")
    secret_arn = get_settings().PAYSTACK_SECRET_KEY_ARN
    if not secret_arn:
        security_logger.error("Paystack webhook verifier is not configured")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook verifier unavailable")
    if not verify_paystack_signature(
        raw_body=raw_body, supplied_signature=supplied_signature,
        secret_key=get_scalar_secret(secret_arn),
    ):
        security_logger.warning(
            "Rejected invalid Paystack webhook signature",
            extra={"source_ip": request.client.host if request.client else None},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed webhook payload") from error
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed webhook payload")
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    event_type, provider_event_id = _event_identity(payload, payload_hash)
    async for session in get_session():
        inserted = (
            await session.execute(
                text(
                    """
                    INSERT INTO billing.webhook_events (
                        provider, provider_event_id, event_type, payload_hash, status
                    ) VALUES (
                        'PAYSTACK', :provider_event_id, :event_type, :payload_hash, 'RECEIVED'
                    ) ON CONFLICT (provider, provider_event_id) DO NOTHING RETURNING id
                    """
                ),
                {"provider_event_id": provider_event_id, "event_type": event_type,
                 "payload_hash": f"sha256:{payload_hash}"},
            )
        ).scalar_one_or_none()
        if inserted is None:
            await session.commit()
            return {"accepted": True, "duplicate": True}
        try:
            await _process_webhook(session, event_type, payload.get("data"))
        except Exception as exc:
            await session.execute(
                text("UPDATE billing.webhook_events SET status = 'FAILED', processing_attempts = processing_attempts + 1, error_code = 'PROCESSING_FAILED', error_detail = :detail WHERE id = :id"),
                {"id": inserted, "detail": type(exc).__name__},
            )
            await session.commit()
            raise
        await session.execute(
            text("UPDATE billing.webhook_events SET status = 'PROCESSED', processing_attempts = processing_attempts + 1, processed_at = NOW() WHERE id = :id"),
            {"id": inserted},
        )
        await session.commit()
        return {"accepted": True, "duplicate": False}
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook ledger unavailable")


async def _process_webhook(session: Any, event_type: str, data: Any) -> None:
    if not isinstance(data, dict):
        return
    reference = data.get("reference")
    metadata = data.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    if event_type == "charge.success" and isinstance(reference, str) and isinstance(metadata, dict):
        try:
            tenant_id = UUID(str(metadata["tenant_id"]))
        except (KeyError, ValueError):
            return
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        await _activate_checkout(session, tenant_id, reference, data)
    elif event_type in {"subscription.disable", "subscription.not_renew"}:
        subscription_code = data.get("subscription_code")
        if subscription_code:
            await session.execute(
                text("SELECT billing.apply_provider_subscription_state(:reference, :status, TRUE)"),
                {"status": "CANCELLED" if event_type == "subscription.disable" else "ACTIVE",
                 "reference": str(subscription_code)},
            )


async def _activate_checkout(session: Any, tenant_id: UUID, reference: str, data: dict[str, Any]) -> None:
    intent = (
        await session.execute(
            text("SELECT * FROM billing.checkout_intents WHERE tenant_id = :tenant_id AND provider_reference = :reference FOR UPDATE"),
            {"tenant_id": tenant_id, "reference": reference},
        )
    ).mappings().one_or_none()
    if intent is None:
        return
    if intent["status"] == "SUCCEEDED":
        return
    if _provider_amount(data.get("amount")) != intent["amount_cents"] or data.get("currency") != intent["currency"]:
        raise ValueError("Paystack settlement does not match the checkout intent")
    customer_data = data.get("customer")
    customer: dict[str, Any] = customer_data if isinstance(customer_data, dict) else {}
    subscription_data = data.get("subscription")
    subscription: dict[str, Any] = (
        subscription_data if isinstance(subscription_data, dict) else {}
    )
    provider_subscription_ref = subscription.get("subscription_code") or data.get("subscription_code")
    subscription_id = (
        await session.execute(
        text(
            """
            INSERT INTO billing.subscriptions (
                tenant_id, plan_code, status, current_period_start, current_period_end,
                provider, provider_customer_ref, provider_subscription_ref
            ) VALUES (
                :tenant_id, :plan_code, 'ACTIVE', NOW(), NOW() + INTERVAL '1 month',
                'PAYSTACK', :customer_ref, :subscription_ref
            ) ON CONFLICT (tenant_id) WHERE status IN ('TRIALING','ACTIVE','PAST_DUE')
              DO UPDATE SET plan_code = EXCLUDED.plan_code, status = 'ACTIVE',
                current_period_start = EXCLUDED.current_period_start,
                current_period_end = EXCLUDED.current_period_end,
                provider = 'PAYSTACK',
                provider_customer_ref = COALESCE(EXCLUDED.provider_customer_ref, billing.subscriptions.provider_customer_ref),
                provider_subscription_ref = COALESCE(EXCLUDED.provider_subscription_ref, billing.subscriptions.provider_subscription_ref),
                updated_at = NOW()
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "plan_code": intent["plan_code"],
         "customer_ref": customer.get("customer_code"),
         "subscription_ref": provider_subscription_ref},
        )
    ).scalar_one()
    await session.execute(
        text("UPDATE auth.tenants SET status = 'ACTIVE', updated_at = NOW() WHERE id = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO billing.invoices (
                tenant_id, subscription_id, provider, provider_invoice_ref, amount_cents,
                currency, status, paid_at, metadata
            ) VALUES (
                :tenant_id, :subscription_id, 'PAYSTACK', :reference, :amount_cents,
                :currency, 'PAID', NOW(), CAST(:metadata AS JSONB)
            ) ON CONFLICT (provider, provider_invoice_ref) DO NOTHING
            """
        ),
        {"tenant_id": tenant_id, "subscription_id": subscription_id, "reference": reference,
         "amount_cents": intent["amount_cents"], "currency": intent["currency"],
         "metadata": json.dumps({
             "checkout_intent_id": str(intent["id"]),
             "display_amount_cents": intent["display_amount_cents"],
             "display_currency": intent["display_currency"],
             "fx_rate": str(intent["fx_rate"]),
             "fx_source": intent["fx_source"],
             "fx_source_url": intent["fx_source_url"],
             "fx_quoted_at": intent["fx_quoted_at"].isoformat() if intent["fx_quoted_at"] else None,
         }, separators=(",", ":"), sort_keys=True)},
    )
    await session.execute(
        text("UPDATE billing.checkout_intents SET status = 'SUCCEEDED', completed_at = NOW(), updated_at = NOW() WHERE tenant_id = :tenant_id AND provider_reference = :reference"),
        {"tenant_id": tenant_id, "reference": reference},
    )


def _paystack_secret() -> str:
    arn = get_settings().PAYSTACK_SECRET_KEY_ARN
    if not arn:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is unavailable")
    return get_scalar_secret(arn)


def _provider_amount(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


router.add_api_route(
    "/webhooks/paystack", _paystack_webhook, methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
)
router.add_api_route(
    "/billing/webhook", _paystack_webhook, methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED, include_in_schema=False,
)
