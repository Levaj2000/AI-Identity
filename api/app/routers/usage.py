"""Usage & quota endpoints — check limits, view usage, list tiers, aggregation."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.quota import get_usage_summary
from api.app.usage_aggregation import get_full_aggregation
from common.models import TIER_QUOTAS, User, get_db
from common.schemas.quota import (
    TierInfoResponse,
    TierListResponse,
    UsageAggregationResponse,
    UsageSummaryResponse,
)

logger = logging.getLogger("ai_identity.api.usage")

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


# ── GET /api/v1/usage ─────────────────────────────────────────────────


@router.get(
    "",
    response_model=UsageSummaryResponse,
    summary="Get usage summary",
)
def get_usage(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current resource usage against your tier's quota limits.

    Shows agents, keys, credentials, and monthly request counts
    with percentage utilization for each resource.
    """
    summary = get_usage_summary(db, user)
    return UsageSummaryResponse(**summary)


# ── GET /api/v1/usage/aggregation ─────────────────────────────────────


@router.get(
    "/aggregation",
    response_model=UsageAggregationResponse,
    summary="Get usage aggregation",
)
def get_aggregation(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed usage aggregation for the current billing period.

    Returns:
    - **billing_period**: Current period summary (total requests, allowed/denied/errors,
      active agents, peak/avg daily)
    - **previous_period**: Previous period for comparison (null if no data)
    - **daily**: Time-series of daily request counts (zero-filled)
    - **by_agent**: Per-agent breakdown sorted by total requests (desc)

    The billing period is calculated from the user's `usage_reset_day`
    (defaults to the 1st of each month).
    """
    data = get_full_aggregation(db, user)
    return UsageAggregationResponse(**data)


# ── GET /api/v1/usage/tiers ───────────────────────────────────────────


@router.get(
    "/tiers",
    response_model=TierListResponse,
    summary="List available tiers",
)
def list_tiers(
    user: User = Depends(get_current_user),
):
    """List all available subscription tiers with their quota limits."""
    tiers = []
    for name, quotas in TIER_QUOTAS.items():
        tiers.append(
            TierInfoResponse(
                name=name,
                max_agents=quotas["max_agents"],
                max_keys_per_agent=quotas["max_keys_per_agent"],
                max_requests_per_month=quotas["max_requests_per_month"],
                max_credentials=quotas["max_credentials"],
                audit_retention_days=quotas["audit_retention_days"],
            )
        )
    return TierListResponse(tiers=tiers, current_tier=user.tier)
