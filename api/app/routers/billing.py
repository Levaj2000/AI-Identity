"""Stripe billing — checkout, customer portal, and webhook handler.

Endpoints:
    POST /api/v1/billing/checkout    — Create a Stripe Checkout session (upgrade to Pro)
    POST /api/v1/billing/portal      — Create a Stripe Customer Portal session (manage sub)
    POST /api/v1/billing/webhook     — Stripe webhook handler (tier sync)
    GET  /api/v1/billing/status      — Current billing status
"""

import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from common.config.settings import settings
from common.models import User, get_db

logger = logging.getLogger("ai_identity.api.billing")

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

# Configure Stripe SDK
stripe.api_key = settings.stripe_secret_key

# Map Stripe Price IDs → tier names
PRICE_TO_TIER: dict[str, str] = {}
if settings.stripe_price_id_pro:
    PRICE_TO_TIER[settings.stripe_price_id_pro] = "pro"
if settings.stripe_price_id_enterprise:
    PRICE_TO_TIER[settings.stripe_price_id_enterprise] = "enterprise"


# ── Helpers ──────────────────────────────────────────────────────────────


def _get_or_create_stripe_customer(user: User) -> str:
    """Get existing Stripe customer or create one. Returns customer ID."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    return customer.id


def _sync_tier_from_subscription(db: Session, subscription: stripe.Subscription) -> None:
    """Update user tier based on Stripe subscription status."""
    customer_id = subscription.customer
    if isinstance(customer_id, stripe.Customer):
        customer_id = customer_id.id

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.warning("Webhook: no user found for Stripe customer %s", customer_id)
        return

    if subscription.status in ("active", "trialing"):
        # Determine tier from the subscription's price
        items = subscription.get("items", {})
        data = items.get("data", []) if isinstance(items, dict) else []
        if data:
            price_id = data[0].get("price", {}).get("id", "") if isinstance(data[0], dict) else ""
            new_tier = PRICE_TO_TIER.get(price_id, "pro")
        else:
            new_tier = "pro"

        user.tier = new_tier
        user.stripe_subscription_id = subscription.id
        logger.info("Tier synced: user=%s → %s (sub=%s)", user.email, new_tier, subscription.id)

    elif subscription.status in ("canceled", "unpaid", "incomplete_expired"):
        user.tier = "free"
        user.stripe_subscription_id = None
        logger.info("Tier downgraded: user=%s → free (sub canceled)", user.email)

    elif subscription.status == "past_due":
        # Keep current tier but log warning — Stripe will retry payment
        logger.warning("Payment past due: user=%s, sub=%s", user.email, subscription.id)

    db.commit()


# ── POST /api/v1/billing/checkout ────────────────────────────────────────


@router.post(
    "/checkout",
    summary="Create checkout session",
    responses={
        400: {"description": "Already on Pro or no Stripe config"},
    },
)
def create_checkout_session(
    plan: str = "pro",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session to upgrade to Pro or Enterprise.

    Returns a `checkout_url` — redirect the user there to complete payment.
    After payment, Stripe redirects to the dashboard with a session ID.
    The webhook handler automatically upgrades the user's tier.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe billing is not configured")

    price_id = (
        settings.stripe_price_id_pro if plan == "pro" else settings.stripe_price_id_enterprise
    )
    if not price_id:
        raise HTTPException(status_code=400, detail=f"No price configured for plan: {plan}")

    if user.tier == plan:
        raise HTTPException(status_code=400, detail=f"Already on the {plan} plan")

    # Get or create Stripe customer
    customer_id = _get_or_create_stripe_customer(user)

    # Persist customer ID if new
    if not user.stripe_customer_id:
        user.stripe_customer_id = customer_id
        db.commit()

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
            metadata={"user_id": str(user.id)},
            subscription_data={"metadata": {"user_id": str(user.id)}},
        )
    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error") from e

    logger.info("Checkout session created: user=%s, plan=%s", user.email, plan)
    return {"checkout_url": session.url, "session_id": session.id}


# ── POST /api/v1/billing/portal ──────────────────────────────────────────


@router.post(
    "/portal",
    summary="Create customer portal session",
)
def create_portal_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscriptions.

    Returns a `portal_url` — redirect the user there to update payment methods,
    change plans, or cancel their subscription.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe billing is not configured")

    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found. Subscribe first.")

    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=settings.stripe_cancel_url,
        )
    except stripe.StripeError as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error") from e

    return {"portal_url": session.url}


# ── GET /api/v1/billing/status ───────────────────────────────────────────


@router.get(
    "/status",
    summary="Get billing status",
)
def billing_status(
    user: User = Depends(get_current_user),
):
    """Get current billing status including tier, Stripe IDs, and subscription state."""
    result = {
        "tier": user.tier,
        "has_billing_account": user.stripe_customer_id is not None,
        "has_subscription": user.stripe_subscription_id is not None,
        "stripe_customer_id": user.stripe_customer_id,
    }

    # If there's an active subscription, fetch details from Stripe
    if user.stripe_subscription_id and settings.stripe_secret_key:
        try:
            sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
            result["subscription"] = {
                "id": sub.id,
                "status": sub.status,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except stripe.StripeError:
            result["subscription"] = None

    return result


# ── POST /api/v1/billing/webhook ─────────────────────────────────────────


@router.post(
    "/webhook",
    summary="Stripe webhook handler",
    include_in_schema=False,  # Hide from OpenAPI docs — Stripe-only endpoint
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events to sync subscription state.

    Events handled:
    - customer.subscription.created → set tier
    - customer.subscription.updated → update tier
    - customer.subscription.deleted → downgrade to free
    - invoice.payment_failed → log warning (Stripe retries automatically)
    - checkout.session.completed → link customer ID if needed
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.stripe_webhook_secret,
        )
    except ValueError as e:
        logger.warning("Webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.SignatureVerificationError as e:
        logger.warning("Webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Stripe webhook: %s", event_type)

    # ── Subscription lifecycle events ─────────────────────────────────

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        _sync_tier_from_subscription(db, data_object)

    # ── Checkout completed — ensure customer ID is linked ─────────────

    elif event_type == "checkout.session.completed":
        session_data = data_object
        customer_id = session_data.get("customer")
        user_id = (session_data.get("metadata") or {}).get("user_id")

        if user_id and customer_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id
                db.commit()
                logger.info("Linked Stripe customer: user=%s, customer=%s", user.email, customer_id)

    # ── Payment failures ──────────────────────────────────────────────

    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            logger.warning(
                "Payment failed: user=%s, customer=%s. Stripe will retry.",
                user.email,
                customer_id,
            )

    else:
        logger.debug("Webhook: unhandled event type %s", event_type)

    return {"status": "ok"}
